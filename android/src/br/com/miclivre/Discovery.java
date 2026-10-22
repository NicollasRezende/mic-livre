package br.com.miclivre;

import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.JSONObject;

/** Short, cancellable UDP scan. Offers never contain pairing secrets. */
public final class Discovery {
    public interface Listener {
        void found(String name,String ip,int port,boolean busy);
        void done(String error);
    }
    private volatile DatagramSocket socket;
    private volatile boolean cancelled;
    public void cancel() { cancelled=true; DatagramSocket value=socket; if(value!=null)value.close(); }
    public void search(String lastHost,Listener listener) {
        String error="";
        try(DatagramSocket sock=new DatagramSocket()) {
            socket=sock;
            if(cancelled)return;
            sock.setBroadcast(true); sock.setSoTimeout(300);
            String nonce=UUID.randomUUID().toString();
            byte[] query=("MICLIVRE_DISCOVER_V1 "+nonce).getBytes(StandardCharsets.US_ASCII);
            Set<InetAddress> targets=new HashSet<>(); targets.add(InetAddress.getByName("255.255.255.255"));
            Enumeration<NetworkInterface> interfaces=NetworkInterface.getNetworkInterfaces();
            while(interfaces!=null && interfaces.hasMoreElements()) {
                NetworkInterface network=interfaces.nextElement();
                if(!network.isUp() || network.isLoopback())continue;
                for(InterfaceAddress address:network.getInterfaceAddresses())
                    if(address.getBroadcast()!=null) targets.add(address.getBroadcast());
            }
            // Last numeric IPv4 also works when a router blocks broadcasts.
            if(lastHost!=null && lastHost.matches("[0-9]{1,3}(\\.[0-9]{1,3}){3}")) targets.add(InetAddress.getByName(lastHost));
            Set<String> seen=new HashSet<>();
            long end=System.nanoTime()+4_000_000_000L; long next=0;
            while(!cancelled && System.nanoTime()<end) {
                if(System.nanoTime()>=next) {
                    for(InetAddress target:targets) {
                        try { sock.send(new DatagramPacket(query,query.length,target,45872)); } catch(SocketException ignored) {}
                    }
                    next=System.nanoTime()+900_000_000L;
                }
                byte[] buffer=new byte[2048]; DatagramPacket packet=new DatagramPacket(buffer,buffer.length);
                try { sock.receive(packet); } catch(SocketTimeoutException ignored) { continue; }
                try {
                    JSONObject offer=new JSONObject(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                    if(!"MICLIVRE1".equals(offer.optString("magic")) || !nonce.equals(offer.optString("nonce")))continue;
                    int port=offer.optInt("port",0); if(port<1 || port>65535)continue;
                    String ip=packet.getAddress().getHostAddress(); String key=ip+":"+port;
                    if(seen.add(key)) {
                        String name=offer.optString("name","Computador").replaceAll("[\\p{Cntrl}]","");
                        listener.found(name.substring(0,Math.min(name.length(),64)),ip,port,offer.optBoolean("busy",false));
                    }
                } catch(Exception ignored) { /* Ignore unrelated/malformed UDP responses. */ }
            }
        } catch(Exception failure) { if(!cancelled)error="Busca indisponível: "+failure.getMessage(); }
        finally { socket=null; if(!cancelled)listener.done(error); }
    }
}
