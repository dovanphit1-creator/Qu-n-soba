package vn.dovanphi.quanmicuatoi;

import org.json.JSONArray;
import org.json.JSONObject;
import java.net.URI;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Public release metadata only. No save, identity or credentials leave the device. */
final class UpdateChecker {
    static final String REPO="dovanphit1-creator/Qu-n-soba";
    static final String API="https://api.github.com/repos/"+REPO+"/releases?per_page=30";
    static final String CHANNEL="[android-apk-channel:androidbeta]";
    interface Fetcher { Update fetch(String current) throws Exception; }
    static final class Update {
        final String version,url,notes;
        Update(String version,String url,String notes){this.version=version;this.url=url;this.notes=notes;}
    }
    static long[] version(String text) {
        Matcher m=Pattern.compile("(?:android-|v)?(\\d{1,6})\\.(\\d{1,6})\\.(\\d{1,6})(?:-beta\\.(\\d{1,6}))?").matcher(text);
        if(!m.matches())return null;
        return new long[]{Long.parseLong(m.group(1)),Long.parseLong(m.group(2)),Long.parseLong(m.group(3)),m.group(4)==null?1000000:Long.parseLong(m.group(4))};
    }
    static int compare(long[] a,long[] b){for(int i=0;i<a.length;i++){int c=Long.compare(a[i],b[i]);if(c!=0)return c;}return 0;}
    static Update select(String json,String current) throws Exception {
        long[] best=version(current);if(best==null)return null;
        Update result=null;
        JSONArray releases=new JSONArray(json);
        for(int i=0;i<releases.length();i++){
            JSONObject release=releases.optJSONObject(i);if(release==null || release.optBoolean("draft",true))continue;
            String tag=release.optString("tag_name"),body=release.optString("body");
            if(!tag.startsWith("android-") || !body.contains(CHANNEL))continue;
            long[] next=version(tag);if(next==null || compare(next,best)<=0)continue;
            JSONArray assets=release.optJSONArray("assets");if(assets==null)continue;
            String name="QuanMiCuaToi-Android-"+tag.substring(8)+".apk";
            for(int j=0;j<assets.length();j++){
                JSONObject asset=assets.optJSONObject(j);if(asset==null || !name.equals(asset.optString("name")) || !"uploaded".equals(asset.optString("state")) || asset.optLong("size")<=0)continue;
                String url=asset.optString("browser_download_url");URI uri;
                try{uri=new URI(url);}catch(Exception e){continue;}
                if(!"https".equals(uri.getScheme()) || !"github.com".equals(uri.getHost()) || uri.getUserInfo()!=null || uri.getPort()!=-1 || uri.getQuery()!=null || uri.getFragment()!=null || !("/"+REPO+"/releases/download/"+tag+"/"+name).equals(uri.getPath()))continue;
                String notes=body.replace(CHANNEL,"").replaceAll("[\\p{Cntrl}\\s]+"," ").trim();
                if(notes.length()>420)notes=notes.substring(0,420)+"…";
                result=new Update(tag.substring(8),url,notes);best=next;break;
            }
        }
        return result;
    }
    static Update fetch(String current) throws Exception {
        HttpURLConnection connection=(HttpURLConnection)new URL(API).openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(5000);connection.setReadTimeout(5000);
        connection.setRequestProperty("Accept","application/vnd.github+json");
        connection.setRequestProperty("User-Agent","QuanMiCuaToi-Android/"+current);
        try {
            if(connection.getResponseCode()!=200)return null;
            try(InputStream input=connection.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()){
                byte[] buffer=new byte[8192];int count;
                while((count=input.read(buffer))!=-1){if(out.size()+count>262144)return null;out.write(buffer,0,count);}
                return select(new String(out.toByteArray(),StandardCharsets.UTF_8),current);
            }
        } finally {connection.disconnect();}
    }
}
