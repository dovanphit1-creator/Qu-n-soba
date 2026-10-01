// Companion speech program: eSpeak NG GPL-3.0; source and COPYING accompany this file.
import initialise from './espeak-ng.js';
let engine;
async function ready(){if(!engine){const module=await initialise();engine=new module.eSpeakNGWorker();engine.set_voice('vi');engine.set_rate(160);}return engine;}
self.onmessage=async ({data})=>{try{const voice=await ready();const chunks=[];voice.synthesize(String(data.text),samples=>{chunks.push(samples);return false;});const count=chunks.reduce((n,c)=>n+c.length,0);const pcm=new Float32Array(count);let i=0;for(const c of chunks){for(const s of c)pcm[i++]=s/32768;}self.postMessage({id:data.id,pcm:pcm.buffer,rate:22050},[pcm.buffer]);}catch(error){self.postMessage({id:data.id,error:String(error)});}};
