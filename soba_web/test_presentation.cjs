const vm=require('vm'),fs=require('fs'),assert=require('assert');
async function scenario(mode){
 const events={},startEvents={},docEvents={},calls=[];
 const canvas={width:1600,height:1000,style:{},getBoundingClientRect(){return {left:0,top:0,width:800,height:500}}};
 const elements={canvas,'boot-start':{addEventListener:(n,f)=>startEvents[n]=f},'mobile-landscape-hint':{hidden:true},'safe-area-probe':{},'background-music-toggle':{hidden:false}};
 const document={documentElement:{},getElementById:n=>elements[n],addEventListener:(n,f)=>docEvents[n]=f};
 const window={innerWidth:844,innerHeight:390,addEventListener:(n,f)=>events[n]=f};
 const screen={orientation:{}};
 if(mode!=='unsupported'){
  document.documentElement.requestFullscreen=function(){calls.push('fullscreen');if(mode==='denied')return Promise.reject(Error('denied'));document.fullscreenElement=this;return Promise.resolve();};
  screen.orientation.lock=function(value){calls.push(value);return mode==='denied'?Promise.reject(Error('denied')):Promise.resolve();};
 }
 vm.runInNewContext(fs.readFileSync(__dirname+'/mobile-presentation.js','utf8'),{window,document,screen,navigator:{maxTouchPoints:5},matchMedia:()=>({matches:true}),getComputedStyle:()=>({paddingLeft:'20',paddingRight:'20',paddingTop:'0',paddingBottom:'10'}),requestAnimationFrame:f=>f(),MutationObserver:class{observe(){}},JSON,Math,parseFloat});
 assert.equal(calls.length,0,'never requests fullscreen without a gesture');
 startEvents.click();await new Promise(r=>setImmediate(r));
 if(mode!=='unsupported')assert.deepEqual(calls,['fullscreen','landscape']);
 assert.equal(window.sobaPresentation.limited,mode!=='supported');
 events['soba-game-ready']();assert(elements['background-music-toggle'].hidden);
 assert(parseFloat(canvas.style.width)<=804 && parseFloat(canvas.style.height)<=380);
 assert.equal(elements['mobile-landscape-hint'].hidden,true);
 window.innerWidth=390;window.innerHeight=844;events.resize();assert.equal(elements['mobile-landscape-hint'].hidden,false);
 window.innerWidth=844;window.innerHeight=390;events.resize();assert.equal(elements['mobile-landscape-hint'].hidden,true);
 // A settings tap must invoke fullscreen in the pointer callback, before awaiting.
 document.fullscreenElement=null;window.sobaFullscreenRect='[800,400,300,100]';
 const before=calls.length;docEvents.pointerdown({target:canvas,clientX:450,clientY:225});
 if(mode!=='unsupported')assert.equal(calls[before],'fullscreen');
 await new Promise(r=>setImmediate(r));
}
(async()=>{for(const mode of ['supported','denied','unsupported'])await scenario(mode);console.log('PASS: fullscreen gesture, orientation, unsupported/denied fallback, safe-area fit, hidden overlay, portrait hint and settings retry');})().catch(e=>{console.error(e);process.exit(1)});
