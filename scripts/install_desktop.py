"""Create a per-user launcher pointing to this checkout, without absolute paths in Git."""
import os
from pathlib import Path

def desktop_text(launcher):
    escaped=str(launcher).replace('%','%%').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
    return ('[Desktop Entry]\nType=Application\nName=Mic Livre\n'
        'Comment=Seu celular como microfone do PC, sem anúncios\n'
        f'Exec="{escaped}"\nIcon=audio-input-microphone\nTerminal=false\nCategories=AudioVideo;Audio;\n')

def main():
    root=Path(__file__).resolve().parents[1]
    destination=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local'/'share'))/'applications'/'mic-livre.desktop'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(desktop_text(root/'abrir-pc.sh'))
    print('Atalho criado:',destination)

if __name__=='__main__': main()
