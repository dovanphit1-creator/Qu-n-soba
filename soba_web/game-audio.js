// Original instrumental: "Một góc quán", 72 BPM. No voice or external audio.
(() => {
  let context, music, musicGain, enabled = true;
  const button = document.createElement('button');
  button.type = 'button'; button.id = 'background-music-toggle';
  button.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:1000002;padding:9px 12px;border:1px solid #dbc29a;border-radius:6px;background:#193127;color:#fff4df;font:13px Arial;cursor:pointer';
  const label = () => { button.textContent = enabled ? '♫ Nhạc nền: Bật' : '♫ Nhạc nền: Tắt'; button.setAttribute('aria-label', enabled ? 'Tắt nhạc nền' : 'Bật nhạc nền'); button.setAttribute('aria-pressed', String(enabled)); if(window.sobaAudio)window.sobaAudio.musicEnabled=enabled; };
  label(); document.body.append(button);
  const rate = 22050, beat = 60 / 72, duration = beat * 32;
  const frequency = note => 440 * Math.pow(2, (note - 69) / 12);
  function makeMusic() {
    const buffer = context.createBuffer(1, Math.ceil(duration * rate), rate);
    const data = buffer.getChannelData(0);
    const chords = [[48,60,64,67,71],[45,57,60,64,67],[50,62,65,69,72],[43,55,59,62,69]];
    function note(midi, start, length, level, mellow = false) {
      const f = frequency(midi), first = Math.floor(start * rate), count = Math.floor(length * rate);
      for (let i = 0; i < count && first + i < data.length; i++) {
        const t = i / rate, attack = Math.min(1, t / .025), release = Math.min(1, (length - t) / .18);
        const wave = Math.sin(2 * Math.PI * f * t) + (mellow ? .06 : .2) * Math.sin(4 * Math.PI * f * t);
        data[first + i] += level * wave * attack * release * Math.exp(-t / (mellow ? 2.8 : .65));
      }
    }
    for (let bar = 0; bar < 8; bar++) {
      const chord = chords[bar % 4], start = bar * 4 * beat;
      note(chord[0], start, beat * 3.8, .14, true);
      for (let j = 1; j < chord.length; j++) note(chord[j], start + j * .045, beat * 3.5, .055, true);
      for (let j = 0; j < 4; j++) note(chord[1 + (j + bar) % 4] + 12, start + (j + .5) * beat, beat * .48, .085);
    }
    // Bound music output below alerts even when several notes overlap.
    let peak = 0; for (const value of data) peak = Math.max(peak, Math.abs(value));
    for (let i = 0; i < data.length; i++) data[i] *= .6 / Math.max(peak, 1);
    return buffer;
  }
  function setup() {
    if (!context) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return null;
      context = new AudioContext(); musicGain = context.createGain();
      musicGain.gain.value = enabled ? .13 : 0; musicGain.connect(context.destination);
      music = context.createBufferSource(); music.buffer = makeMusic(); music.loop = true;
      music.connect(musicGain); music.start();
    }
    return context;
  }
  const unlock = () => { try { const c = setup(); if (c && c.state !== 'running') c.resume().catch(() => {}); } catch (_) {} };
  // Browser audio starts after a genuine gesture; no synthetic click bypass.
  document.addEventListener('pointerdown', unlock, {capture:true});
  document.addEventListener('keydown', unlock, {capture:true});
  button.onclick = () => { enabled = !enabled; unlock(); if (musicGain) musicGain.gain.setTargetAtTime(enabled ? .13 : 0, context.currentTime, .08); label(); };
  function alertBuffer(seconds, fill) {
    try {
      const c = setup(); if (!c || c.state !== 'running') return;
      const buffer = c.createBuffer(1, Math.round(seconds * rate), rate), data = buffer.getChannelData(0);
      fill(data); const source = c.createBufferSource(), gain = c.createGain();
      source.buffer = buffer; gain.gain.value = .65;
      source.connect(gain); gain.connect(c.destination);
      source.onended = () => {source.disconnect();gain.disconnect();}; source.start(); return source;
    } catch (_) { /* Game continues when sound is unavailable. */ }
  }
  let activeAlarm = null;
  window.sobaAudio = {
    musicEnabled:enabled,
    toggleMusic(){button.onclick();},
    noodleReady() {
      if (activeAlarm) { try { activeAlarm.stop(); } catch (_) {} } // Restart one alarm for a newly ready pot.
      activeAlarm = alertBuffer(10, data => {
        for (let i = 0; i < data.length; i++) {
          const t = i / rate, pulse = t % .5;
          if (pulse < .26) {
            const envelope = Math.min(1, pulse / .01, (.26 - pulse) / .01);
            data[i] = .55 * envelope * Math.sin(2 * Math.PI * 1000 * t);
          }
        }
      });
    },
    doorBell() {
      alertBuffer(1.5, data => {
        for (let i = 0; i < data.length; i++) {
          const t = i / rate;
          const bell = (f, time) => time < 0 ? 0 : Math.min(1,time / .008) * Math.exp(-time * 4.8) * (Math.sin(2 * Math.PI * f * time) + .22 * Math.sin(2 * Math.PI * f * 2.76 * time));
          data[i] = .4 * (bell(1046.5,t) + bell(784,t - .28));
        }
      });
    }
  };
})();
