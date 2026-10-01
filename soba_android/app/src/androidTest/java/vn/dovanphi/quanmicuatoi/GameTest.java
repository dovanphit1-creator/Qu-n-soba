package vn.dovanphi.quanmicuatoi;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.core.app.ActivityScenario;
import androidx.test.platform.app.InstrumentationRegistry;
import androidx.test.uiautomator.UiDevice;
import android.content.Context;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.json.JSONObject;
import java.nio.file.Files;
import static org.junit.Assert.*;

@RunWith(AndroidJUnit4.class)
public class GameTest {
    @Test public void protectsAndRecoversNativeSave() throws Exception {
        Context ctx=InstrumentationRegistry.getInstrumentation().getTargetContext();
        SaveStore store=new SaveStore(new java.io.File(ctx.getCacheDir(),"save-test"));
        store.write("{\"version\":10,\"cash\":123}","{}");
        try{store.write("{\"version\":999}","{}");fail("Unsupported data must fail");}catch(Exception expected){}
        assertEquals(123,new JSONObject(new String(android.util.Base64.decode(store.initial(),0),java.nio.charset.StandardCharsets.UTF_8)).getInt("cash"));
        try{store.write("{\"version\":10,\"cash\":0}","{\"save-vnd../escape.bak\":\"YQ==\"}");fail("Unsafe backup must fail");}catch(Exception expected){}
        assertEquals(123,new JSONObject(new String(android.util.Base64.decode(store.initial(),0))).getInt("cash"));
    }
    private void waitReady(ActivityScenario<MainActivity> scenario) throws Exception {
        long end=System.currentTimeMillis()+120000;
        while(System.currentTimeMillis()<end){final boolean[] ready={false};scenario.onActivity(a->ready[0]=a.gameReady);if(ready[0])return;Thread.sleep(300);}
        final String[] details={""};
        java.util.concurrent.CountDownLatch diagnostic=new java.util.concurrent.CountDownLatch(1);
        scenario.onActivity(a->a.web.evaluateJavascript("JSON.stringify({url:location.href,mm:!!window.MM,ume:window.MM&&window.MM.UME,message:document.querySelector('#boot-message')?.textContent,error:document.querySelector('#boot-detail')?.textContent,stdout:document.querySelector('#stdout')?.value})",result->{details[0]=result;diagnostic.countDown();}));
        diagnostic.await(10,java.util.concurrent.TimeUnit.SECONDS);
        Context ctx=InstrumentationRegistry.getInstrumentation().getTargetContext();
        UiDevice.getInstance(InstrumentationRegistry.getInstrumentation()).takeScreenshot(new java.io.File(ctx.getExternalFilesDir(null),"android-game.png"));
        fail("Bundled Python must reach its first rendered frame. "+details[0]);
    }
    @Test public void offlineTouchZoomAndColdRestore() throws Exception {
        Context ctx=InstrumentationRegistry.getInstrumentation().getTargetContext();
        SaveStore store=new SaveStore(ctx.getFilesDir());store.file.delete();
        UiDevice device=UiDevice.getInstance(InstrumentationRegistry.getInstrumentation());
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            // Start with DOM click only for the loader; gameplay uses a real device touch.
            Thread.sleep(2000);
            scenario.onActivity(a->a.web.evaluateJavascript("document.querySelector('#boot-start').click()",null));
            waitReady(scenario);
            final int[] button={0,0};
            final java.util.concurrent.CountDownLatch coordinates=new java.util.concurrent.CountDownLatch(1);
            scenario.onActivity(a->a.web.evaluateJavascript("(()=>{const b=document.querySelector('#canvas').getBoundingClientRect();return [b.x+b.width*.5,b.y+b.height*.794,devicePixelRatio]})()",result->{
                try{org.json.JSONArray data=new org.json.JSONArray(result);button[0]=(int)(data.getDouble(0)*data.getDouble(2));button[1]=(int)(data.getDouble(1)*data.getDouble(2));}catch(Exception e){throw new RuntimeException(e);}coordinates.countDown();
            }));
            assertTrue(coordinates.await(10,java.util.concurrent.TimeUnit.SECONDS));
            device.click(button[0],button[1]);
            long end=System.currentTimeMillis()+15000;
            while(!store.file.exists()&&System.currentTimeMillis()<end)Thread.sleep(200);
            assertTrue("Welcome touch creates actual Python save",store.file.exists());
            JSONObject saved=new JSONObject(new String(Files.readAllBytes(store.file.toPath()),java.nio.charset.StandardCharsets.UTF_8));assertEquals(10000000,saved.getInt("cash"));
            scenario.onActivity(a->a.web.evaluateJavascript("document.querySelector('#mobile-tools button').click()",null));
            Thread.sleep(500);
            scenario.onActivity(a->a.web.evaluateJavascript("window.sobaIOSCommands.push({kind:'save'})",null));Thread.sleep(1000);
        }
        JSONObject saved=new JSONObject(new String(Files.readAllBytes(store.file.toPath()),java.nio.charset.StandardCharsets.UTF_8));saved.put("cash",9876543);store.write(saved.toString(),"{}");
        try(ActivityScenario<MainActivity> scenario=ActivityScenario.launch(MainActivity.class)){
            Thread.sleep(2000);scenario.onActivity(a->a.web.evaluateJavascript("document.querySelector('#boot-start').click()",null));waitReady(scenario);
            scenario.onActivity(a->a.web.evaluateJavascript("window.sobaIOSCommands.push({kind:'save'})",null));Thread.sleep(1500);
            assertEquals(9876543,new JSONObject(new String(Files.readAllBytes(store.file.toPath()),java.nio.charset.StandardCharsets.UTF_8)).getInt("cash"));
            device.takeScreenshot(new java.io.File(ctx.getExternalFilesDir(null),"android-game.png"));
        }
    }
}
