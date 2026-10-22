package br.com.miclivre;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.text.InputFilter;
import android.text.InputType;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;

public class MainActivity extends Activity {
    private static final int BG=0xff101722, CARD=0xff192535, INK=0xffe6edf5, DIM=0xff9eafc3, GREEN=0xff7be2be;
    private SharedPreferences prefs;
    private EditText host,port,code;
    private TextView status,level,selected,searchStatus,gainLabel;
    private Button connect,searchButton;
    private LinearLayout devices,manual;
    private LevelMeter meter;
    private Spinner source;
    private Discovery discovery;
    private boolean scanned;
    private final Handler handler=new Handler();
    private final Runnable refresh=new Runnable() {
        public void run() {
            status.setText(MicService.status);
            connect.setEnabled(!MicService.active); connect.setAlpha(MicService.active?.45f:1f);
            searchButton.setEnabled(!MicService.active && discovery==null);
            source.setEnabled(!MicService.active);
            float db=MicService.active?MicService.levelDb:-96;
            meter.setLevel(db);
            level.setText(MicService.active?String.format(java.util.Locale.getDefault(),"%.0f dBFS · %d amostras saturadas",db,MicService.clips):"Microfone desligado");
            handler.postDelayed(this,100);
        }
    };
    private int dp(int n) {return Math.round(n*getResources().getDisplayMetrics().density);}
    private GradientDrawable background(int color,int radius) {
        GradientDrawable drawable=new GradientDrawable();drawable.setColor(color);drawable.setCornerRadius(dp(radius));return drawable;
    }
    private TextView text(String value,int size,int color) {
        TextView widget=new TextView(this);widget.setText(value);widget.setTextSize(size);widget.setTextColor(color);
        widget.setPadding(0,dp(5),0,dp(5));return widget;
    }
    private LinearLayout card(LinearLayout parent) {
        LinearLayout box=new LinearLayout(this);box.setOrientation(1);box.setPadding(dp(18),dp(14),dp(18),dp(16));
        box.setBackground(background(CARD,18));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);params.bottomMargin=dp(14);parent.addView(box,params);return box;
    }
    private void heading(LinearLayout parent,String title) {
        TextView label=text(title,12,DIM);label.setLetterSpacing(.1f);label.setTypeface(null,Typeface.BOLD);parent.addView(label);
    }
    private Button button(LinearLayout parent,String title,boolean primary) {
        Button widget=new Button(this);widget.setText(title);widget.setAllCaps(false);widget.setTextSize(16);
        widget.setTextColor(primary?BG:INK);widget.setBackgroundTintList(ColorStateList.valueOf(primary?GREEN:0xff293a50));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,dp(54));params.topMargin=dp(7);parent.addView(widget,params);return widget;
    }
    private EditText field(LinearLayout parent,String title,String value,int type) {
        parent.addView(text(title,13,DIM));EditText widget=new EditText(this);widget.setSingleLine();widget.setTextSize(18);
        widget.setTextColor(INK);widget.setHintTextColor(DIM);widget.setInputType(type);widget.setText(value);
        widget.setBackgroundTintList(ColorStateList.valueOf(GREEN));parent.addView(widget,new LinearLayout.LayoutParams(-1,dp(50)));return widget;
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);prefs=getSharedPreferences("connection",0);
        MicService.gainDb=prefs.getFloat("gain",0);MicService.muted=prefs.getBoolean("muted",false);
        getWindow().setStatusBarColor(BG);getWindow().setNavigationBarColor(BG);
        ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(BG);scroll.setFillViewport(true);
        LinearLayout root=new LinearLayout(this);root.setOrientation(1);root.setPadding(dp(20),dp(22),dp(20),dp(24));scroll.addView(root);setContentView(scroll);
        TextView title=text("Mic Livre",34,INK);title.setTypeface(null,Typeface.BOLD);root.addView(title);
        TextView subtitle=text("SEU CELULAR. SEU MICROFONE.  /  0.2.1",11,DIM);subtitle.setLetterSpacing(.08f);root.addView(subtitle);
        View space=new View(this);root.addView(space,new LinearLayout.LayoutParams(1,dp(16)));

        LinearLayout signal=card(root);heading(signal,"SINAL DO MICROFONE");
        status=text(MicService.status,19,GREEN);signal.addView(status);
        meter=new LevelMeter(this);LinearLayout.LayoutParams meterParams=new LinearLayout.LayoutParams(-1,dp(20));meterParams.topMargin=dp(12);meterParams.bottomMargin=dp(8);signal.addView(meter,meterParams);
        level=text("Microfone desligado",12,DIM);signal.addView(level);
        signal.addView(text("48 kHz · 16 bits · mono · sem compressão",12,DIM));

        LinearLayout connection=card(root);heading(connection,"1  /  ENCONTRE SEU COMPUTADOR");
        selected=text(prefs.getString("host","").isEmpty()?"Nenhum PC selecionado":"Último PC: "+prefs.getString("host",""),17,INK);connection.addView(selected);
        searchButton=button(connection,"Buscar computadores",false);searchButton.setOnClickListener(v->search());
        searchStatus=text("Mesma rede Wi-Fi do computador.",12,DIM);connection.addView(searchStatus);
        devices=new LinearLayout(this);devices.setOrientation(1);connection.addView(devices);
        Button manualButton=button(connection,"Conexão manual ▾",false);
        manual=new LinearLayout(this);manual.setOrientation(1);connection.addView(manual);
        host=field(manual,"IP do PC",prefs.getString("host",""),InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI);host.setHint("192.168.1.10");
        port=field(manual,"Porta TCP",prefs.getString("port","45871"),InputType.TYPE_CLASS_NUMBER);
        manual.setVisibility(View.GONE);manualButton.setOnClickListener(v->manual.setVisibility(manual.getVisibility()==View.VISIBLE?View.GONE:View.VISIBLE));

        LinearLayout pairing=card(root);heading(pairing,"2  /  CONECTE COM SEGURANÇA");
        code=field(pairing,"Código de seis dígitos mostrado no PC",state==null?"":state.getString("code",""),InputType.TYPE_CLASS_NUMBER);
        code.setHint("000000");code.setFilters(new InputFilter[]{new InputFilter.LengthFilter(6)});code.setLetterSpacing(.25f);code.setTextSize(27);
        connect=button(pairing,"Iniciar microfone",true);
        connect.setOnClickListener(v->{
            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},1);return;
            }
            startMic();
        });
        Button stop=button(pairing,"Parar transmissão",false);stop.setOnClickListener(v->stopService(new Intent(this,MicService.class)));

        LinearLayout audio=card(root);heading(audio,"AJUSTES DE CAPTURA");
        Switch mute=new Switch(this);mute.setText("Silenciar microfone");mute.setTextColor(INK);mute.setTextSize(16);mute.setPadding(0,dp(12),0,dp(12));mute.setChecked(MicService.muted);
        mute.setOnCheckedChangeListener((widget,checked)->{MicService.muted=checked;prefs.edit().putBoolean("muted",checked).apply();});audio.addView(mute);
        gainLabel=text("Ganho: "+Math.round(MicService.gainDb)+" dB",14,INK);audio.addView(gainLabel);
        SeekBar gain=new SeekBar(this);gain.setMax(36);gain.setProgress(Math.round(MicService.gainDb)+12);gain.setProgressTintList(ColorStateList.valueOf(GREEN));gain.setThumbTintList(ColorStateList.valueOf(GREEN));
        gain.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            public void onProgressChanged(SeekBar bar,int value,boolean user){MicService.gainDb=value-12;gainLabel.setText("Ganho: "+(value-12)+" dB");if(user)prefs.edit().putFloat("gain",value-12).apply();}
            public void onStartTrackingTouch(SeekBar bar){}public void onStopTrackingTouch(SeekBar bar){}
        });audio.addView(gain);
        audio.addView(text("Fonte do microfone · altere antes de conectar",13,DIM));
        source=new Spinner(this);
        String[] options={"Fidelidade · sem processamento quando possível","Voz · reconhecimento de fala","Chamada · cancelamento de eco do Android","Microfone · padrão do aparelho"};
        ArrayAdapter<String> adapter=new ArrayAdapter<String>(this,android.R.layout.simple_spinner_item,options){
            @Override public View getView(int position,View convert,android.view.ViewGroup parent){TextView view=(TextView)super.getView(position,convert,parent);view.setTextColor(INK);view.setTextSize(13);return view;}
        };
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);source.setAdapter(adapter);source.setSelection(prefs.getInt("source",0));audio.addView(source);
        source.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onItemSelected(AdapterView<?> p,View v,int position,long id){prefs.edit().putInt("source",position).apply();}public void onNothingSelected(AdapterView<?> p){}});
        audio.addView(text("Comece em 0 dB. Ganho alto pode saturar. Os filtros de ruído e graves ficam na janela do PC, onde você pode comparar com o áudio original.",12,DIM));
        root.addView(text("Sem anúncios, sem conta e sem nuvem. Use uma rede confiável: o áudio local não é criptografado. A notificação permite parar com a tela apagada.",12,DIM));
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},2);
    }
    private void search() {
        if(discovery!=null || MicService.active)return;
        devices.removeAllViews();searchStatus.setText("Procurando PCs por 4 segundos…");searchButton.setEnabled(false);
        final Discovery task=new Discovery();discovery=task;final int[] found={0};
        final String lastHost=host.getText().toString().trim();
        new Thread(()->task.search(lastHost,new Discovery.Listener(){
            public void found(String name,String ip,int number,boolean busy){handler.post(()->{
                if(discovery!=task)return;found[0]++;
                Button choice=button(devices,name+"\n"+ip+(busy?" · em uso":""),false);choice.setTextSize(13);
                choice.setOnClickListener(v->{host.setText(ip);port.setText(String.valueOf(number));selected.setText(name+" · "+ip);saveAddress();code.requestFocus();toast("PC selecionado. Digite o código mostrado nele.");});
            });}
            public void done(String error){handler.post(()->{
                if(discovery!=task)return;discovery=null;searchButton.setEnabled(true);
                searchStatus.setText(!error.isEmpty()?error:found[0]>0?"Toque no computador para selecionar.":"Nenhum PC encontrado. Abra o receptor, confira o Wi-Fi ou use conexão manual.");
            });}
        }),"MicLivre-discovery").start();
    }
    private void saveAddress(){prefs.edit().putString("host",host.getText().toString().trim()).putString("port",port.getText().toString()).apply();}
    private void startMic(){
        if(MicService.active)return;
        String address=host.getText().toString().trim(),secret=code.getText().toString();int number;
        try{number=Integer.parseInt(port.getText().toString());}catch(NumberFormatException e){toast("Confira a porta");return;}
        if(address.isEmpty() || number<1 || number>65535 || !secret.matches("[0-9]{6}")){manual.setVisibility(View.VISIBLE);toast("Selecione um PC e digite o código de seis dígitos");return;}
        saveAddress();selected.setText("PC: "+address);
        Intent intent=new Intent(this,MicService.class).putExtra("host",address).putExtra("port",number).putExtra("code",secret).putExtra("source",source.getSelectedItemPosition());
        try{startForegroundService(intent);connect.setEnabled(false);((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(code.getWindowToken(),0);}
        catch(RuntimeException e){toast("Não foi possível iniciar: "+e.getMessage());}
    }
    private void toast(String message){Toast.makeText(this,message,Toast.LENGTH_LONG).show();}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==1 && results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)startMic();}
    @Override public void onSaveInstanceState(Bundle state){state.putString("code",code.getText().toString());super.onSaveInstanceState(state);}
    @Override protected void onResume(){super.onResume();handler.post(refresh);if(!scanned && !MicService.active){scanned=true;search();}}
    @Override protected void onPause(){handler.removeCallbacks(refresh);if(discovery!=null){discovery.cancel();discovery=null;searchStatus.setText("Busca pausada. Toque em Buscar para repetir.");}super.onPause();}
}
