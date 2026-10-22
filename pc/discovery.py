"""Small LAN-only discovery response; pairing secrets are never advertised."""
import json
import re
import socket
import threading
import time

PORT=45872
QUERY=b'MICLIVRE_DISCOVER_V1 '

def parse_query(data):
    if not data.startswith(QUERY): return None
    nonce=data[len(QUERY):]
    if not re.fullmatch(rb'[a-zA-Z0-9-]{6,48}',nonce): return None
    return nonce.decode('ascii')

def make_offer(nonce,name,port,busy):
    return json.dumps({'magic':'MICLIVRE1','nonce':nonce,'name':name[:64],
        'port':port,'busy':bool(busy),'version':'0.2.1'},ensure_ascii=False).encode('utf-8')

class DiscoveryResponder:
    def __init__(self,port,busy=lambda:False,on_error=lambda message:None):
        self.port=port; self.busy=busy; self.on_error=on_error
        self.stop_event=threading.Event(); self.thread=None; self.socket=None

    def start(self):
        self.thread=threading.Thread(target=self.run,name='mic-livre-discovery',daemon=True)
        self.thread.start()

    def run(self):
        try:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                self.socket=sock
                sock.settimeout(.5)
                sock.bind(('0.0.0.0',PORT))
                last={}
                while not self.stop_event.is_set():
                    try: data,address=sock.recvfrom(256)
                    except socket.timeout: continue
                    nonce=parse_query(data)
                    if nonce is None: continue
                    now=time.monotonic()
                    if now-last.get(address[0],0)<.2: continue
                    if len(last)>512: last.clear()
                    last[address[0]]=now
                    sock.sendto(make_offer(nonce,socket.gethostname(),self.port,self.busy()),address)
        except OSError as error:
            if not self.stop_event.is_set(): self.on_error('Busca automática indisponível: '+str(error))
        finally: self.socket=None

    def stop(self):
        self.stop_event.set()
        if self.thread: self.thread.join(timeout=1)
