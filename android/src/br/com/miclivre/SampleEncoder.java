package br.com.miclivre;

/** PCM encoding with explicit gain and saturation, never integer wraparound. */
public final class SampleEncoder {
    public int peak;
    public int clips;
    public void encode(short[] samples,int count,float gainDb,boolean muted,byte[] output) {
        double gain=Math.pow(10,gainDb/20.0); peak=0; clips=0;
        for(int i=0;i<count;i++) {
            int sample=muted?0:(int)Math.round(samples[i]*gain);
            if(sample>32767) {sample=32767;clips++;}
            if(sample< -32768) {sample=-32768;clips++;}
            peak=Math.max(peak,Math.abs(sample));
            output[2*i]=(byte)sample; output[2*i+1]=(byte)(sample>>8);
        }
    }
}
