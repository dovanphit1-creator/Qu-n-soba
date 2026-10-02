import ast, os, sys, platform
from pathlib import Path
from types import SimpleNamespace
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
p=Path(__file__).resolve().parent;sys.path.insert(0,str(p/'game'))
from v2app import V2App as App
from camera import CameraMixin
from model import Party
calls=[];platform.window=SimpleNamespace(sobaAudio=SimpleNamespace(doorBell=lambda:calls.append('door'),noodleReady=lambda:calls.append('ready')))
tree=ast.parse((p/'entry.py').read_text());main=next(n for n in tree.body if isinstance(n,ast.AsyncFunctionDef));classes=[n for n in ast.walk(main) if isinstance(n,ast.ClassDef) and n.name in ('ReadySignal','BrowserApp')]
namespace={'App':App,'CameraMixin':CameraMixin,'Path':Path,'pg':__import__('pygame'),'__file__':str(p/'game/main.py')}
exec(compile(ast.Module(body=classes,type_ignores=[]),'entry.py','exec'),namespace)
a=namespace['BrowserApp'](headless=True,persistent=False)
a.world.place('square4',420,460,name='Audio test')
party=Party(1,1,['Kake soba'],['easy'],recipes=[['Nước dùng']],prices=[45000]);a.world.parties=[party];a.world.stock['Mì tươi']=10;a.world.stock['Nước dùng']=10
assert a.world.respond(1,'accept');assert calls==['door'];assert not a.world.respond(1,'accept');assert calls==['door'];None
a.persist() # Disposable web session deliberately does not serialize fixtures or saves.
a.sound.play();assert calls==['door','ready']
print('PASS: real admission bridge, no duplicate bell, disposable session, noodle alarm bridge')
