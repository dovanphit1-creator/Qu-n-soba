package vn.dovanphi.quanmicuatoi;

import android.util.AtomicFile;
import android.util.Base64;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Iterator;

/** Keep saves outside WebView storage; never replace corrupt user data on load. */
final class SaveStore {
    final File directory;
    final File file;
    SaveStore(File root) throws Exception {
        directory = new File(root, "QuanMiCuaToi");
        if (!directory.isDirectory() && !directory.mkdirs()) throw new Exception("Cannot create save directory");
        file = new File(directory, "save-vnd.json");
    }
    synchronized String initial() throws Exception {
        AtomicFile atomic = new AtomicFile(file);
        // AtomicFile recovers interrupted writes before the game reads the bytes.
        if (!file.exists() && !new File(file.getPath()+".bak").exists()) return "";
        return Base64.encodeToString(atomic.readFully(), Base64.NO_WRAP);
    }
    synchronized void write(String snapshot, String backupsJson) throws Exception {
        JSONObject object = new JSONObject(snapshot);
        if (object.getInt("version") != 10) throw new Exception("Unsupported save version");
        JSONObject backups = new JSONObject(backupsJson);
        Iterator<String> names = backups.keys();
        while(names.hasNext()) {
            String name = names.next();
            if(!name.startsWith("save-vnd.") || !name.endsWith(".bak") || name.contains("/") || name.contains("\\"))
                throw new Exception("Invalid backup name");
            File backup = new File(directory, name);
            if (!backup.exists()) atomicWrite(backup, Base64.decode(backups.getString(name), Base64.DEFAULT));
        }
        atomicWrite(file, snapshot.getBytes(StandardCharsets.UTF_8));
    }
    private static void atomicWrite(File target, byte[] bytes) throws Exception {
        AtomicFile atomic = new AtomicFile(target);
        FileOutputStream stream = null;
        try { stream=atomic.startWrite();stream.write(bytes);atomic.finishWrite(stream); }
        catch(Exception e) { if(stream!=null)atomic.failWrite(stream);throw e; }
    }
}
