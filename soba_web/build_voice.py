"""Fetch a pinned, separately executed browser speech engine and its GPL source notice."""
from pathlib import Path
import urllib.request,hashlib
ROOT=Path(__file__).parent
COMMIT='7ab07eba2d966ce45040c88d9be953e1d68640e7'
dest=ROOT/'voice';dest.mkdir(exist_ok=True)
for name in ('espeak-ng.js','espeak-ng.data','COPYING'):
    url=f'https://raw.githubusercontent.com/echogarden-project/espeak-ng-emscripten/{COMMIT}/{name}'
    with urllib.request.urlopen(url,timeout=60) as r:data=r.read()
    (dest/name).write_bytes(data)
    print(name,len(data),hashlib.sha256(data).hexdigest())
(dest/'SOURCES.txt').write_text(f'eSpeak NG companion program, GPL-3.0. Compiled JS and data source: https://github.com/echogarden-project/espeak-ng-emscripten/tree/{COMMIT}\nCorresponding C++ fork source/build instructions: https://github.com/echogarden-project/espeak-ng/tree/fork\nAdapter source: voice-worker.js (GPL-3.0).\n',encoding='utf-8')
(dest/'voice-worker.js').write_bytes((ROOT/'voice-worker.js').read_bytes())
