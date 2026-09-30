# Unit tests for photo search that need neither the model nor the network.
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
os.environ['PARCHAOS_IMAGE_SEARCH_LIB'] = ROOT


def load(name, filename=None):
    path = os.path.join(ROOT, filename or name)
    loader = importlib.machinery.SourceFileLoader(name.replace('-', '_'), path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


clip = load('clipsearch', 'clipsearch.py')


class Tokens(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        # A tiny vocabulary: single letters, "cat</w>", and the two markers.
        vocab = {}
        for ch in 'abcdefghijklmnopqrstuvwxyz':
            vocab[ch] = len(vocab)
            vocab[ch + '</w>'] = len(vocab)
        vocab['ca'] = len(vocab)
        vocab['cat</w>'] = len(vocab)
        vocab['<|startoftext|>'] = clip.START
        vocab['<|endoftext|>'] = clip.END
        with open(os.path.join(self.dir.name, 'vocab.json'), 'w') as f:
            json.dump(vocab, f)
        with open(os.path.join(self.dir.name, 'merges.txt'), 'w') as f:
            f.write('#version: 0.2\nc a\nca t</w>\n')
        self.tok = clip.Tokenizer(os.path.join(self.dir.name, 'vocab.json'),
                                  os.path.join(self.dir.name, 'merges.txt'))
        self.vocab = vocab

    def test_merges_are_applied_and_text_is_wrapped(self):
        ids = self.tok.encode('Cat')
        self.assertEqual(ids, [clip.START, self.vocab['cat</w>'], clip.END])

    def test_unmerged_letters_stay_separate(self):
        ids = self.tok.encode('dog')
        self.assertEqual(ids, [clip.START, self.vocab['d'], self.vocab['o'], self.vocab['g</w>'], clip.END])

    def test_long_text_is_cut_and_still_ends_with_the_marker(self):
        ids = self.tok.encode('cat ' * 200)
        self.assertEqual(len(ids), 77)
        self.assertEqual(ids[-1], clip.END)


class Index(unittest.TestCase):
    def test_finding_pictures_skips_hidden_and_other_files(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ('a.jpg', 'b.PNG', 'notes.txt', '.hidden.jpg'):
                open(os.path.join(d, name), 'w').close()
            os.mkdir(os.path.join(d, '.cache'))
            open(os.path.join(d, '.cache', 'c.jpg'), 'w').close()
            found = sorted(os.path.basename(p) for p in clip.find_pictures([d]))
            self.assertEqual(found, ['a.jpg', 'b.PNG'])

    def test_database_is_created(self):
        with tempfile.TemporaryDirectory() as d:
            db = clip.open_db(os.path.join(d, 'x', 'index.sqlite'))
            self.assertEqual(db.execute('SELECT count(*) FROM images').fetchone(), (0,))


class Download(unittest.TestCase):
    def test_every_model_file_has_a_size_and_a_pinned_checksum(self):
        tool = load('parchaos-image-search')
        for name, (remote, size, digest) in tool.MODEL_FILES.items():
            self.assertGreater(size, 0, name)
            self.assertEqual(len(digest), 64, name)

    def test_a_download_that_fails_its_check_is_discarded(self):
        tool = load('parchaos-image-search')
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'src')
            os.mkdir(src)
            for name, (remote, size, _digest) in tool.MODEL_FILES.items():
                path = os.path.join(src, remote)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(b'x' * size)
            dest = os.path.join(d, 'model')
            with self.assertRaises(RuntimeError):
                tool.download_model(dest, base='file://' + src + '/')
            self.assertEqual([f for f in os.listdir(dest) if f.endswith('.part')], [])


if __name__ == '__main__':
    unittest.main()
