#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Tests for parchaos-ambient: every sound builds and renders audible, unclipped audio; the tone,
# timer and motion helpers stay in range. Skips when GStreamer is not installed.
import array
import os
import random
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    ambient = SourceFileLoader('ambient', os.path.join(HERE, '..', 'files', 'parchaos-ambient')).load_module()
except (ImportError, ValueError):
    ambient = None


def render(sound, seconds=2):
    """Render a sound offline to raw float samples; returns the samples."""
    pipeline, _layers, tone, master = ambient.build(sound, 'fakesink', random.Random(1), live=False)
    tone.set_property('cutoff', ambient.tone_cutoff(0.5))
    master.set_property('volume', 0.5)
    kind = lambda e: e.get_factory().get_name()
    sink = next(e for e in pipeline.children if kind(e) == 'fakesink')
    convert = sink.get_static_pad('sink').get_peer().get_parent_element()
    convert.unlink(sink)
    pipeline.remove(sink)
    out = tempfile.NamedTemporaryFile(suffix='.raw', delete=False)
    out.close()
    caps = Gst.ElementFactory.make('capsfilter')
    caps.set_property('caps', Gst.Caps.from_string('audio/x-raw,format=F32LE,channels=1'))
    filesink = Gst.ElementFactory.make('filesink')
    filesink.set_property('location', out.name)
    pipeline.add(caps)
    pipeline.add(filesink)
    convert.link(caps)
    caps.link(filesink)
    for src in [e for e in pipeline.children if kind(e) == 'audiotestsrc']:
        src.set_property('num-buffers', int(44100 * seconds / 1024))
    pipeline.set_state(Gst.State.PLAYING)
    pipeline.get_bus().timed_pop_filtered(20 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    pipeline.set_state(Gst.State.NULL)
    samples = array.array('f')
    with open(out.name, 'rb') as f:
        samples.frombytes(f.read())
    os.unlink(out.name)
    return samples


@unittest.skipIf(ambient is None, 'GStreamer (python3-gobject, gstreamer1) is not installed')
class AmbientTests(unittest.TestCase):
    def test_every_sound_is_audible_and_unclipped(self):
        for sound in ambient.SOUNDS:
            samples = render(sound)
            self.assertGreater(len(samples), 44100, sound)
            rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
            peak = max(abs(s) for s in samples)
            self.assertGreater(rms, 0.005, f'{sound} is silent')
            self.assertLess(peak, 1.0, f'{sound} clips')

    def test_tone_and_timer_ranges(self):
        self.assertAlmostEqual(ambient.tone_cutoff(0), 1200.0)
        self.assertAlmostEqual(ambient.tone_cutoff(1), 18000.0)
        self.assertEqual(ambient.tone_cutoff(-5), ambient.tone_cutoff(0))
        self.assertEqual(ambient.timer_seconds(0), 0)
        self.assertEqual(ambient.timer_seconds(5), 15 * 60)
        self.assertEqual(ambient.timer_seconds(60), 3600)
        self.assertEqual(ambient.timer_seconds(10000), 8 * 3600)

    def test_motions_stay_in_range(self):
        for kind, period in [('swell', 9.0), ('flutter', 0.0), ('patter', 0.0), ('chirp', 0.0)]:
            motion = ambient.Motion(kind, period, random.Random(2))
            values = [motion.step(0.05) for _ in range(2000)]
            self.assertTrue(all(0.0 <= v <= 1.0 for v in values), kind)
            self.assertGreater(max(values) - min(values), 0.3, f'{kind} does not move')


if __name__ == '__main__':
    unittest.main()
