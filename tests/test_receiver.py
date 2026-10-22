import io
import struct
import sys
import unittest
from unittest.mock import patch
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc'))
from protocol import pump
from receiver import PlaybackOutput, VirtualMic

class FlowTests(unittest.TestCase):
    def test_stalled_playback_times_out(self):
        read_fd, write_fd = os.pipe()
        with os.fdopen(read_fd,'rb',buffering=0), os.fdopen(write_fd,'wb',buffering=0) as pipe:
            output = PlaybackOutput(pipe)
            with patch('receiver.select.select', return_value=([],[],[])):
                with self.assertRaises(TimeoutError): output.write(b'xx')

    def test_failed_source_creation_unloads_sink(self):
        calls=[]
        def fake_pactl(*args):
            calls.append(args)
            if args[:2]==('load-module','module-null-sink'): return '42'
            if args[0]=='load-module': raise OSError('Source unavailable')
        with patch('receiver.pactl',side_effect=fake_pactl):
            with self.assertRaises(OSError):
                with VirtualMic(): pass
        self.assertEqual(calls[-1],('unload-module','42'))

    def test_short_output_writes_do_not_drop_samples(self):
        class ShortWriter(io.BytesIO):
            def write(self, data): return super().write(data[:7])
        pcm = bytes(range(256))*3
        output = ShortWriter()
        pump(io.BytesIO(struct.pack('!H',len(pcm))+pcm),output)
        self.assertEqual(output.getvalue(),pcm)

    def test_audio_reaches_output_unchanged(self):
        # A receiver that changes samples or loses frames breaks this assertion.
        pcm = struct.pack('<480h', *range(-240,240))
        source = io.BytesIO((struct.pack('!H',960)+pcm)*100)
        output = io.BytesIO()
        self.assertEqual(pump(source,output),96000)
        self.assertEqual(output.getvalue(),pcm*100)

    def test_truncated_input_never_writes_partial_audio(self):
        output = io.BytesIO()
        with self.assertRaises(EOFError): pump(io.BytesIO(b'\x03\xc0bad'),output)
        self.assertEqual(output.getvalue(), b'')
