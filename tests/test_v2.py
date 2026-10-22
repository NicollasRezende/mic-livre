import json
import math
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc'))
from settings import Settings, SettingsStore
from audio import AudioProcessor, DeepFilter
from discovery import make_offer, parse_query, QUERY

def pcm(values): return struct.pack('<'+'h'*len(values),*values)
def samples(data): return struct.unpack('<'+'h'*(len(data)//2),data)

class SettingsTests(unittest.TestCase):
    def test_invalid_values_rejected(self):
        for changes in ({'gain_db':60},{'port':0},{'latency_ms':2},{'denoise':'yes'},{'gain_db':float('nan')},{'beta':1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError): Settings(**changes).validate()

    def test_atomic_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            store=SettingsStore(path); store.update(gain_db=6.0,highpass=True); store.save()
            loaded=SettingsStore(path)
            self.assertEqual(loaded.get().gain_db,6)
            self.assertTrue(loaded.get().highpass)
            with self.assertRaises(ValueError): loaded.update(gain_db=100)
            self.assertEqual(loaded.get().gain_db,6)

class AudioTests(unittest.TestCase):
    def test_incompatible_noise_library_reports_readable_error(self):
        with patch('audio.noise_available',return_value=True),patch('audio.c.CDLL',return_value=object()):
            with self.assertRaisesRegex(RuntimeError,'incompatível'): DeepFilter()

    def test_bypass_is_bit_exact(self):
        data=pcm([-32768,-103,0,103,32767]*96)
        with AudioProcessor() as proc: self.assertEqual(proc.process(data,Settings()),data)

    def test_gain_clips_without_wrapping(self):
        with AudioProcessor() as proc:
            result=samples(proc.process(pcm([20000,-20000,1000]),Settings(gain_db=6.020599913)))
            self.assertEqual(result,(32767,-32768,2000))
            self.assertEqual(proc.clips,2)

    def test_mute_outputs_silence(self):
        with AudioProcessor() as proc:
            self.assertEqual(proc.process(pcm([1000]*480),Settings(muted=True)),bytes(960))

    def test_highpass_rejects_dc(self):
        with AudioProcessor() as proc:
            for _ in range(20): out=proc.process(pcm([10000]*480),Settings(highpass=True))
            self.assertLess(max(abs(v) for v in samples(out)),5)

class DiscoveryTests(unittest.TestCase):
    def test_query_validation(self):
        self.assertEqual(parse_query(QUERY+b'abc123'), 'abc123')
        self.assertIsNone(parse_query(b'bad'))
        self.assertIsNone(parse_query(QUERY+b'x'*100))

    def test_offer_never_leaks_code(self):
        offer=json.loads(make_offer('abc123','Meu PC',45871,False))
        self.assertEqual(offer['magic'],'MICLIVRE1')
        self.assertEqual(offer['nonce'],'abc123')
        self.assertEqual(offer['port'],45871)
        self.assertNotIn('code',offer)
