"""Exercise the installed open C backend; skipped on machines without it."""
import random
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from audio import AudioProcessor,noise_available
from settings import Settings

@unittest.skipUnless(noise_available(),'DeepFilterNet não instalado')
class NoiseIntegrationTests(unittest.TestCase):
    def test_real_c_backend_processes_pcm_and_can_return_to_bypass(self):
        rng=random.Random(7)
        original=struct.pack('<480h',*(rng.randint(-5000,5000) for _ in range(480)))
        with AudioProcessor() as processor:
            outputs=[processor.process(original,Settings(denoise=True)) for _ in range(50)]
            self.assertTrue(all(len(output)==960 for output in outputs))
            self.assertNotEqual(outputs[-1],original)
            self.assertEqual(processor.process(original,Settings()),original)
            self.assertIsNone(processor.filter)
