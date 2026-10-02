// Native text entry makes naming furniture and editing menus work on touch keyboards.
window.sobaText={result:'',request(title,value){
 document.getElementById('v2-text-entry')?.remove();
 const layer=document.createElement('div');layer.id='v2-text-entry';layer.style.cssText='position:fixed;inset:0;z-index:1000005;display:grid;place-items:center;background:#14291cd9;font-family:Arial;color:#263f35';
 const card=document.createElement('form');card.style.cssText='width:min(420px,85vw);padding:24px;background:#f3e6c8;border:5px solid #6c866a';
 const heading=document.createElement('h2');heading.textContent=title;
 const input=document.createElement('input');input.value=value;input.maxLength=48;input.autocomplete='off';input.style.cssText='width:100%;box-sizing:border-box;font-size:22px;padding:14px;border:2px solid #718265';
 const ok=document.createElement('button');ok.textContent='Xác nhận';ok.type='submit';
 const cancel=document.createElement('button');cancel.textContent='Hủy';cancel.type='button';
 for(const b of [ok,cancel])b.style.cssText='font-size:18px;padding:12px 18px;margin:16px 12px 0 0;background:#426c55;color:#fff0d0;border:0';
 card.onsubmit=e=>{e.preventDefault();if(!input.value.trim())return;window.sobaText.result=JSON.stringify({value:input.value.trim()});layer.remove();};
 cancel.onclick=()=>{window.sobaText.result=JSON.stringify({cancel:true});layer.remove();};
 card.append(heading,input,ok,cancel);layer.append(card);document.body.append(layer);input.focus();
}};
