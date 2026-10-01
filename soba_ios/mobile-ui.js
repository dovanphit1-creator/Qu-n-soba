// Fixed logical canvas; zoom and pan controls make small desktop-sized labels usable.
(() => {
  let zoom = 1, x = 0, y = 0;
  const style = document.createElement('style');
  style.textContent = `#mobile-tools{position:fixed;right:5px;bottom:8px;z-index:9000;display:none;gap:4px;flex-direction:column}
  #mobile-tools button,#mobile-pan button{width:38px;height:38px;border:1px solid #83957b;border-radius:9px;background:#26372eeb;color:#fff2d2;font:bold 19px Arial;touch-action:manipulation}
  #mobile-pan{position:fixed;left:5px;bottom:8px;z-index:9000;display:none;grid-template-columns:38px 38px;gap:4px}
  canvas#canvas{transform-origin:center;touch-action:none}`;
  document.head.append(style);
  const tools = document.createElement('div'); tools.id = 'mobile-tools';
  const pan = document.createElement('div'); pan.id = 'mobile-pan';
  function layout() {
    const canvas = document.getElementById('canvas'); if (!canvas) return;
    const width = Math.min(innerWidth, innerHeight * 1.6), height = width / 1.6;
    x = Math.max(-(width * zoom - width) / 2, Math.min((width * zoom - width) / 2, x));
    y = Math.max(-(height * zoom - height) / 2, Math.min((height * zoom - height) / 2, y));
    canvas.style.setProperty('width', width + 'px', 'important');
    canvas.style.setProperty('height', height + 'px', 'important');
    canvas.style.transform = `translate(${x}px, ${y}px) scale(${zoom})`;
    pan.style.display = zoom > 1 ? 'grid' : 'none';
  }
  function button(parent, text, label, fn) {
    const b = document.createElement('button'); b.textContent = text; b.ariaLabel = label;
    b.onclick = event => { event.preventDefault(); event.stopPropagation(); fn(); layout(); };
    for (const name of ['touchstart','touchmove','touchend','pointerdown','pointerup'])
      b.addEventListener(name, event => event.stopPropagation());
    parent.append(b);
  }
  button(tools, '+', 'Phóng to', () => { zoom = Math.min(2.5, zoom + .5); });
  button(tools, '−', 'Thu nhỏ', () => { zoom = Math.max(1, zoom - .5); });
  button(tools, '↺', 'Xem toàn quán', () => { zoom = 1; x = y = 0; });
  button(pan, '←', 'Xem bên trái', () => { x += 110; });
  button(pan, '→', 'Xem bên phải', () => { x -= 110; });
  button(pan, '↑', 'Xem phía trên', () => { y += 110; });
  button(pan, '↓', 'Xem phía dưới', () => { y -= 110; });
  document.body.append(tools, pan);
  const original = window.sobaStatus;
  window.sobaStatus = (state, detail) => {
    original(state, detail);
    if (state === 'ready') { tools.style.display = 'flex'; layout(); }
    else if (state === 'error' || state === 'stopped') { tools.style.display = pan.style.display = 'none'; }
  };
  addEventListener('resize', layout);
})();
