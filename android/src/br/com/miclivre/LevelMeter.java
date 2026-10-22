package br.com.miclivre;
import android.content.Context;
import android.graphics.*;
import android.view.View;

public final class LevelMeter extends View {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private float value=-96;
    public LevelMeter(Context context) {super(context);setContentDescription("Nível do microfone");}
    public void setLevel(float db) {value=db;invalidate();}
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float width=getWidth(),height=getHeight(),density=getResources().getDisplayMetrics().density;
        int segments=30; float gap=3*density, step=width/segments;
        float fraction=Math.max(0,Math.min(1,(value+60)/60));
        for(int i=0;i<segments;i++) {
            boolean lit=i<(int)(fraction*segments);
            paint.setColor(lit?(i>=28?Color.rgb(255,121,115):i>=24?Color.rgb(246,202,108):Color.rgb(103,224,181)):Color.rgb(38,53,70));
            canvas.drawRoundRect(i*step,0,(i+1)*step-gap,height,2*density,2*density,paint);
        }
    }
}
