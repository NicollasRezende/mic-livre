package br.com.miclivre;

import android.app.*;
import android.content.Intent;
import android.media.*;
import android.media.audiofx.*;
import android.os.*;
import java.io.*;
import java.net.*;
import java.util.ArrayList;
import java.util.concurrent.*;

public class MicService extends Service {
    public static volatile String status = "Pronto para conectar";
    public static volatile boolean active = false;
    public static volatile boolean muted = false;
    public static volatile float gainDb = 0;
    public static volatile float levelDb = -96;
    public static volatile long clips = 0;
    private static MicService owner;
    private volatile boolean running;
    private volatile Socket socket;
    private volatile AudioRecord recorder;
    private PowerManager.WakeLock wake;
    private Thread worker;
    private int latestStartId;
    private final ArrayList<AudioEffect> effects = new ArrayList<>();

    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent,int flags,int id) {
        latestStartId=id;
        if (intent==null || "STOP".equals(intent.getAction())) { stopSelf(); return START_NOT_STICKY; }
        if (owner!=null) {
            if(owner!=this) stopSelfResult(id);
            return START_NOT_STICKY;
        }
        owner=this;
        running=true; active=true; clips=0; levelDb=-96; status="Conectando ao computador…";
        try {
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel("mic","Microfone ativo",NotificationManager.IMPORTANCE_LOW));
        PendingIntent open = PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this,1,new Intent(this,MicService.class).setAction("STOP"),PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(this,"mic").setContentTitle("Mic Livre")
            .setContentText("Microfone em uso — toque em Parar para encerrar")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentIntent(open).setOngoing(true)
            .addAction(new Notification.Action.Builder(null,"Parar",stop).build()).build();
        startForeground(1,notification);
        wake=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"miclivre:capture");
        wake.acquire();
        worker=new Thread(() -> transmit(intent,id),"MicLivre-session"); worker.start();
        } catch(RuntimeException error) {
            running=false;active=false;owner=null;status="Não foi possível iniciar: "+error.getMessage();
            if(wake!=null && wake.isHeld())wake.release();
            stopSelfResult(id);
        }
        return START_NOT_STICKY;
    }
    private void disableEffects(int session) {
        try { if (AutomaticGainControl.isAvailable()) { AutomaticGainControl e=AutomaticGainControl.create(session); if(e!=null){effects.add(e);e.setEnabled(false);} } } catch(RuntimeException ignored){}
        try { if (NoiseSuppressor.isAvailable()) { NoiseSuppressor e=NoiseSuppressor.create(session); if(e!=null){effects.add(e);e.setEnabled(false);} } } catch(RuntimeException ignored){}
        try { if (AcousticEchoCanceler.isAvailable()) { AcousticEchoCanceler e=AcousticEchoCanceler.create(session); if(e!=null){effects.add(e);e.setEnabled(false);} } } catch(RuntimeException ignored){}
    }
    private void transmit(Intent intent,int startId) {
        ScheduledExecutorService watchdog=Executors.newSingleThreadScheduledExecutor();
        try {
            Socket connection=new Socket(); socket=connection;
            connection.connect(new InetSocketAddress(intent.getStringExtra("host"),intent.getIntExtra("port",45871)),5000);
            connection.setTcpNoDelay(true); connection.setSoTimeout(5000); connection.setSendBufferSize(4096);
            OutputStream output=connection.getOutputStream();
            Wire.hello(output,intent.getStringExtra("code"));
            byte[] reply=new byte[4]; new DataInputStream(connection.getInputStream()).readFully(reply);
            if (!java.util.Arrays.equals(reply,new byte[]{'O','K','A','Y'})) throw new IOException("Conexão recusada. Confira o código no PC.");
            if (!running) return;
            AudioManager manager=(AudioManager)getSystemService(AUDIO_SERVICE);
            int mode=intent.getIntExtra("source",0);
            boolean raw=mode==0 && "true".equals(manager.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED));
            int source=mode==2?MediaRecorder.AudioSource.VOICE_COMMUNICATION:mode==3?MediaRecorder.AudioSource.MIC:raw?MediaRecorder.AudioSource.UNPROCESSED:MediaRecorder.AudioSource.VOICE_RECOGNITION;
            String sourceName=mode==2?"modo chamada":mode==3?"microfone padrão":raw?"sem processamento":"reconhecimento de voz";
            int min=AudioRecord.getMinBufferSize(48000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
            if(min<=0) throw new IOException("O aparelho não oferece captura PCM a 48 kHz");
            AudioRecord capture=new AudioRecord(source,48000,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(min,3840));
            recorder=capture;
            if(capture.getState()!=AudioRecord.STATE_INITIALIZED) throw new IOException("Falha ao abrir o microfone");
            if(mode!=2 && mode!=3)disableEffects(capture.getAudioSessionId()); capture.startRecording();
            if(capture.getRecordingState()!=AudioRecord.RECORDSTATE_RECORDING) throw new IOException("Captura não iniciou");
            status="Transmitindo • "+sourceName;
            final java.util.concurrent.atomic.AtomicLong progress=new java.util.concurrent.atomic.AtomicLong(System.nanoTime());
            watchdog.scheduleAtFixedRate(() -> {
                if(System.nanoTime()-progress.get()>TimeUnit.SECONDS.toNanos(3)) closeSocket();
            },1,1,TimeUnit.SECONDS);
            short[] samples=new short[480]; byte[] pcm=new byte[960];
            SampleEncoder encoder=new SampleEncoder();
            long frames=0;
            while(running) {
                int count=capture.read(samples,0,samples.length,AudioRecord.READ_BLOCKING);
                if(count<=0) throw new IOException("Falha de captura: "+count);
                encoder.encode(samples,count,gainDb,muted,pcm);clips+=encoder.clips;
                levelDb=(float)(20*Math.log10(Math.max(1,encoder.peak)/32768.0));
                Wire.frame(output,pcm,count*2); progress.set(System.nanoTime());
                frames+=count;
                if(frames>=48000) { status=(muted?"Silenciado":"Transmitindo")+" • "+sourceName; frames=0; }
            }
        } catch(Exception error) {
            if(running) status="Parou: "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage());
        } finally {
            running=false; levelDb=-96; watchdog.shutdownNow(); closeSocket();
            for(AudioEffect effect:effects) effect.release(); effects.clear();
            AudioRecord capture=recorder;
            if(capture!=null) { try { capture.stop(); } catch(RuntimeException ignored){} capture.release(); }
            recorder=null;
            new Handler(getMainLooper()).post(() -> {
                if(owner==this) { owner=null; active=false; }
                stopSelfResult(latestStartId);
            });
        }
    }
    private void closeSocket() { Socket s=socket; if(s!=null) try{s.close();}catch(IOException ignored){} }
    @Override public void onDestroy() {
        boolean requested=running; running=false; closeSocket();
        AudioRecord capture=recorder; if(capture!=null) try{capture.stop();}catch(RuntimeException ignored){}
        if(wake!=null && wake.isHeld()) wake.release();
        if(requested) status="Microfone parado";
        // A new session is allowed only after the worker releases its recorder.
        if(worker==null && owner==this) { owner=null; active=false; }
        stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy();
    }
}
