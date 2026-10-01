"""Generate the original two-note ready signal; no external audio assets."""
from pathlib import Path
import math,struct,wave

def build():
    path=Path(__file__).with_name('assets')/'noodle-ready.wav'
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050)
        frames=[]
        for n in range(int(.8*22050)):
            t=n/22050;local=t if t<.3 else t-.4
            value=0 if .3<t<.4 else int(9500*max(0,1-local/.4)**2*math.sin(2*math.pi*(880 if t<.3 else 1174.66)*local))
            frames.append(struct.pack('<h',value))
        f.writeframes(b''.join(frames))
if __name__=='__main__':build()
