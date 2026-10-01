"""Nonblocking operating-system speech for ticket announcements."""
import sys

def speak(message):
    if sys.platform=='emscripten':
        import platform
        try:platform.window.sobaSpeak(message)
        except Exception:pass
    elif sys.platform=='win32':
        import subprocess,base64
        # Message is data encoded as UTF-8 base64, never executable PowerShell text.
        value=base64.b64encode(message.encode('utf-8')).decode('ascii')
        script="$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+value+"')); $v=New-Object -ComObject SAPI.SpVoice; $voices=$v.GetVoices(); foreach($voice in $voices){if($voice.GetAttribute('Language') -match '42a'){$v.Voice=$voice;break}}; $v.Speak($text)|Out-Null"
        # Serialize utterances so staff announcements do not talk over each other.
        _enqueue(script)

_queue=None

def _enqueue(script):
    global _queue
    import threading,queue,subprocess
    if _queue is None:
        _queue=queue.Queue(maxsize=6)
        def worker():
            while True:
                s=_queue.get()
                try:subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',__import__('base64').b64encode(s.encode('utf-16le')).decode('ascii')],creationflags=0x08000000,timeout=25,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                except (OSError,subprocess.TimeoutExpired):pass
        threading.Thread(target=worker,daemon=True).start()
    try:_queue.put_nowait(script)
    except queue.Full:pass
