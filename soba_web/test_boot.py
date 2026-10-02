"""Execute the packaged HTML bootstrap with an audio-blocked browser and bad downloads."""
import ast, asyncio, io, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from contextlib import asynccontextmanager

root=Path(__file__).resolve().parent
html=(root/'index.html').read_text()
code=html.split('>#<!--',1)[1].split('asyncio.run(boot_game())',1)[0]
tree=ast.parse(code)
funcs=[n for n in tree.body if isinstance(n,ast.AsyncFunctionDef)]

async def scenario(corrupt=False, late_click=False):
    with tempfile.TemporaryDirectory() as temp:
        def mapped_path(value):
            return Path(temp)/'game' if str(value).startswith('/data/data/') else Path(value)
        calls=[]
        window=NS(sobaStartRequested=not late_click,MM=NS(UME=False),location=NS(host='example.test'),
                  transfer=NS(hidden=False),canvas=NS(style=NS(visibility='hidden')),
                  infobox=NS(style=NS(display=''),innerText=''),python=NS(config=NS(debug=False)),
                  config=NS(gui_divider=2),window_resize=lambda:None,
                  sobaStatus=lambda kind,detail='':calls.append((kind,detail)))
        @asynccontextmanager
        async def fopen(url, mode):
            assert url=='play/game.tar.gz?v=1.11.0',url
            data=b'bad download' if corrupt else (root/'game/build/web/game.tar.gz').read_bytes()
            yield io.BytesIO(data)
        def run_main(*args,**kwargs):calls.append(('mount',str(kwargs['loaderhome'])))
        async def source(main,**kwargs):
            assert main.is_file() and (main.parent/'camera.py').is_file()
            calls.append(('start',str(main)))
        async def toplevel(*args,**kwargs):pass
        shell=NS(source=source,interactive=lambda:None)
        platform=NS(window=window,document=NS(body=NS(style=NS())),fopen=fopen,run_main=run_main,shell=shell)
        sys.modules['embed']=NS(counter=lambda:0)
        sys.modules['boot_test']=NS()
        scope={'asyncio':asyncio,'Path':mapped_path,'platform':platform,'true':True,
               'PyConfig':NS(),'TopLevel_async_handler':NS(start_toplevel=toplevel),
               'window':window,'shell':shell,'__name__':'boot_test'}
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'packaged-bootstrap','exec'),scope)
        task=asyncio.create_task(scope['boot_game']())
        if late_click:
            await asyncio.sleep(.05)
            assert not any(kind=='start' for kind,_ in calls)
            window.sobaStartRequested=True
        await asyncio.wait_for(task,2)
        assert window.MM.UME is False
        if corrupt:
            assert any(kind=='error' and 'ReadError' in detail for kind,detail in calls)
            assert not any(kind=='start' for kind,_ in calls)
        else:assert any(kind=='start' for kind,_ in calls),calls

asyncio.run(scenario());asyncio.run(scenario(late_click=True));asyncio.run(scenario(True))
print('PASS: real HTML bootstrap starts with blocked/reset audio; damaged download shows error instead of hanging')
