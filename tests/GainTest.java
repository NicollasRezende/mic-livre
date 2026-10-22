import br.com.miclivre.SampleEncoder;
import java.util.Arrays;
public class GainTest {
    public static void main(String[] args) {
        SampleEncoder encoder=new SampleEncoder(); byte[] output=new byte[8];
        encoder.encode(new short[]{-32768,-1,0,32767},4,0,false,output);
        if(!Arrays.equals(output,new byte[]{0,(byte)128,(byte)255,(byte)255,0,0,(byte)255,127})) throw new AssertionError("Bypass alterado");
        encoder.encode(new short[]{20000,-20000,1000,0},4,6.0206f,false,output);
        if(encoder.clips!=2 || output[0]!=(byte)255 || output[1]!=127 || output[2]!=0 || output[3]!=(byte)128) throw new AssertionError("Clipping incorreto");
        encoder.encode(new short[]{1000,1000,1000,1000},4,0,true,output);
        if(!Arrays.equals(output,new byte[8]) || encoder.peak!=0) throw new AssertionError("Mute não silenciou");
        System.out.println("GainTest: 3 verificações OK");
    }
}
