import io
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc'))
import protocol as p

class Fragmented(io.BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 3))

class ProtocolTests(unittest.TestCase):
    def test_handshake_fragmented(self):
        raw = b'MLV1' + b'123456' + struct.pack('!IBB',48000,1,16)
        self.assertEqual(p.authenticate(Fragmented(raw), '123456'), None)

    def test_wrong_code(self):
        with self.assertRaises(p.ProtocolError):
            p.authenticate(io.BytesIO(b'MLV1xxxxxx'+struct.pack('!IBB',48000,1,16)), '123456')

    def test_format_rejected(self):
        with self.assertRaises(p.ProtocolError):
            p.authenticate(io.BytesIO(b'MLV1123456'+struct.pack('!IBB',44100,1,16)), '123456')

    def test_pcm_preserved(self):
        pcm = bytes(range(256))*3
        source = Fragmented(struct.pack('!H', len(pcm)) + pcm)
        self.assertEqual(p.read_frame(source), pcm)
        self.assertIsNone(p.read_frame(source))

    def test_truncated_frame(self):
        with self.assertRaises(EOFError): p.read_frame(io.BytesIO(b'\x03\xc0short'))

    def test_invalid_size(self):
        for size in (0, 3, 962, 65535):
            with self.subTest(size=size), self.assertRaises(p.ProtocolError):
                p.read_frame(io.BytesIO(struct.pack('!H',size)))

if __name__ == '__main__': unittest.main()
