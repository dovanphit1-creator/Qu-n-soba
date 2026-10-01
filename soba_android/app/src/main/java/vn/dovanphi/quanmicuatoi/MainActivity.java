package vn.dovanphi.quanmicuatoi;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.webkit.*;
import android.view.View;
import android.widget.EditText;
import android.text.InputType;
import android.speech.tts.TextToSpeech;
import android.net.Uri;
import androidx.webkit.WebViewAssetLoader;
import org.json.JSONObject;
import java.util.Locale;
import java.io.ByteArrayInputStream;

public final class MainActivity extends Activity {
    WebView web;
    SaveStore store;
    TextToSpeech speech;
    boolean vietnameseVoice=false;
    boolean gameReady=false;
    volatile boolean exitPending=false;
    private static final String ORIGIN="https://appassets.androidplatform.net";
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        try { store=new SaveStore(getFilesDir()); }
        catch(Exception e) { showError(); return; }
        speech=new TextToSpeech(this, status->{ if(status==TextToSpeech.SUCCESS) vietnameseVoice=speech.setLanguage(Locale.forLanguageTag("vi-VN"))>=TextToSpeech.LANG_AVAILABLE; });
        web=new WebView(this);setContentView(web);
        WebSettings settings=web.getSettings();
        settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        final WebViewAssetLoader loader=new WebViewAssetLoader.Builder().addPathHandler("/assets/",new WebViewAssetLoader.AssetsPathHandler(this)).build();
        web.setWebViewClient(new WebViewClient(){
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request) {
                Uri uri=request.getUrl();
                if ("https".equals(uri.getScheme()) && "appassets.androidplatform.net".equals(uri.getHost())) {
                    WebResourceResponse response=loader.shouldInterceptRequest(uri);
                    if(response!=null)return response;
                }
                android.util.Log.w("SobaRuntime","Blocked resource: "+uri);
                return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",java.util.Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !request.getUrl().toString().startsWith(ORIGIN+"/assets/game/");
            }
        });
        web.setWebChromeClient(new WebChromeClient(){@Override public boolean onConsoleMessage(ConsoleMessage message){android.util.Log.i("SobaRuntime",message.message()+" @"+message.sourceId()+":"+message.lineNumber());return true;}});
        web.addJavascriptInterface(new NativeBridge(),"NativeGame");
        if(android.os.Build.VERSION.SDK_INT>=33)getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, this::showExit);
        web.loadUrl(ORIGIN+"/assets/game/index.html");
    }
    private void showError(){new AlertDialog.Builder(this).setMessage("Không đọc được dữ liệu đã lưu. Hãy kiểm tra dung lượng máy; dữ liệu cũ được giữ nguyên.").setPositiveButton("Đóng",(d,w)->finish()).setCancelable(false).show();}
    void command(String json){if(web!=null)web.evaluateJavascript("window.sobaIOSCommands && window.sobaIOSCommands.push("+json+")",null);}
    final class NativeBridge {
        @JavascriptInterface public String initialSave(){try{return store.initial();}catch(Exception e){runOnUiThread(()->{web.stopLoading();showError();});throw new IllegalStateException("Cannot read saved progress",e);}}
        @JavascriptInterface public boolean save(String snapshot,String backups){try{store.write(snapshot,backups);if(exitPending)runOnUiThread(()->{exitPending=false;finish();});return true;}catch(Exception e){return false;}}
        @JavascriptInterface public void ready(){runOnUiThread(()->gameReady=true);}
        @JavascriptInterface public void reload(){runOnUiThread(()->{gameReady=false;web.reload();});}
        @JavascriptInterface public void speak(String text){runOnUiThread(()->{if(speech!=null && vietnameseVoice)speech.speak(text,TextToSpeech.QUEUE_ADD,null,"order");});}
        @JavascriptInterface public void edit(String field,String value){
            if(!field.equals("name")&&!field.equals("price")&&!field.equals("shift_name"))return;
            runOnUiThread(()->{
                EditText input=new EditText(MainActivity.this);input.setText(value);
                if(field.equals("price"))input.setInputType(InputType.TYPE_CLASS_NUMBER);
                new AlertDialog.Builder(MainActivity.this).setTitle(field.equals("price")?"Giá bán (VND)":field.equals("name")?"Tên món":"Tên ca làm").setView(input)
                    .setPositiveButton("Xong",(d,w)->command("{\"kind\":\"text\",\"field\":"+JSONObject.quote(field)+",\"text\":"+JSONObject.quote(input.getText().toString())+"}"))
                    .setNegativeButton("Hủy",(d,w)->command("{\"kind\":\"cancelText\"}"))
                    .setOnCancelListener(d->command("{\"kind\":\"cancelText\"}")).show();
                input.requestFocus();
            });
        }
    }
    @Override protected void onPause(){if(gameReady)command("{\"kind\":\"save\"}");super.onPause();}
    @Override public void onBackPressed(){showExit();}
    private void showExit(){
        if(!gameReady){finish();return;}
        new AlertDialog.Builder(this).setMessage("Lưu và thoát game?").setPositiveButton("Thoát",(d,w)->{
            exitPending=true;
            command("{\"kind\":\"save\"}");
            web.postDelayed(()->{if(exitPending){exitPending=false;new AlertDialog.Builder(this).setMessage("Chưa lưu được game. Hãy kiểm tra dung lượng máy và thử lại.").setPositiveButton("OK",null).show();}},5000);
        }).setNegativeButton("Chơi tiếp",null).show();
    }
    @Override protected void onDestroy(){if(web!=null){web.removeJavascriptInterface("NativeGame");web.destroy();}if(speech!=null)speech.shutdown();super.onDestroy();}
}
