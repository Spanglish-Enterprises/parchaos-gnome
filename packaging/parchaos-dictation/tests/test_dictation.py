# Unit tests for the dictation helpers (no microphone, model or network needed).
import hashlib
import importlib.machinery
import importlib.util
import os
import tempfile
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    path = os.path.join(HERE, '..', name)
    loader = importlib.machinery.SourceFileLoader(name.replace('-', '_'), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class Transcribe(unittest.TestCase):
    def setUp(self):
        self.t = load('parchaos-dictation-transcribe')

    def test_noise_markers_removed(self):
        self.assertEqual(self.t.clean([' [BLANK_AUDIO]', ' (music) hello', ' *cough* there ']), 'hello there')

    def test_plain_characters_only(self):
        self.assertEqual(self.t.clean(['“Café” — it’s fine…']), '"Cafe" - it\'s fine...')

    def test_empty_when_only_silence(self):
        self.assertEqual(self.t.clean([' [BLANK_AUDIO]']), '')

    def test_missing_model_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            self.t.MODEL_DIR = d
            self.assertEqual(self.t.main(['x', 'a.wav']), 3)


class Model(unittest.TestCase):
    def setUp(self):
        self.m = load('parchaos-dictation-model')
        self.dir = tempfile.TemporaryDirectory()
        self.m.MODEL_DIR = self.dir.name
        self.addCleanup(self.dir.cleanup)

    def serve(self, data):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        chunks = [data, b'']
        response.read.side_effect = lambda n: chunks.pop(0)
        return unittest.mock.patch.object(self.m.urllib.request, 'urlopen', return_value=response)

    def test_good_download_is_kept(self):
        data = b'model bytes'
        self.m.MODELS['tiny.en'] = (len(data), hashlib.sha256(data).hexdigest())
        with self.serve(data):
            self.m.download('tiny.en')
        self.assertTrue(os.path.isfile(self.m.path_for('tiny.en')))

    def test_corrupt_download_is_discarded(self):
        data = b'model bytes'
        self.m.MODELS['tiny.en'] = (len(data), hashlib.sha256(b'other').hexdigest())
        with self.serve(data), self.assertRaises(RuntimeError):
            self.m.download('tiny.en')
        self.assertEqual(os.listdir(self.dir.name), [])

    def test_status(self):
        with unittest.mock.patch.object(self.m.importlib.util, 'find_spec', return_value=None):
            self.assertEqual(self.m.main(['x', 'status']), 1)
        os.environ['PARCHAOS_DICTATION_ASSUME_ENGINE'] = '1'
        self.addCleanup(os.environ.pop, 'PARCHAOS_DICTATION_ASSUME_ENGINE')
        self.assertEqual(self.m.main(['x', 'status']), 1)
        open(self.m.path_for('base.en'), 'w').close()
        self.assertEqual(self.m.main(['x', 'status']), 0)


if __name__ == '__main__':
    unittest.main()
