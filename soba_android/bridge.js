window.sobaIOSCommands=[];
window.sobaIOSInitialSave=NativeGame.initialSave();
window.sobaIOSDrain=()=>JSON.stringify(window.sobaIOSCommands.splice(0));
window.sobaIOSSave=(snapshot,backups)=>{if(!NativeGame.save(snapshot,backups))window.sobaIOSCommands.push({kind:'saveError'});};
window.sobaIOSEdit=(field,value)=>NativeGame.edit(field,value);
window.sobaSpeak=text=>NativeGame.speak(text);
// Compatibility adapter for the bundled mobile shell; no Apple services used.
window.webkit={messageHandlers:{game:{postMessage:m=>{
 if(m.kind==='reload')NativeGame.reload();
 if(m.kind==='ready')NativeGame.ready();
}}}};
document.addEventListener('visibilitychange',()=>{if(document.hidden)window.sobaIOSCommands.push({kind:'save'});});
