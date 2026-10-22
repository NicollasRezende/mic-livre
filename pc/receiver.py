#!/usr/bin/env python3
"""Receptor local do Mic Livre. Requer pactl e pacat para microfone virtual."""
import argparse
import contextlib
import os
import secrets
import select
import shutil
import signal
import socket
import subprocess
import sys
from protocol import authenticate, pump, ProtocolError

def pactl(*args):
    return subprocess.check_output(['pactl', *args], text=True, stderr=subprocess.PIPE, timeout=5).strip()

class PlaybackOutput:
    """Bounded writes keep a stopped audio server from pinning the session."""
    def __init__(self, pipe):
        self.fd = pipe.fileno()
        os.set_blocking(self.fd, False)

    def write(self, data):
        if not select.select([], [self.fd], [], 3)[1]:
            raise TimeoutError('Saída de áudio travada por três segundos')
        try:
            return os.write(self.fd, data)
        except BlockingIOError as error:
            raise TimeoutError('Saída de áudio indisponível') from error

    def flush(self):
        pass

class VirtualMic:
    def __init__(self, latency_ms=40):
        self.modules = []
        self.process = None
        self.latency_ms=latency_ms

    def __enter__(self):
        suffix = str(os.getpid())
        self.sink = 'mic_livre_sink_' + suffix
        self.source = 'mic_livre_' + suffix
        try:
            self.modules.append(pactl('load-module', 'module-null-sink',
                'sink_name='+self.sink, 'rate=48000', 'channels=1',
                'sink_properties=device.description=Mic_Livre_Interno'))
            self.modules.append(pactl('load-module', 'module-remap-source',
                'master='+self.sink+'.monitor', 'source_name='+self.source,
                'source_properties=device.description=Mic_Livre', 'channels=1', 'remix=no'))
            self.process = subprocess.Popen(['pacat','--playback','--raw','--format=s16le',
                '--rate=48000','--channels=1',f'--latency-msec={self.latency_ms}','--device='+self.sink],
                stdin=subprocess.PIPE, bufsize=0)
            return PlaybackOutput(self.process.stdin)
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def __exit__(self,*exc):
        if self.process:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process.stdin.close()
        for module in reversed(self.modules):
            with contextlib.suppress(Exception): pactl('unload-module',module)
        self.modules.clear()

def main():
    from service import ReceiverService
    from settings import SettingsStore
    import time
    parser = argparse.ArgumentParser(description='Mic Livre — microfone Android por Wi-Fi')
    parser.add_argument('--bind',default='0.0.0.0',help='Endereço de escuta (padrão: todas as interfaces IPv4)')
    parser.add_argument('--port',type=int,default=45871)
    parser.add_argument('--code',help='Código de seis dígitos (padrão: aleatório)')
    parser.add_argument('--output',help='Gravar PCM bruto em arquivo em vez de criar microfone virtual')
    parser.add_argument('--latency',type=int,default=40,help='Buffer de reprodução em ms: 20 a 200')
    args = parser.parse_args()
    code = args.code or f'{secrets.randbelow(1000000):06d}'
    if len(code)!=6 or not code.isascii() or not code.isdigit(): parser.error('Código deve ter seis dígitos')
    if not 1 <= args.port <= 65535: parser.error('Porta deve estar entre 1 e 65535')
    if not 20 <= args.latency <= 200: parser.error('Buffer deve estar entre 20 e 200 ms')
    if not args.output:
        for command in ('pactl','pacat'):
            if not shutil.which(command): parser.error('Instale pulseaudio-utils: falta '+command)
    store=SettingsStore()
    store.update(port=args.port,latency_ms=args.latency)
    service=ReceiverService(store,args.bind,args.output)
    service.start(code)
    signal.signal(signal.SIGTERM,lambda *_: service.stop())
    print(f'\nMIC LIVRE • PCM 48 kHz / 16 bits / mono\nPorta: {args.port}   Código: {code}',flush=True)
    print('Abra o app e toque em Buscar computadores. Ctrl+C encerra.\n',flush=True)
    last=''
    try:
        while service.is_alive():
            state=service.snapshot()
            message=state['status']+' '+state['error']
            if message!=last: print(message,flush=True); last=message
            time.sleep(.25)
    except KeyboardInterrupt:
        service.stop()
    finally:
        service.stop(); service.join()
    if service.snapshot()['fatal']: parser.exit(1,service.snapshot()['error']+'\n')

if __name__ == '__main__': main()
