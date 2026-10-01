// The Python/WASM proxy transports strings as byte strings. Use ASCII on
// that boundary so Vietnamese and emoji survive every save and keyboard edit.
const fromUtf8Base64=value=>new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(atob(value),c=>c.charCodeAt(0)));
window.sobaIOSCommands=[];
window.sobaIOSInitialSave=NativeGame.initialSave();
window.sobaIOSDrain=()=>JSON.stringify(window.sobaIOSCommands.splice(0)).replace(/[^\x00-\x7f]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
window.sobaIOSSave=(snapshot,backups)=>{if(!NativeGame.save(fromUtf8Base64(snapshot),backups))window.sobaIOSCommands.push({kind:'saveError'});};
window.sobaIOSEdit=(field,value)=>NativeGame.edit(field,fromUtf8Base64(value));
window.sobaSpeak=text=>NativeGame.speak(fromUtf8Base64(text));
// Compatibility adapter for the bundled mobile shell; no Apple services used.
window.webkit={messageHandlers:{game:{postMessage:m=>{
 if(m.kind==='reload')NativeGame.reload();
 if(m.kind==='ready')NativeGame.ready();
}}}};
document.addEventListener('visibilitychange',()=>{if(document.hidden)window.sobaIOSCommands.push({kind:'save'});});

// A start tap made while WASM is still loading must not be lost.
const startTimer=setInterval(()=>{if(window.sobaStartRequested && window.MM){window.MM.UME=true;clearInterval(startTimer);}},100);
