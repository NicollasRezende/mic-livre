import br.com.miclivre.Wire;
import java.io.ByteArrayOutputStream;
import java.util.Arrays;
public class WireTest {
    public static void main(String[] args) throws Exception {
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        Wire.hello(out,"123456");
        byte[] expected={77,76,86,49,49,50,51,52,53,54,0,0,(byte)187,(byte)128,1,16};
        if(!Arrays.equals(expected,out.toByteArray())) throw new AssertionError("Handshake incompatível");
        out.reset(); Wire.frame(out,new byte[]{0,0,1,0},4);
        if(!Arrays.equals(new byte[]{0,4,0,0,1,0},out.toByteArray())) throw new AssertionError("PCM alterado");
        try { Wire.hello(out,"bad"); throw new AssertionError("Aceitou código inválido"); } catch(IllegalArgumentException expectedError) {}
        try { Wire.frame(out,new byte[3],3); throw new AssertionError("Aceitou frame ímpar"); } catch(IllegalArgumentException expectedError) {}
        System.out.println("WireTest: 4 verificações OK");
    }
}
