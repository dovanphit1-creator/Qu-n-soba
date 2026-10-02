// A running disposable web session can discover a later deployment safely.
(()=>{
 const credit=document.querySelector('.boot-credit')?.textContent||'';
 const current=credit.match(/Phiên bản (\d+\.\d+\.\d+)/)?.[1];
 if(!current)return;
 const version=s=>/^\d{1,6}\.\d{1,6}\.\d{1,6}$/.test(s)?s.split('.').map(Number):null;
 const newer=s=>{const a=version(s),b=version(current);if(!a||!b)return false;for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i];}return false;};
 let shown='',busy=false,lastCheck=0,ready=false;
 const check=async()=>{
  if(!ready||busy||Date.now()-lastCheck<60000)return;
  busy=true;lastCheck=Date.now();
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),5000);
  try{
   const response=await fetch('version.json',{cache:'no-store',signal:controller.signal});
   if(!response.ok)return;const data=await response.json();
   if(!newer(data.game_version)||shown===data.game_version)return;
   shown=data.game_version;
   const box=document.createElement('div');box.setAttribute('role','dialog');box.setAttribute('aria-modal','true');box.setAttribute('aria-label','Có phiên bản mới');
   box.style.cssText='position:fixed;inset:0;z-index:1000001;background:#0009;display:grid;place-items:center;padding:24px;color:#243f39;font-family:monospace';
   const card=document.createElement('div');card.style.cssText='box-sizing:border-box;width:min(480px,calc(100vw - 32px));max-height:calc(100dvh - 24px);overflow:auto;background:#fff0ce;padding:28px;border:14px solid #956743;border-image:url(pixel-ui-frame.png) 24 fill stretch;image-rendering:pixelated;box-shadow:8px 8px 0 #14251f80';
   const title=document.createElement('h2');title.textContent='Có phiên bản mới';
   const message=document.createElement('p');message.style.lineHeight='1.6';message.textContent='Quán Mì Của Tôi '+data.game_version+' đã sẵn sàng. Bản đang chơi: '+current+'. Bản web không lưu; mở bản mới sẽ bắt đầu ván mới.';
   const later=document.createElement('button'),update=document.createElement('button');
   later.textContent='Để sau';update.textContent='Chơi bản mới';
   for(const button of [later,update])button.style.cssText='padding:12px 16px;margin:8px 8px 0 0;border:3px solid #b99b60;border-radius:0;background:#426c55;color:#fff0ce;font-family:inherit;font-weight:bold;cursor:pointer';
   later.onclick=()=>box.remove();update.onclick=()=>location.reload();
   card.append(title,message,later,update);box.append(card);document.body.append(box);later.focus();
  }catch(_){/* Offline play remains available. */}finally{clearTimeout(timeout);busy=false;}
 };
 window.addEventListener('soba-game-ready',()=>{ready=true;check();});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
 setInterval(check,15*60*1000);
})();
