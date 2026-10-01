package vn.dovanphi.quanmicuatoi;

import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import androidx.test.uiautomator.By;
import androidx.test.uiautomator.Until;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.IntentFilter;
import org.json.JSONObject;
import org.json.JSONArray;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class UpdateTest {
    private JSONObject release(String version) throws Exception {
        String tag="android-"+version,name="QuanMiCuaToi-Android-"+version+".apk";
        JSONObject asset=new JSONObject().put("name",name).put("state","uploaded").put("size",23000000)
            .put("browser_download_url","https://github.com/"+UpdateChecker.REPO+"/releases/download/"+tag+"/"+name);
        return new JSONObject().put("tag_name",tag).put("draft",false).put("prerelease",true)
            .put("body","Đã bổ sung thông báo cập nhật. "+UpdateChecker.CHANNEL).put("assets",new JSONArray().put(asset));
    }
    private UpdateChecker.Update select(JSONObject r) throws Exception {
        return UpdateChecker.select(new JSONArray().put(r).toString(),BuildConfig.VERSION_NAME);
    }
    @Test public void onlyNewerCompatiblePublishedApks() throws Exception {
        assertNull(select(release(BuildConfig.VERSION_NAME)));
        assertNull(select(release("1.8.0-beta.2")));
        assertNotNull(select(release("1.8.0")));
        assertNotNull(select(release("1.9.0-beta.1")));
        assertNull(select(release("1.9.0-beta.1").put("draft",true)));
        assertNull(select(release("1.9.0-beta.1").put("body","Windows release")));
        assertNull(select(release("1.9.0-beta.1").put("tag_name","v1.9.0")));
        JSONObject unsafe=release("1.9.0-beta.1");
        unsafe.getJSONArray("assets").getJSONObject(0).put("browser_download_url","https://github.com.evil.invalid/app.apk");
        assertNull(select(unsafe));
        assertNull(select(release("broken")));
        assertNull(select(release("1.9.0-beta.1").put("assets",new JSONArray())));
        JSONArray unordered=new JSONArray().put(release("1.9.0-beta.2")).put(release("1.9.0-beta.1")).put(release("1.8.1"));
        assertEquals("1.9.0-beta.2",UpdateChecker.select(unordered.toString(),BuildConfig.VERSION_NAME).version);
    }
    @Test public void visiblePromptDownloadIntentAndOfflineFailure() throws Exception {
        UiDevice device=UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());
        UpdateChecker.Update next=select(release("1.9.0-beta.1"));
        Instrumentation instrumentation=InstrumentationRegistry.getInstrumentation();
        IntentFilter filter=new IntentFilter(Intent.ACTION_VIEW);filter.addDataScheme("https");
        Instrumentation.ActivityMonitor monitor=new Instrumentation.ActivityMonitor(filter,new Instrumentation.ActivityResult(0,null),true);
        instrumentation.addMonitor(monitor);
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            scenario.onActivity(a->{a.updateFetcher=current->next;a.checkUpdates(true);});
            assertNotNull("A newer APK must produce an actual native notification",device.wait(Until.findObject(By.text("Có phiên bản mới")),10000));
            assertNotNull(device.findObject(By.textContains("1.9.0-beta.1")));
            device.executeShellCommand("screencap -p /data/local/tmp/android-update.png");
            device.findObject(By.text("TẢI BẢN MỚI")).click();
            instrumentation.waitForIdleSync();
            assertEquals("Download action opens the external browser",1,monitor.getHits());
            scenario.onActivity(a->{a.updateFetcher=current->{throw new java.io.IOException("Offline");};a.checkUpdates(true);});
            long end=System.currentTimeMillis()+5000;
            while(System.currentTimeMillis()<end){final boolean[] busy={true};scenario.onActivity(a->busy[0]=a.updateChecking);if(!busy[0])break;Thread.sleep(50);}
            assertNull(device.findObject(By.text("Có phiên bản mới")));
            scenario.onActivity(a->assertFalse("Offline failures never prevent play",a.updateChecking));
        } finally {instrumentation.removeMonitor(monitor);}
    }
}
