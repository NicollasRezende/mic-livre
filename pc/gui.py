#!/usr/bin/env python3
"""Native GTK3 desktop interface for Mic Livre."""
import contextlib
import ipaddress
import json
import socket
import subprocess
import sys
import time
from audio import noise_available
from service import ReceiverService
from settings import SettingsStore

def local_addresses():
    try:
        rows=json.loads(subprocess.check_output(['ip','-j','-4','addr','show'],text=True,timeout=2,stderr=subprocess.DEVNULL))
        addresses=[]
        for row in rows:
            name=row.get('ifname','')
            if name.startswith(('lo','docker','br-','veth','tun','wg','virbr','tailscale')): continue
            for address in row.get('addr_info',[]):
                value=address.get('local','')
                if address.get('scope')=='global' and ipaddress.ip_address(value).version==4: addresses.append(value)
        return addresses
    except (OSError,ValueError,subprocess.SubprocessError): return []

def main():
    try:
        import gi
        gi.require_version('Gtk','3.0')
        from gi.repository import Gtk, Gdk, GLib
    except (ImportError,ValueError):
        sys.exit('Interface requer GTK3 e python3-gi (no Ubuntu/Mint: sudo apt install python3-gi gir1.2-gtk-3.0).')
    if not Gtk.init_check()[0]: sys.exit('Não foi possível abrir a interface: execute no terminal da sua sessão gráfica.')

    css=Gtk.CssProvider()
    css.load_from_data(b'''
        window { background: #101722; color: #e6edf5; }
        headerbar { background: #151f2d; border: 0; }
        .card { background: #192535; border-radius: 14px; padding: 18px; }
        .hero { font-size: 27px; font-weight: bold; }
        .subtitle { color: #9eafc3; font-size: 13px; }
        .section { font-weight: bold; font-size: 15px; }
        .code { font: bold 32px monospace; color: #7be2be; }
        .good { color: #7be2be; }
        .danger { color: #ff9c96; }
        .primary { background: #2d846b; color: white; border: 0; padding: 10px 20px; }
        button, entry, combobox { border-radius: 8px; }
        progressbar trough { min-height: 12px; background: #0c121c; border: 0; border-radius: 6px; }
        progressbar progress { background: #55d5aa; border: 0; border-radius: 6px; }
        scale highlight { background: #55d5aa; }
        .log { font: 12px monospace; color: #b5c4d7; }
    ''')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    class Window(Gtk.Window):
        def __init__(self):
            super().__init__(title='Mic Livre')
            self.set_default_size(800,740); self.set_border_width(0)
            self.store=SettingsStore(); self.service=ReceiverService(self.store)
            self.closing=False; self.save_timer=None; self.last_state=None
            header=Gtk.HeaderBar(title='Mic Livre',subtitle='Microfone pelo celular · 0.2.1')
            header.set_show_close_button(True); self.set_titlebar(header)
            self.start_button=Gtk.Button(label='Iniciar receptor')
            self.start_button.get_style_context().add_class('primary')
            self.start_button.connect('clicked',self.toggle); header.pack_end(self.start_button)
            scroll=Gtk.ScrolledWindow(); scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
            self.add(scroll)
            root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=16); root.set_border_width(22)
            scroll.add(root)
            self.state_label=self.label('Seu celular, seu microfone.','hero'); root.pack_start(self.state_label,False,False,0)
            root.pack_start(self.label('Áudio local sem compressão. Sem conta e sem anúncios.','subtitle'),False,False,0)
            pairing=self.card(root)
            top=Gtk.Box(spacing=18); pairing.pack_start(top,False,False,0)
            info=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6); top.pack_start(info,True,True,0)
            info.pack_start(self.label('CONECTAR PELO CELULAR','section'),False,False,0)
            info.pack_start(self.label(socket.gethostname()),False,False,0)
            self.ip_label=self.label('IP: '+(' · '.join(local_addresses()) or 'consulte hostname -I'),'subtitle')
            info.pack_start(self.ip_label,False,False,0)
            info.pack_start(self.label('Abra Mic Livre → Buscar computadores → digite o código.','subtitle'),False,False,0)
            self.code=self.label('—','code'); top.pack_end(self.code,False,False,0)
            self.port_label=self.label('','subtitle'); pairing.pack_start(self.port_label,False,False,0)
            meter=self.card(root)
            line=Gtk.Box(spacing=10); meter.pack_start(line,False,False,0)
            line.pack_start(self.label('NÍVEL DE SAÍDA','section'),True,True,0)
            self.level=self.label('Silêncio','subtitle'); line.pack_end(self.level,False,False,0)
            self.meter=Gtk.ProgressBar(); meter.pack_start(self.meter,False,False,0)
            self.stats=self.label('48 kHz · 16 bits · mono · PCM','subtitle'); meter.pack_start(self.stats,False,False,0)
            row=Gtk.Box(spacing=16); root.pack_start(row,False,False,0)
            left=self.card(row,True); right=self.card(row,True)
            left.pack_start(self.label('AJUSTES DE ÁUDIO','section'),False,False,0)
            self.gain=self.slider(left,'Ganho',-24,24,1,'gain_db',' dB')
            self.check(left,'Silenciar saída','muted')
            self.check(left,'Cortar graves abaixo de 80 Hz','highpass')
            left.pack_start(self.label('Filtros e ganho mudam ao vivo.\nComece em 0 dB para preservar a voz.','subtitle'),False,False,0)
            right.pack_start(self.label('REDUÇÃO DE RUÍDO','section'),False,False,0)
            noise=self.check(right,'DeepFilterNet · opcional','denoise')
            available=noise_available(); noise.set_sensitive(available)
            if not available:
                self.store.update(denoise=False)
                noise.set_active(False)
                right.pack_start(self.label('Biblioteca/modelo não encontrados.','subtitle'),False,False,0)
            self.slider(right,'Atenuação máxima',0,40,1,'attenuation',' dB')
            self.slider(right,'Pós-filtro',0,.05,.005,'beta','',digits=3)
            right.pack_start(self.label('Mais redução pode alterar a voz.\nDesligue para comparar com o original.','subtitle'),False,False,0)
            network=self.card(root)
            network.pack_start(self.label('CONEXÃO E ESTABILIDADE','section'),False,False,0)
            controls=Gtk.Box(spacing=14); network.pack_start(controls,False,False,0)
            controls.pack_start(self.label('Porta TCP'),False,False,0)
            self.port=Gtk.SpinButton.new_with_range(1,65535,1); self.port.set_value(self.store.get().port)
            self.port.connect('value-changed',lambda widget:self.change(port=widget.get_value_as_int()))
            controls.pack_start(self.port,False,False,0)
            controls.pack_start(self.label('Buffer'),False,False,0)
            latency=Gtk.ComboBoxText()
            for value,title in ((20,'20 ms · menor atraso'),(40,'40 ms · equilibrado'),(80,'80 ms · rede instável'),(120,'120 ms · mais margem'),(200,'200 ms · máximo')):
                latency.append(str(value),title)
            latency.set_active_id(str(self.store.get().latency_ms))
            latency.connect('changed',lambda widget:self.change(latency_ms=int(widget.get_active_id())) if widget.get_active_id() else None)
            controls.pack_start(latency,True,True,0)
            network.pack_start(self.label('Porta: reinicie o receptor. Buffer: reconecte o celular. Não é o atraso total medido.','subtitle'),False,False,0)
            self.message=self.label(self.store.error,'log'); root.pack_start(self.message,False,False,0)
            root.pack_start(self.label('Use rede confiável. Descoberta: UDP 45872 · áudio sem criptografia.','subtitle'),False,False,0)
            self.connect('delete-event',self.close_window)
            GLib.timeout_add(100,self.refresh)
            self.show_all(); self.service.start()

        def label(self,text,style=None):
            widget=Gtk.Label(label=text,xalign=0); widget.set_line_wrap(True); widget.set_selectable(True)
            if style: widget.get_style_context().add_class(style)
            return widget

        def card(self,parent,expand=False):
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
            box.get_style_context().add_class('card'); parent.pack_start(box,expand,expand,0)
            return box

        def slider(self,parent,title,low,high,step,key,suffix,digits=0):
            line=self.label(f'{title}: {getattr(self.store.get(),key):.{digits}f}{suffix}','subtitle')
            parent.pack_start(line,False,False,0)
            widget=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,low,high,step)
            widget.set_draw_value(False); widget.set_value(getattr(self.store.get(),key)); widget.set_size_request(230,-1)
            def change(widget):
                value=round(widget.get_value(),digits)
                line.set_text(f'{title}: {value:.{digits}f}{suffix}'); self.change(**{key:value})
            widget.connect('value-changed',change); parent.pack_start(widget,False,False,0)
            return widget

        def check(self,parent,title,key):
            widget=Gtk.CheckButton(label=title); widget.set_active(getattr(self.store.get(),key))
            widget.connect('toggled',lambda widget:self.change(**{key:widget.get_active()}))
            parent.pack_start(widget,False,False,0); return widget

        def change(self,**values):
            self.store.update(**values)
            if self.save_timer: GLib.source_remove(self.save_timer)
            self.save_timer=GLib.timeout_add(500,self.save)

        def save(self):
            self.save_timer=None
            try: self.store.save()
            except OSError as error: self.message.set_text('Não foi possível salvar: '+str(error))
            return False

        def toggle(self,*args):
            if self.service.is_alive(): self.service.stop()
            else: self.service.start()

        def close_window(self,*args):
            self.closing=True; self.service.stop(); self.start_button.set_sensitive(False)
            self.save(); return True

        def refresh(self):
            if self.closing:
                if not self.service.is_alive(): Gtk.main_quit(); return False
                self.state_label.set_text('Encerrando…'); return True
            state=self.service.snapshot(); live=self.service.is_alive()
            self.start_button.set_label('Parar receptor' if live else 'Iniciar receptor')
            self.state_label.set_text(state['status'])
            self.code.set_text(state['code'] if live else '—')
            self.port_label.set_text(f"Porta {state['port']} · "+('Celular: '+state['peer'] if state['connected'] else 'Pronto para busca automática' if live else 'Receptor desligado'))
            self.meter.set_fraction(max(0,min(1,(state['peak_db']+60)/60)))
            self.level.set_text(f"{state['peak_db']:.0f} dBFS" if state['connected'] else 'Sem sinal')
            self.stats.set_text(f"48 kHz · PCM · {state['seconds']:.0f}s · processamento {state['processing_ms']:.2f} ms/quadro · {state['clips']} amostras saturadas")
            self.message.set_text(state['error'] or state['warning'] or self.store.error)
            return True

    Window(); Gtk.main()

if __name__=='__main__': main()
