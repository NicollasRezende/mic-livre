"""Receiver lifecycle independent of the terminal and GTK main loop."""
import contextlib
import secrets
import socket
import subprocess
import threading
import time
from audio import AudioProcessor
from discovery import DiscoveryResponder
from protocol import authenticate, read_frame, ProtocolError
from receiver import VirtualMic

def write_all(output,data):
    pending=memoryview(data)
    while pending:
        count=output.write(pending)
        if not count: raise OSError('Saída de áudio interrompida')
        pending=pending[count:]
    output.flush()

class ReceiverService:
    def __init__(self,settings,bind='0.0.0.0',output=None):
        self.settings=settings; self.bind=bind; self.output=output
        self.lock=threading.Lock(); self.stop_event=threading.Event()
        self.thread=None; self.connection=None; self.server=None
        self.state={'status':'Parado','error':'','warning':'','fatal':False,'connected':False,
            'code':'—','port':settings.get().port,'peer':'','peak_db':-96.0,'rms_db':-96.0,
            'clips':0,'seconds':0.0,'processing_ms':0.0}

    def update(self,**values):
        with self.lock: self.state.update(values)

    def snapshot(self):
        with self.lock: return dict(self.state)

    def is_alive(self): return self.thread is not None and self.thread.is_alive()

    def start(self,code=None):
        if self.is_alive(): return
        code=code or f'{secrets.randbelow(1000000):06d}'
        if len(code)!=6 or not code.isascii() or not code.isdigit(): raise ValueError('Código inválido')
        self.stop_event.clear()
        self.update(status='Iniciando…',error='',warning='',fatal=False,code=code,port=self.settings.get().port)
        self.thread=threading.Thread(target=self.run,name='mic-livre-receiver')
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        # shutdown unblocks a makefile read even while that file retains the fd.
        connection=self.connection
        if connection:
            with contextlib.suppress(OSError): connection.shutdown(socket.SHUT_RDWR)

    def join(self,timeout=None):
        if self.thread: self.thread.join(timeout)

    def run(self):
        discovery=None
        try:
            config=self.settings.get()
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:
                self.server=server
                server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
                server.bind((self.bind,config.port)); server.listen(2); server.settimeout(.4)
                discovery=DiscoveryResponder(config.port,lambda:self.snapshot()['connected'],
                    lambda message:self.update(warning=message))
                discovery.start()
                self.update(status='Aguardando celular',error='')
                while not self.stop_event.is_set():
                    try: connection,address=server.accept()
                    except socket.timeout: continue
                    self.connection=connection
                    with connection:
                        if self.stop_event.is_set(): break
                        connection.settimeout(5)
                        connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                        try:
                            with connection.makefile('rb',buffering=0) as stream:
                                authenticate(stream,self.snapshot()['code'])
                                session=self.settings.get()
                                with (open(self.output,'wb') if self.output else VirtualMic(session.latency_ms)) as output, AudioProcessor() as processor:
                                    connection.sendall(b'OKAY')
                                    self.update(status='Recebendo áudio',connected=True,peer=address[0],error='',clips=0,seconds=0)
                                    self.receive(stream,output,processor)
                        except (OSError,EOFError,ProtocolError,RuntimeError,subprocess.SubprocessError) as error:
                            if not self.stop_event.is_set():
                                self.update(error=str(error))
                                with contextlib.suppress(OSError): connection.sendall(b'FAIL')
                        finally:
                            self.connection=None
                            self.update(connected=False,status='Aguardando celular',peak_db=-96,rms_db=-96)
        except (OSError,subprocess.SubprocessError) as error:
            if not self.stop_event.is_set(): self.update(error=str(error),fatal=True)
        finally:
            if discovery: discovery.stop()
            self.server=None; self.connection=None
            self.update(status='Erro ao iniciar' if self.snapshot()['fatal'] else 'Parado',connected=False,peak_db=-96,rms_db=-96)

    def receive(self,stream,output,processor):
        pending=bytearray(); total=0; publish=time.monotonic(); cost=0; count=0
        while not self.stop_event.is_set():
            frame=read_frame(stream)
            if frame is None: break
            pending.extend(frame)
            while len(pending)>=960:
                raw=bytes(pending[:960]); del pending[:960]
                start=time.perf_counter()
                result=processor.process(raw,self.settings.get())
                cost+=(time.perf_counter()-start)*1000; count+=1
                write_all(output,result); total+=len(raw)
                now=time.monotonic()
                if now-publish>=.1:
                    self.update(peak_db=processor.peak_db,rms_db=processor.rms_db,clips=processor.clips,
                        seconds=total/96000,processing_ms=cost/max(1,count))
                    publish=now; cost=0; count=0
        if pending and not self.stop_event.is_set():
            write_all(output,processor.process(bytes(pending),self.settings.get())); total+=len(pending)
        self.update(seconds=total/96000)
