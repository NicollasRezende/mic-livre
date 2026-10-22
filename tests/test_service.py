import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pc'))
from audio import AudioProcessor
from service import ReceiverService
from settings import SettingsStore

class ServiceTests(unittest.TestCase):
    def service(self,directory): return ReceiverService(SettingsStore(Path(directory)/'settings.json'))

    def test_partial_network_frames_are_assembled_without_sample_loss(self):
        with tempfile.TemporaryDirectory() as directory,AudioProcessor() as processor:
            service=self.service(directory); output=io.BytesIO()
            pcm=struct.pack('<500h',*range(500))
            # Protocol permits variable-size even frames, including a final short one.
            wire=b''.join(struct.pack('!H',len(chunk))+chunk for chunk in (pcm[:100],pcm[100:600],pcm[600:]))
            service.receive(io.BytesIO(wire),output,processor)
            self.assertEqual(output.getvalue(),pcm)
            self.assertAlmostEqual(service.snapshot()['seconds'],500/48000)

    def test_live_mute_is_applied_before_output(self):
        with tempfile.TemporaryDirectory() as directory,AudioProcessor() as processor:
            service=self.service(directory);service.settings.update(muted=True)
            pcm=struct.pack('<480h',*([10000]*480));output=io.BytesIO()
            service.receive(io.BytesIO(struct.pack('!H',960)+pcm),output,processor)
            self.assertEqual(output.getvalue(),bytes(960))

    def test_stop_prevents_further_audio(self):
        with tempfile.TemporaryDirectory() as directory,AudioProcessor() as processor:
            service=self.service(directory);service.stop();output=io.BytesIO()
            service.receive(io.BytesIO(b'garbage'),output,processor)
            self.assertEqual(output.getvalue(),b'')

    def test_settings_failure_keeps_defaults_and_reports_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json';path.write_text('{bad json')
            store=SettingsStore(path)
            self.assertEqual(store.get().port,45871)
            self.assertTrue(store.error)
