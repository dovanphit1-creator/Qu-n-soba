"""Queued Vietnamese speech. Desktop engine is bundled and works offline."""
import sys
from pathlib import Path

_queue=None

def render_vi(message):
    import subprocess,tempfile
    engine=Path(__file__).with_name('assets')/'speech'
    exe=engine/'espeak-ng.exe'
    with tempfile.TemporaryDirectory(prefix='quanmi-voice-') as d:
        out=Path(d)/'voice.wav'
        subprocess.run([str(exe),'--path='+str(engine),'-v','vi','-s','160','-w',str(out),'--stdin'],input=message.encode('utf-8'),check=True,timeout=30,creationflags=0x08000000 if sys.platform=='win32' else 0,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return out.read_bytes()

def speak(message,dishes=None):
    if sys.platform=='emscripten':
        import platform
        try:platform.window.sobaSpeak(message)
        except Exception:pass
    elif sys.platform=='win32' and not any(a in sys.argv for a in ('--smoke-test','--verify-new-player')):
        _enqueue(message)


def _enqueue(message):
    global _queue
    import threading,queue,time,io
    if _queue is None:
        _queue=queue.Queue(maxsize=10)
        def worker():
            import pygame as pg
            while True:
                text=_queue.get()
                try:
                    wave=render_vi(text)
                    if pg.mixer.get_init():
                        channel=pg.mixer.Channel(7)
                        channel.play(pg.mixer.Sound(io.BytesIO(wave)))
                        while channel.get_busy():time.sleep(.05)
                except Exception:
                    # Keep subtitles in the game's log if the audio device is unavailable.
                    pass
        threading.Thread(target=worker,daemon=True).start()
    try:_queue.put_nowait(message)
    except queue.Full:pass
