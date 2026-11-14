# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for Parcha Nearby (ticket #149). Run:
#   python3 packaging/parchaos-nearby/tests/test_nearby.py
# The second half starts two Nearby devices in this process on spare ports and sends files
# between them over real sockets (multicast discovery, HTTPS, uploads).
import http.client
import importlib.machinery
import importlib.util
import json
import os
import ssl
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
os.environ['PARCHAOS_NEARBY_CONFIG'] = os.path.join(TMP, 'nearby.ini')
loader = importlib.machinery.SourceFileLoader('parchaos_nearby', os.path.join(HERE, '..', 'parchaos-nearby'))
spec = importlib.util.spec_from_loader('parchaos_nearby', loader)
nb = importlib.util.module_from_spec(spec)
loader.exec_module(nb)

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print(f'FAIL {what}')


# Names from the network can't climb out of Downloads.
check(nb.safe_parts('photo.jpg') == ['photo.jpg'], 'plain name')
check(nb.safe_parts('Trip/day 1/a.jpg') == ['Trip', 'day 1', 'a.jpg'], 'a folder keeps its inside')
check(nb.safe_parts('../../.bashrc') == ['.bashrc'], 'no climbing up')
check(nb.safe_parts('/etc/passwd') == ['etc', 'passwd'], 'no absolute paths')
check(nb.safe_parts('..\\..\\x') == ['x'], 'backslashes too')
check(nb.safe_parts('../..') is None and nb.safe_parts(5) is None, 'nothing left is refused')

with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, 'a.txt'), 'w').close()
    open(os.path.join(d, 'a (2).txt'), 'w').close()
    check(nb.free_name(d, 'a.txt') == 'a (3).txt', 'a taken name gets a number')
    check(nb.free_name(d, 'b.txt') == 'b.txt', 'a free name stays')
    open(os.path.join(d, 'x.tar.gz'), 'w').close()
    check(nb.free_name(d, 'x.tar.gz') == 'x (2).tar.gz', 'double extensions stay together')

    os.makedirs(os.path.join(d, 'Trip', 'day1'))
    os.makedirs(os.path.join(d, 'Trip', '.cache'))
    for p in ('Trip/one.jpg', 'Trip/day1/two.jpg', 'Trip/.hidden', 'Trip/.cache/x'):
        with open(os.path.join(d, p), 'w') as f:
            f.write('12345')
    files = nb.collect_files([os.path.join(d, 'Trip'), os.path.join(d, 'a.txt')])
    names = sorted(f[2] for f in files)
    check(names == ['Trip/day1/two.jpg', 'Trip/one.jpg', 'a.txt'], f'folders sent with their inside ({names})')
    check(all(f[1].startswith(d) for f in files) and len({f[0] for f in files}) == 3, 'ids unique, real paths')
    check(next(f for f in files if f[2] == 'Trip/one.jpg')[4] == 'image/jpeg', 'file type')
    check(nb.top_names(names) == ['Trip', 'a.txt'], 'a folder counts once')

dev = nb.parse_device({'alias': 'Pixel 8', 'fingerprint': 'AB', 'port': 53317, 'protocol': 'https',
                       'deviceType': 'mobile', 'deviceModel': 'Google'}, '192.168.1.5')
check(dev['alias'] == 'Pixel 8' and dev['type'] == 'mobile' and dev['ip'] == '192.168.1.5', 'device parsed')
check(nb.parse_device({'alias': 'x', 'fingerprint': 'y', 'deviceType': 'toaster'}, 'i')['type'] == 'desktop',
      'unknown kinds are computers')
check(nb.parse_device({'alias': '', 'fingerprint': 'y'}, 'i') is None, 'no name, no device')
check(nb.parse_device({'alias': 'x', 'fingerprint': 'y', 'port': 'z'}, 'i') is None, 'bad port refused')
check(nb.parse_device({'alias': 'x', 'fingerprint': 'y', 'protocol': 'ftp'}, 'i') is None, 'bad protocol refused')

check(nb.is_message({'a': {'fileType': 'text/plain', 'preview': 'hola', 'fileName': 'a.txt'}}) == 'hola',
      'a text message')
check(nb.is_message({'a': {'fileType': 'text/plain', 'fileName': 'notes.txt', 'size': 4}}) is None,
      'a text file is a file')

title, detail = nb.offer_text('Pixel 8', {'1': {'fileName': 'a.jpg', 'size': 2_000_000},
                                          '2': {'fileName': 'Trip/b.jpg', 'size': 1_000_000},
                                          '3': {'fileName': 'Trip/c.jpg', 'size': 1_200_000}})
check(title == 'Pixel 8 wants to send you 3 files', title)
check(detail == 'a.jpg and Trip · 4.2 MB', detail)
check(nb.names_text(['a', 'b', 'c', 'd']) == 'a, b and 2 more', 'long lists shortened')
check(nb.error_text(403, 'Pixel') == 'Pixel declined.', 'declined in words')
check(nb.format_size(512) == '512 bytes', 'bytes')

targets = nb.scan_targets([('wlp3s0', '192.168.1.20', 24), ('docker0', '172.17.0.1', 16)])
check(len(targets) == 253 and '192.168.1.20' not in targets and '192.168.1.1' in targets,
      'search the real /24 but not ourselves or docker')
check(len(nb.scan_targets([('eth0', '10.0.5.9', 8)])) == 1021, 'a huge network only near us')


class Body:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def readline(self, n):
        i = self.data.find(b'\n', self.pos, self.pos + n)
        end = i + 1 if i >= 0 else min(len(self.data), self.pos + n)
        out, self.pos = self.data[self.pos:end], end
        return out

    def read(self, n):
        out = self.data[self.pos:self.pos + n]
        self.pos += len(out)
        return out


got = bytearray()
n = nb.read_body(Body(b'5\r\nhello\r\n6;x=y\r\n world\r\n0\r\n\r\n'), {'Transfer-Encoding': 'chunked'},
                 got.extend, 100)
check(n == 11 and bytes(got) == b'hello world', 'chunked bodies (how LocalSend streams files)')
try:
    nb.read_body(Body(b'5\r\nhello\r\n0\r\n\r\n'), {'Transfer-Encoding': 'chunked'}, lambda b: None, 3)
    check(False, 'a body bigger than announced is refused')
except ValueError:
    pass

# ---------------------------------------------------------------------------------------------
# Two devices on this computer.
# ---------------------------------------------------------------------------------------------
received, messages, asked = [], [], []
answer = {'value': True}


def ask(offer):
    asked.append(offer)
    return answer['value']


a_dir, b_dir = os.path.join(TMP, 'a'), os.path.join(TMP, 'b')
a = nb.Node(conf={'receive': True, 'alias': 'Alpha'}, port=53417,
            identity=nb.ensure_identity(os.path.join(a_dir, 'id')), folder=os.path.join(a_dir, 'Downloads'))
b = nb.Node(conf={'receive': True, 'alias': 'Beta'}, port=53427,
            identity=nb.ensure_identity(os.path.join(b_dir, 'id')), folder=os.path.join(b_dir, 'Downloads'),
            ask=ask, on_received=lambda *x: received.append(x), on_message=lambda *x: messages.append(x))
check(len(a.fingerprint) == 64 and a.fingerprint == a.fingerprint.upper(), 'fingerprint: SHA-256, upper-case hex')
check(nb.ensure_identity(os.path.join(a_dir, 'id'))[2] == a.fingerprint, 'the identity is kept')
check(oct(os.stat(os.path.join(a_dir, 'id', 'key.pem')).st_mode & 0o777) == '0o600', 'the key is private')
a.start()
b.start()
a.start_discovery()
deadline = time.monotonic() + 8
while time.monotonic() < deadline and not (any(d['alias'] == 'Beta' for d in a.device_list()) and
                                           any(d['alias'] == 'Alpha' for d in b.device_list())):
    time.sleep(0.1)
beta = next((d for d in a.device_list() if d['alias'] == 'Beta'), None)
if beta is None and not nb.ipv4_interfaces():
    # A build container with only loopback has no multicast: find Beta the second way the
    # protocol has (asking an address directly) and test the rest.
    print('nearby: no network here besides loopback; skipping the multicast check')
    beta = a.register_with('127.0.0.1', 53427)
    b.register_with('127.0.0.1', 53417)
else:
    check(beta is not None, 'Alpha finds Beta by multicast')
check(all(d['fingerprint'] != a.fingerprint for d in a.device_list()), 'Alpha does not find itself')
check(any(d['alias'] == 'Alpha' for d in b.device_list()), 'Beta learned about Alpha too')

if beta:
    check(beta['port'] == 53427 and beta['fingerprint'] == b.fingerprint, 'with its port and fingerprint')
    src = os.path.join(TMP, 'src')
    os.makedirs(os.path.join(src, 'Album'))
    big = os.urandom(3 * 1024 * 1024 + 17)
    with open(os.path.join(src, 'Album', 'big.bin'), 'wb') as f:
        f.write(big)
    with open(os.path.join(src, 'note.txt'), 'w') as f:
        f.write('hola')
    steps = []
    err = a.send(beta, nb.collect_files([os.path.join(src, 'Album'), os.path.join(src, 'note.txt')]),
                 lambda *s: steps.append(s), threading.Event())
    check(err is None, f'sent ({err})')
    check(asked and asked[-1]['alias'] == 'Alpha' and len(asked[-1]['files']) == 2, 'Beta was asked first')
    got_dir = os.path.join(b_dir, 'Downloads')
    check(open(os.path.join(got_dir, 'Album', 'big.bin'), 'rb').read() == big, 'the big file arrived whole')
    check(open(os.path.join(got_dir, 'note.txt')).read() == 'hola', 'and the small one')
    check(steps[0][0] == 'waiting' and steps[-1] == ('sending', len(big) + 4, len(big) + 4), 'progress reported')
    check(received and received[-1][0] == 'Alpha' and received[-1][2] == 0 and
          sorted(os.path.basename(p) for p in received[-1][1]) == ['Album', 'note.txt'],
          f'Beta was told what arrived ({received[-1:]})')
    check(not [n for n in os.listdir(got_dir) if n.startswith('.')], 'no partial files left')

    # Again: names already there get a number, nothing is overwritten.
    err = a.send(beta, nb.collect_files([os.path.join(src, 'note.txt')]), lambda *s: None, threading.Event())
    check(err is None and open(os.path.join(got_dir, 'note (2).txt')).read() == 'hola', 'a second copy beside it')

    # A device that claims to be Beta but isn't: nothing is sent.
    fake = dict(beta, fingerprint='00' * 32)
    n_asked = len(asked)
    err = a.send(fake, nb.collect_files([os.path.join(src, 'note.txt')]), lambda *s: None, threading.Event())
    check(err and 'confirm' in err and len(asked) == n_asked, f'wrong fingerprint refused ({err})')

    # Straight HTTP calls, as another implementation could make them.
    def call(method, path, body=None, headers=None):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        c = http.client.HTTPSConnection('127.0.0.1', 53427, context=ctx, timeout=10)
        c.request(method, path, body, headers or {})
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data

    info = {'alias': 'Phone', 'version': '2.2', 'fingerprint': 'F00', 'port': 1, 'protocol': 'https'}
    status, data = call('GET', nb.API + '/info')
    check(status == 200 and json.loads(data)['alias'] == 'Beta', 'info')
    status, _ = call('POST', nb.API + '/prepare-upload', json.dumps(
        {'info': info, 'files': {'m': {'id': 'm', 'fileName': 'm.txt', 'size': 4, 'fileType': 'text/plain',
                                       'preview': 'hola!'}}}))
    check(status == 204 and messages and messages[-1] == ('Phone', 'hola!'), 'a text message is shown, not saved')
    status, data = call('POST', nb.API + '/prepare-upload', json.dumps(
        {'info': info, 'files': {'x': {'id': 'x', 'fileName': '../../escape.txt', 'size': 11,
                                       'fileType': 'text/plain', 'sha256': None}}}))
    check(status == 200, f'offer accepted ({status})')
    sess = json.loads(data)
    q = f"sessionId={sess['sessionId']}&fileId=x&token={sess['files']['x']}"
    status, _ = call('POST', nb.API + '/upload?' + q.replace(sess['files']['x'], 'wrong'), b'hello world')
    check(status == 403, 'a wrong token is refused')
    status, _ = call('POST', nb.API + '/upload?' + q, b'5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n',
                     {'Transfer-Encoding': 'chunked'})
    check(status == 200 and open(os.path.join(got_dir, 'escape.txt')).read() == 'hello world'
          and not os.path.exists(os.path.join(TMP, 'escape.txt')), 'chunked upload lands inside Downloads')

    status, data = call('POST', nb.API + '/prepare-upload', json.dumps(
        {'info': info, 'files': {'y': {'id': 'y', 'fileName': 'y.txt', 'size': 3, 'fileType': 'text/plain',
                                       'sha256': 'a' * 64}}}))
    sess = json.loads(data)
    status, _ = call('POST', nb.API + f"/upload?sessionId={sess['sessionId']}&fileId=y&token={sess['files']['y']}",
                     b'abc')
    check(status == 422 and not os.path.exists(os.path.join(got_dir, 'y.txt')), 'a damaged file is not kept')

    # Cancelling a transfer part way: the receiver keeps nothing half-written.
    huge = os.path.join(src, 'huge.bin')
    with open(huge, 'wb') as f:
        f.truncate(200 * 1024 * 1024)
    stop = threading.Event()

    def watch(stage, done, total):
        if done > 5 * 1024 * 1024:
            stop.set()
    err = a.send(beta, nb.collect_files([huge]), watch, stop)
    time.sleep(0.5)
    check(err == 'Cancelled.', f'cancelled ({err})')
    check(not os.path.exists(os.path.join(got_dir, 'huge.bin')) and
          not [n for n in os.listdir(got_dir) if n.endswith('.part')], 'nothing half-written stays')
    check(b.session is None, 'Beta is free for the next transfer')

    # Declining.
    answer['value'] = False
    err = a.send(beta, nb.collect_files([os.path.join(src, 'note.txt')]), lambda *s: None, threading.Event())
    check(err == 'Beta declined.', f'declined in words ({err})')
    err = a.send(beta, nb.collect_files([os.path.join(src, 'note.txt')]), lambda *s: None, threading.Event())
    check(err and 'wait' in err, f'asking again straight away is held off ({err})')

    # Receiving off: offers refused without asking, and Beta stops answering discovery.
    b.conf['receive'] = False
    n_asked = len(asked)
    status, _ = call('POST', nb.API + '/prepare-upload', json.dumps(
        {'info': info, 'files': {'z': {'id': 'z', 'fileName': 'z', 'size': 1, 'fileType': 'x'}}}))
    check(status == 403 and len(asked) == n_asked, 'receiving off: refused, nobody asked')
    status, _ = call('POST', nb.API + '/register', json.dumps(info))
    check(status == 403, 'receiving off: not discoverable')

a.stop_discovery()
a.stop()
b.stop()
if failures:
    print(f'nearby: {failures} failure(s)')
    sys.exit(1)
print('nearby: all checks passed')
