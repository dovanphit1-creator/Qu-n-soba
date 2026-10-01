// Vietnamese speech runs in a separate worker; synthesis never blocks gameplay.
let worker,context,serial=Promise.resolve(),counter=0;const pending=new Map();
function setup(){if(worker)return;worker=new Worker(new URL('./voice/voice-worker.js',import.meta.url),{type:'module'});worker.onmessage=({data})=>{const entry=pending.get(data.id);if(!entry)return;pending.delete(data.id);data.error?entry.reject(Error(data.error)):entry.resolve(data);};}
function unlock(){context??=new AudioContext();context.resume().catch(()=>{});}
addEventListener('pointerdown',unlock,{passive:true});
window.sobaSpeak=text=>{serial=serial.then(async()=>{setup();unlock();const id=++counter;const data=await new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});worker.postMessage({id,text});});const pcm=new Float32Array(data.pcm);if(!pcm.length)return;const buffer=context.createBuffer(1,pcm.length,data.rate);buffer.copyToChannel(pcm,0);const source=context.createBufferSource();source.buffer=buffer;source.connect(context.destination);await new Promise(resolve=>{source.onended=resolve;source.start();});}).catch(error=>console.warn('Giọng đọc tiếng Việt:',String(error)));};
