#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
install_packages=false
install_desktop=false
for option in "$@"; do
  case "$option" in
    --install) install_packages=true ;;
    --desktop) install_desktop=true ;;
    --help|-h) echo 'Uso: ./setup-linux.sh [--install] [--desktop]'; echo '--install instala dependências gratuitas via apt; --desktop cria um atalho no menu.'; exit 0 ;;
    *) echo "Opção desconhecida: $option" >&2; exit 1 ;;
  esac
done
if "$install_packages"; then
  command -v apt-get >/dev/null || { echo 'Instalação automática disponível para Debian/Ubuntu/Mint. Veja README para outras distribuições.' >&2; exit 1; }
  privilege=()
  if [[ $(id -u) != 0 ]]; then privilege=(sudo); fi
  "${privilege[@]}" apt-get update
  "${privilege[@]}" apt-get install -y python3 python3-gi gir1.2-gtk-3.0 pulseaudio-utils adb
fi
command -v python3 >/dev/null || { echo 'Instale Python 3.10+.' >&2; exit 1; }
python3 - <<'PY'
import sys
if sys.version_info<(3,10): sys.exit('É necessário Python 3.10 ou superior.')
try:
 import gi
 gi.require_version('Gtk','3.0')
 from gi.repository import Gtk
except (ImportError,ValueError): sys.exit('Falta GTK3/PyGObject. No Debian/Ubuntu/Mint: ./setup-linux.sh --install')
PY
for command in pactl pacat; do
  command -v "$command" >/dev/null || { echo "Falta $command. No Debian/Ubuntu/Mint: ./setup-linux.sh --install" >&2; exit 1; }
done
if "$install_desktop"; then python3 scripts/install_desktop.py; fi
echo 'Dependências encontradas. Inicie com ./abrir-pc.sh (ou ./iniciar-pc.sh no terminal).'
echo 'Celular: instale apk/mic-livre-0.2.1.apk; sem necessidade de compilar ou pagar.'
