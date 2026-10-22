"""Validated, immutable settings shared by audio and UI threads."""
from dataclasses import asdict, dataclass, replace
import json
import math
import os
from pathlib import Path
import threading

@dataclass(frozen=True)
class Settings:
    port: int = 45871
    latency_ms: int = 40
    gain_db: float = 0.0
    muted: bool = False
    highpass: bool = False
    denoise: bool = False
    attenuation: float = 15.0
    beta: float = 0.02

    def validate(self):
        for name, low, high in (('port',1,65535),('latency_ms',20,200),('gain_db',-24,24),('attenuation',0,40),('beta',0,0.05)):
            value=getattr(self,name)
            if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
                raise ValueError(f'Valor inválido em {name}')
        if type(self.port) is not int or type(self.latency_ms) is not int:
            raise ValueError('Porta e buffer devem ser inteiros')
        for name in ('muted','highpass','denoise'):
            if type(getattr(self,name)) is not bool: raise ValueError(f'{name} deve ser booleano')
        return self

class SettingsStore:
    def __init__(self,path=None):
        self.path=Path(path) if path else Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'mic-livre'/'settings.json'
        self.lock=threading.Lock()
        self.value=Settings()
        self.error=''
        if self.path.exists():
            try:
                values=json.loads(self.path.read_text())
                self.value=Settings(**values).validate()
            except (OSError,ValueError,TypeError) as error:
                self.error=f'Configuração anterior inválida: {error}. Usando padrões.'

    def get(self):
        with self.lock: return self.value

    def update(self,**changes):
        with self.lock:
            self.value=replace(self.value,**changes).validate()
            return self.value

    def save(self):
        with self.lock:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(asdict(self.value),indent=2)+'\n')
            temporary.replace(self.path)
