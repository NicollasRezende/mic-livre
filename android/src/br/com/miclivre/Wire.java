package br.com.miclivre;

import java.io.DataOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

public final class Wire {
    private Wire() {}
    public static void hello(OutputStream output, String code) throws IOException {
        if (!code.matches("[0-9]{6}")) throw new IllegalArgumentException("Código deve ter seis dígitos");
        DataOutputStream data = new DataOutputStream(output);
        data.writeBytes("MLV1");
        data.write(code.getBytes(StandardCharsets.US_ASCII));
        data.writeInt(48000);
        data.writeByte(1);
        data.writeByte(16);
        data.flush();
    }
    public static void frame(OutputStream output, byte[] pcm, int count) throws IOException {
        if (count < 2 || count > 960 || count % 2 != 0) throw new IllegalArgumentException("Quadro inválido");
        output.write(count >>> 8);
        output.write(count & 255);
        output.write(pcm, 0, count);
    }
}
