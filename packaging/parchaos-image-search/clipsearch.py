# SPDX-License-Identifier: GPL-3.0-or-later
# Local photo search: finds pictures by what is in them.
#
# A small image model (CLIP ViT-B/32, MIT licence, run through ONNX Runtime)
# turns every picture and every search phrase into a list of 512 numbers;
# pictures whose numbers are close to the phrase's are the matches. Everything
# stays on this computer. Original code for ParchaOS, GPL-3.0-or-later.

import gzip
import json
import os
import re
import sqlite3
import sys
import time

DATA_DIR = os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share'),
                        'parchaos-image-search')
MODEL_DIR = os.path.join(DATA_DIR, 'model')
DB_PATH = os.path.join(DATA_DIR, 'index.sqlite')
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff')
MEAN = (0.48145466, 0.4578275, 0.40821073)
STD = (0.26862954, 0.26130258, 0.27577711)
START, END = 49406, 49407


# ---- tokenizer (CLIP byte-pair encoding) -----------------------------------

def _bytes_to_unicode():
    keep = list(range(ord('!'), ord('~') + 1)) + list(range(0xA1, 0xAD)) + list(range(0xAE, 0x100))
    chars = keep[:]
    extra = 0
    for b in range(256):
        if b not in keep:
            keep.append(b)
            chars.append(256 + extra)
            extra += 1
    return dict(zip(keep, map(chr, chars)))


class Tokenizer:
    """Turns text into the token numbers the text model expects."""

    SPLIT = re.compile(r"'s|'t|'re|'ve|'m|'ll|'d|[^\W\d_]+|\d|[^\s\w]+", re.IGNORECASE)

    def __init__(self, vocab_path, merges_path):
        with open(vocab_path, encoding='utf-8') as f:
            self.vocab = json.load(f)
        opener = gzip.open if merges_path.endswith('.gz') else open
        with opener(merges_path, 'rt', encoding='utf-8') as f:
            lines = f.read().split('\n')
        merges = [tuple(line.split()) for line in lines[1:] if line and not line.startswith('#')]
        self.ranks = {pair: i for i, pair in enumerate(merges)}
        self.byte_map = _bytes_to_unicode()
        self.cache = {}

    def _bpe(self, token):
        if token in self.cache:
            return self.cache[token]
        word = tuple(token[:-1]) + (token[-1] + '</w>',)
        while len(word) > 1:
            pairs = {(a, b) for a, b in zip(word, word[1:])}
            best = min(pairs, key=lambda p: self.ranks.get(p, float('inf')))
            if best not in self.ranks:
                break
            merged = []
            i = 0
            while i < len(word):
                if i < len(word) - 1 and (word[i], word[i + 1]) == best:
                    merged.append(word[i] + word[i + 1])
                    i += 2
                else:
                    merged.append(word[i])
                    i += 1
            word = tuple(merged)
        self.cache[token] = word
        return word

    def encode(self, text, limit=77):
        text = re.sub(r'\s+', ' ', text).strip().lower()
        ids = [START]
        for match in self.SPLIT.findall(text):
            token = ''.join(self.byte_map[b] for b in match.encode('utf-8'))
            ids.extend(self.vocab[piece] for piece in self._bpe(token) if piece in self.vocab)
        ids = ids[:limit - 1] + [END]
        return ids


# ---- model -------------------------------------------------------------------

def model_files(directory=None):
    directory = directory or MODEL_DIR
    return {name: os.path.join(directory, name) for name in
            ('vision_model_quantized.onnx', 'text_model_quantized.onnx', 'vocab.json', 'merges.txt')}


def model_ready(directory=None):
    return all(os.path.isfile(p) for p in model_files(directory).values())


class Model:
    def __init__(self, directory=None):
        import numpy
        import onnxruntime
        self.np = numpy
        files = model_files(directory)
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        self.vision = onnxruntime.InferenceSession(files['vision_model_quantized.onnx'], options,
                                                   providers=['CPUExecutionProvider'])
        self.text = onnxruntime.InferenceSession(files['text_model_quantized.onnx'], options,
                                                 providers=['CPUExecutionProvider'])
        self.tokenizer = Tokenizer(files['vocab.json'], files['merges.txt'])

    def _normalise(self, vectors):
        np = self.np
        return vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)

    def prepare(self, path):
        """Load one picture as the 3x224x224 array the model expects."""
        from PIL import Image
        np = self.np
        with Image.open(path) as image:
            image = image.convert('RGB')
            w, h = image.size
            scale = 224 / min(w, h)
            image = image.resize((max(224, round(w * scale)), max(224, round(h * scale))), Image.BICUBIC)
            w, h = image.size
            left, top = (w - 224) // 2, (h - 224) // 2
            image = image.crop((left, top, left + 224, top + 224))
            pixels = np.asarray(image, dtype=np.float32) / 255.0
        pixels = (pixels - np.array(MEAN, dtype=np.float32)) / np.array(STD, dtype=np.float32)
        return pixels.transpose(2, 0, 1)

    def embed_images(self, paths):
        np = self.np
        batch = np.stack([self.prepare(p) for p in paths]).astype(np.float32)
        out = self.vision.run(None, {'pixel_values': batch})[0]
        return self._normalise(out)

    def embed_text(self, phrase):
        np = self.np
        ids = np.array([self.tokenizer.encode(phrase)], dtype=np.int64)
        out = self.text.run(None, {'input_ids': ids})[0]
        return self._normalise(out)[0]


# ---- index -------------------------------------------------------------------

def open_db(path=None):
    path = path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS images (path TEXT PRIMARY KEY, mtime REAL, size INTEGER, emb BLOB)')
    return db


def find_pictures(folders):
    for folder in folders:
        for root, dirs, files in os.walk(os.path.expanduser(folder)):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            for name in sorted(files):
                if name.lower().endswith(IMAGE_EXTENSIONS) and not name.startswith('.'):
                    yield os.path.join(root, name)


def index_pictures(model, db, folders, batch=8, log=None, budget=None):
    """Embed pictures that are new or changed; drop ones that are gone.

    budget: stop after this many seconds (the rest is done next run).
    Returns (added, removed, failed).
    """
    np = model.np
    start = time.monotonic()
    known = {p: (m, s) for p, m, s in db.execute('SELECT path, mtime, size FROM images')}
    seen = set()
    todo = []
    for path in find_pictures(folders):
        seen.add(path)
        try:
            st = os.stat(path)
        except OSError:
            continue
        if known.get(path) != (st.st_mtime, st.st_size):
            todo.append((path, st.st_mtime, st.st_size))
    added = failed = 0
    for i in range(0, len(todo), batch):
        if budget is not None and time.monotonic() - start > budget:
            break
        chunk = todo[i:i + batch]
        good, vectors = [], []
        for item in chunk:
            try:
                vectors.append(model.prepare(item[0]))
                good.append(item)
            except Exception as err:  # an unreadable or broken picture
                failed += 1
                if log:
                    log(f'skipped {item[0]}: {err}')
        if not good:
            continue
        out = model._normalise(model.vision.run(None, {'pixel_values': np.stack(vectors).astype(np.float32)})[0])
        for (path, mtime, size), vec in zip(good, out):
            db.execute('INSERT OR REPLACE INTO images VALUES (?, ?, ?, ?)',
                       (path, mtime, size, vec.astype(np.float16).tobytes()))
            added += 1
        db.commit()
    gone = [p for p in known if p not in seen and any(
        p.startswith(os.path.expanduser(f).rstrip('/') + '/') for f in folders)]
    for path in gone:
        db.execute('DELETE FROM images WHERE path = ?', (path,))
    db.commit()
    return added, len(gone), failed


def search(model, db, phrase, limit=20, minimum=0.18):
    """Best matches for a phrase: [(score, path)], best first."""
    np = model.np
    rows = db.execute('SELECT path, emb FROM images').fetchall()
    if not rows:
        return []
    matrix = np.stack([np.frombuffer(blob, dtype=np.float16) for _p, blob in rows]).astype(np.float32)
    scores = matrix @ model.embed_text(phrase)
    order = np.argsort(-scores)[:limit]
    return [(float(scores[i]), rows[i][0]) for i in order if scores[i] >= minimum and os.path.exists(rows[i][0])]
