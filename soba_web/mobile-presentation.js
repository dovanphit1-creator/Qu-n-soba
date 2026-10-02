// Keep native fullscreen requests inside actual player gestures; denial never blocks the game.
(() => {
  const mobile = matchMedia('(pointer: coarse)').matches && Math.min(window.innerWidth,window.innerHeight)<1100;
  const canvas = document.getElementById('canvas');
  const start = document.getElementById('boot-start');
  const hint = document.getElementById('mobile-landscape-hint');
  const probe = document.getElementById('safe-area-probe');
  let ready = false;
  const state = window.sobaPresentation = {fullscreen: false, landscape: false, limited: false};
  function layout() {
    state.fullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
    const viewport = window.visualViewport;
    const width = viewport?.width || window.innerWidth, height = viewport?.height || window.innerHeight;
    state.landscape = width >= height;
    hint.hidden = !(ready && mobile && !state.landscape);
    if (!ready || !canvas) return;
    const safe = getComputedStyle(probe);
    const left = parseFloat(safe.paddingLeft) || 0, right = parseFloat(safe.paddingRight) || 0;
    const top = parseFloat(safe.paddingTop) || 0, bottom = parseFloat(safe.paddingBottom) || 0;
    const usableWidth = Math.max(1, width-left-right), usableHeight = Math.max(1,height-top-bottom);
    const ratio = (canvas.width || 1600)/(canvas.height || 1000);
    const w = Math.min(usableWidth, usableHeight*ratio), h = w/ratio;
    const values = {position:'fixed',left:(left+(usableWidth-w)/2)+'px',top:(top+(usableHeight-h)/2)+'px',
      width:w+'px',height:h+'px',right:'auto',bottom:'auto',margin:'0',padding:'0',border:'0',touchAction:'none'};
    for (const [key,value] of Object.entries(values)) if(canvas.style[key]!==value)canvas.style[key]=value;
  }
  async function enterFullscreen() {
    const element = document.documentElement;
    const request = element.requestFullscreen || element.webkitRequestFullscreen;
    try {
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        if(request) await request.call(element,{navigationUI:'hide'});
        else state.limited=true;
      }
    } catch (_) {state.limited=true;}
    try {
      if (mobile && screen.orientation?.lock) await screen.orientation.lock('landscape');
      else if(mobile) state.limited=true;
    } catch (_) {state.limited=true;}
    layout();
  }
  start.addEventListener('click',()=>{if(mobile)enterFullscreen();});
  // An in-game settings button publishes its rectangle in SDL display pixels.
  document.addEventListener('pointerdown',event=>{
    if(event.target!==canvas || !window.sobaFullscreenRect)return;
    try {
      const [x,y,w,h]=JSON.parse(window.sobaFullscreenRect), r=canvas.getBoundingClientRect();
      const px=(event.clientX-r.left)/r.width*canvas.width, py=(event.clientY-r.top)/r.height*canvas.height;
      if(px>=x && px<=x+w && py>=y && py<=y+h)enterFullscreen();
    } catch (_) {}
  },{capture:true});
  window.addEventListener('soba-game-ready',()=>{
    ready=true;
    const music=document.getElementById('background-music-toggle');if(music)music.hidden=true;
    layout();
  });
  const schedule=()=>requestAnimationFrame(layout);
  window.addEventListener('resize',schedule);
  window.visualViewport?.addEventListener('resize',schedule);
  document.addEventListener('fullscreenchange',schedule);
  document.addEventListener('webkitfullscreenchange',schedule);
  if(canvas)new MutationObserver(schedule).observe(canvas,{attributes:true,attributeFilter:['style','width','height']});
})();
