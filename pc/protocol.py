"""Mic Livre v1: network-order header, little-endian PCM payload."""
import hmac
import struct

RATE = 48000
FRAME_BYTES = 960

class ProtocolError(ValueError):
    pass

def read_exact(stream, count, allow_eof=False):
    data = bytearray()
    while len(data) < count:
        chunk = stream.read(count - len(data))
        if not chunk:
            if allow_eof and not data:
                return None
            raise EOFError('Transmissão interrompida no meio de um quadro')
        data.extend(chunk)
    return bytes(data)

def authenticate(stream, code):
    header = read_exact(stream, 16)
    if header[:4] != b'MLV1' or not hmac.compare_digest(header[4:10], code.encode('ascii')):
        raise ProtocolError('Código de conexão incorreto ou protocolo incompatível')
    if struct.unpack('!IBB', header[10:]) != (RATE, 1, 16):
        raise ProtocolError('Formato incompatível: use PCM mono 16 bits 48 kHz')

def read_frame(stream):
    header = read_exact(stream, 2, allow_eof=True)
    if header is None:
        return None
    size, = struct.unpack('!H', header)
    if size == 0 or size > FRAME_BYTES or size % 2:
        raise ProtocolError('Tamanho de quadro inválido')
    return read_exact(stream, size)

def pump(stream, output):
    total = 0
    while True:
        frame = read_frame(stream)
        if frame is None:
            return total
        pending = memoryview(frame)
        while pending:
            written = output.write(pending)
            if written is None or written <= 0:
                raise OSError('Saída de áudio interrompida')
            pending = pending[written:]
        output.flush()
        total += len(frame)
