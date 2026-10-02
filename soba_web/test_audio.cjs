const vm=require('vm'), fs=require('fs'), assert=require('assert');
let sources=[],listeners={},buttons=[];
class Context{constructor(){this.state='running';this.currentTime=0;this.destination={};}createBuffer(c,n,r){return {duration:n/r,data:new Float32Array(n),getChannelData(){return this.data;}};}createGain(){return {gain:{value:0,setTargetAtTime(v){this.value=v;}},connect(){},disconnect(){}};}createBufferSource(){const s={connect(g){this.gain=g;},disconnect(){},stop(){this.stopped=true;},start(){}};sources.push(s);return s;}resume(){return Promise.resolve();}}
let doc={body:{append:b=>buttons.push(b)},createElement:()=>({style:{},setAttribute(){}}),addEventListener:(n,f)=>listeners[n]=f};let window={AudioContext:Context};
vm.runInNewContext(fs.readFileSync(__dirname+'/game-audio.js','utf8'),{document:doc,window,Math,Float32Array});
listeners.pointerdown();assert.equal(sources.length,1);assert(sources[0].loop);assert.equal(sources[0].gain.gain.value,.13);
window.sobaAudio.noodleReady();assert.equal(sources[1].buffer.duration,10);window.sobaAudio.noodleReady();assert.equal(sources.length,3);assert(sources[1].stopped);assert.equal(sources[2].buffer.duration,10);
window.sobaAudio.doorBell();assert.equal(sources[3].buffer.duration,1.5);
const peak=s=>s.buffer.data.reduce((max,v)=>Math.max(max,Math.abs(v)),0)*s.gain.gain.value;
assert(peak(sources[1])>peak(sources[0])*3);assert(peak(sources[3])>peak(sources[0])*3);
buttons[0].onclick();assert.equal(sources[0].gain.gain.value,0);window.sobaAudio.doorBell();assert.equal(sources.length,5);assert(peak(sources[4])>0);
buttons[0].onclick();assert.equal(sources[0].gain.gain.value,.13);
console.log('PASS: looping music, 10-second non-stacked alarm, louder alerts, music-only toggle');
