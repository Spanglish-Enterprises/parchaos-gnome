# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-assistant: the Claude backend against a local fake Messages endpoint (no network,
# no key), and the config helpers. Skips without GTK/libsecret for Python or the anthropic SDK.
import http.server
import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('Secret', '1')
    import anthropic  # noqa: F401
except (ImportError, ValueError):
    print('assistant: skipped (needs GTK 4, libadwaita, libsecret for Python and the anthropic SDK)')
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('parchaos_assistant', os.path.join(HERE, '..', 'files', 'parchaos-assistant'))
spec = importlib.util.spec_from_loader('parchaos_assistant', loader)
assistant = importlib.util.module_from_spec(spec)
loader.exec_module(assistant)


def sse(events):
    return ''.join(f'event: {name}\ndata: {json.dumps(data)}\n\n' for name, data in events).encode()


def reply_events(text, stop='end_turn'):
    msg = {'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': assistant.CLAUDE_MODEL,
           'content': [], 'stop_reason': None, 'stop_sequence': None,
           'usage': {'input_tokens': 5, 'output_tokens': 0}}
    half = len(text) // 2
    return sse([
        ('message_start', {'type': 'message_start', 'message': msg}),
        ('content_block_start', {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}}),
        ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text[:half]}}),
        ('content_block_delta', {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text[half:]}}),
        ('content_block_stop', {'type': 'content_block_stop', 'index': 0}),
        ('message_delta', {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None}, 'usage': {'output_tokens': 7}}),
        ('message_stop', {'type': 'message_stop'}),
    ])


class Fake(http.server.BaseHTTPRequestHandler):
    requests = []
    status = 200

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['content-length'])))
        Fake.requests.append({'path': self.path, 'headers': {k.lower(): v for k, v in self.headers.items()}, 'body': body})
        if Fake.status != 200:
            payload = json.dumps({'type': 'error', 'error': {'type': 'authentication_error', 'message': 'bad key'}}).encode()
            self.send_response(Fake.status)
            self.send_header('content-type', 'application/json')
            self.send_header('content-length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        data = reply_events('Hola, ¿en qué te ayudo?')
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class Claude(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        os.environ['ANTHROPIC_BASE_URL'] = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        Fake.requests.clear()
        Fake.status = 200

    def test_streams_text_and_sends_the_expected_request(self):
        backend = assistant.ClaudeBackend('sk-test')
        pieces = []
        backend.reply([{'role': 'user', 'text': 'hola'}], pieces.append)
        self.assertEqual(''.join(pieces), 'Hola, ¿en qué te ayudo?')
        req = Fake.requests[0]
        self.assertEqual(req['path'].split('?')[0], '/v1/messages')
        # The SDK sends the key as x-api-key or, in newer releases, as a bearer token.
        self.assertIn('sk-test', (req['headers'].get('x-api-key', ''), req['headers'].get('authorization', '').removeprefix('Bearer ')))
        self.assertIn('server-side-fallback-2026-07-01', req['headers'].get('anthropic-beta', ''))
        body = req['body']
        self.assertEqual(body['model'], 'claude-opus-5-5')
        self.assertTrue(body['stream'])
        self.assertEqual(body['fallbacks'], 'default')
        self.assertEqual(body['output_config'], {'effort': 'low'})
        self.assertNotIn('thinking', body)
        self.assertEqual(body['messages'], [{'role': 'user', 'content': 'hola'}])

    def test_second_turn_sends_the_first_answer_back_as_returned(self):
        backend = assistant.ClaudeBackend('sk-test')
        backend.reply([{'role': 'user', 'text': 'hola'}], lambda t: None)
        history = [{'role': 'user', 'text': 'hola'}, {'role': 'assistant', 'text': 'Hola, ¿en qué te ayudo?'},
                   {'role': 'user', 'text': 'gracias'}]
        backend.reply(history, lambda t: None)
        sent = Fake.requests[1]['body']['messages']
        self.assertEqual([m['role'] for m in sent], ['user', 'assistant', 'user'])
        self.assertEqual(sent[1]['content'], [{'type': 'text', 'text': 'Hola, ¿en qué te ayudo?'}])

    def test_bad_key_gets_a_plain_message(self):
        Fake.status = 401
        backend = assistant.ClaudeBackend('sk-wrong')
        backend.client = backend.client.with_options(max_retries=0)
        with self.assertRaises(Exception) as ctx:
            backend.reply([{'role': 'user', 'text': 'hola'}], lambda t: None)
        self.assertIn('API key', backend.describe_error(ctx.exception))


class FakeOllama(http.server.BaseHTTPRequestHandler):
    chats = []

    def do_GET(self):
        self._json({'models': [{'name': 'llama3.2:latest', 'model': 'llama3.2:latest', 'modified_at': '2026-11-01T00:00:00Z',
                                'size': 1, 'digest': 'x', 'details': {}}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['content-length'])))
        FakeOllama.chats.append(body)
        lines = [{'model': body['model'], 'created_at': '2026-11-08T00:00:00Z', 'message': {'role': 'assistant', 'content': piece}, 'done': False}
                 for piece in ('Hello', ' there')]
        lines.append({'model': body['model'], 'created_at': '2026-11-08T00:00:00Z', 'message': {'role': 'assistant', 'content': ''}, 'done': True})
        data = ''.join(json.dumps(line) + '\n' for line in lines).encode()
        self.send_response(200)
        self.send_header('content-type', 'application/x-ndjson')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@unittest.skipUnless(importlib.util.find_spec('ollama'), 'needs python3-ollama')
class Ollama(unittest.TestCase):
    def test_lists_models_and_streams_a_reply(self):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), FakeOllama)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            assistant.OLLAMA_HOST = f'http://127.0.0.1:{server.server_port}'
            self.assertEqual(assistant.OllamaBackend.models(), ['llama3.2:latest'])
            pieces = []
            assistant.OllamaBackend('llama3.2:latest').reply([{'role': 'user', 'text': 'hi'}], pieces.append)
            self.assertEqual(''.join(pieces), 'Hello there')
            sent = FakeOllama.chats[0]
            self.assertEqual(sent['messages'][0]['role'], 'system')
            self.assertEqual(sent['messages'][1], {'role': 'user', 'content': 'hi'})
        finally:
            server.shutdown()


class Config(unittest.TestCase):
    def test_round_trip_and_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'sub', 'assistant.json')
            self.assertEqual(assistant.load_config(path), {})
            assistant.save_config({'backend': 'ollama', 'ollama_model': 'llama3.2'}, path)
            self.assertEqual(assistant.load_config(path)['backend'], 'ollama')
            with open(path, 'w') as f:
                f.write('not json')
            self.assertEqual(assistant.load_config(path), {})


if __name__ == '__main__':
    unittest.main()
