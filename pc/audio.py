"""Optional DSP; defaults keep the previously tested PCM signal bit-exact."""
from array import array
import ctypes as c
import math
import os
from pathlib import Path
import sys

def noise_paths():
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'mic-livre'/'deepfilter'
    candidates=[(data/'libdf.so',data/'DeepFilterNet3_onnx.tar.gz'),
        (Path('/usr/local/lib/libdf.so'),Path('/usr/local/share/deepfilternet/DeepFilterNet3_onnx.tar.gz')),
        (Path('/usr/lib/micstream/libdf.so'),Path('/usr/share/micstream/DeepFilterNet3_onnx.tar.gz'))]
    default=next((pair for pair in candidates if all(path.is_file() for path in pair)),candidates[0])
    library=Path(os.environ.get('MICLIVRE_DF_LIB',default[0]))
    model=Path(os.environ.get('MICLIVRE_DF_MODEL',default[1]))
    return library,model

def noise_available():
    return all(path.is_file() for path in noise_paths())

class DeepFilter:
    def __init__(self):
        library,model=noise_paths()
        if not noise_available(): raise RuntimeError('DeepFilterNet não encontrado neste PC')
        self.lib=c.CDLL(str(library))
        try:
            for symbol in ('df_create','df_get_frame_length','df_process_frame','df_set_atten_lim','df_set_post_filter_beta','df_free'):
                getattr(self.lib,symbol)
        except AttributeError as error:
            raise RuntimeError('Biblioteca DeepFilterNet incompatível: falta uma função da API C') from error
        self.lib.df_create.argtypes=[c.c_char_p,c.c_float,c.c_char_p]
        self.lib.df_create.restype=c.c_void_p
        self.lib.df_get_frame_length.argtypes=[c.c_void_p]; self.lib.df_get_frame_length.restype=c.c_size_t
        self.lib.df_process_frame.argtypes=[c.c_void_p,c.POINTER(c.c_float),c.POINTER(c.c_float)]
        self.lib.df_process_frame.restype=c.c_float
        self.lib.df_set_atten_lim.argtypes=[c.c_void_p,c.c_float]; self.lib.df_set_atten_lim.restype=None
        self.lib.df_set_post_filter_beta.argtypes=[c.c_void_p,c.c_float]; self.lib.df_set_post_filter_beta.restype=None
        self.lib.df_free.argtypes=[c.c_void_p]; self.lib.df_free.restype=None
        self.state=self.lib.df_create(os.fsencode(model),15.0,None)
        if not self.state: raise RuntimeError('Não foi possível iniciar DeepFilterNet')
        if self.lib.df_get_frame_length(self.state)!=480:
            self.close(); raise RuntimeError('Modelo DeepFilterNet incompatível: esperado frame de 480 amostras')
        self.input=(c.c_float*480)(); self.output=(c.c_float*480)()
        self.parameters=None

    def process(self,values,attenuation,beta):
        if self.parameters!=(attenuation,beta):
            self.lib.df_set_atten_lim(self.state,attenuation)
            self.lib.df_set_post_filter_beta(self.state,beta)
            self.parameters=(attenuation,beta)
        count=len(values)
        for i in range(480): self.input[i]=values[i] if i<count else 0.0
        self.lib.df_process_frame(self.state,self.input,self.output)
        return list(self.output)[:count]

    def close(self):
        if self.state: self.lib.df_free(self.state); self.state=None

class AudioProcessor:
    def __init__(self):
        self.filter=None; self.x=0.0; self.y=0.0; self.was_highpass=False
        self.peak_db=-96.0; self.rms_db=-96.0; self.clips=0

    def __enter__(self): return self
    def __exit__(self,*args):
        if self.filter: self.filter.close(); self.filter=None

    def process(self,pcm,settings):
        if len(pcm)%2 or len(pcm)>960: raise ValueError('Frame PCM inválido')
        integers=array('h'); integers.frombytes(pcm)
        if sys.byteorder!='little': integers.byteswap()
        values=[v/32768.0 for v in integers]
        if settings.highpass:
            if not self.was_highpass: self.x=self.y=0.0
            # First-order 80 Hz high-pass, retaining state across frames.
            alpha=math.exp(-2*math.pi*80/48000)
            for i,x in enumerate(values):
                y=alpha*(self.y+x-self.x); self.x=x; self.y=y; values[i]=y
        self.was_highpass=settings.highpass
        if settings.denoise:
            if self.filter is None: self.filter=DeepFilter()
            values=self.filter.process(values,settings.attenuation,settings.beta)
        elif self.filter:
            self.filter.close(); self.filter=None
        gain=10**(settings.gain_db/20)
        values=[v*gain for v in values]
        self.clips+=sum(v>32767/32768 or v< -1 for v in values)
        if settings.muted: values=[0.0]*len(values)
        peak=max((abs(v) for v in values),default=0)
        rms=math.sqrt(sum(v*v for v in values)/max(1,len(values)))
        self.peak_db=max(-96,20*math.log10(max(peak,1e-6)))
        self.rms_db=max(-96,20*math.log10(max(rms,1e-6)))
        if not (settings.highpass or settings.denoise or settings.gain_db or settings.muted): return pcm
        output=array('h',(max(-32768,min(32767,round(v*32768))) for v in values))
        if sys.byteorder!='little': output.byteswap()
        return output.tobytes()
