"""Build disposable-session browser edition from the shared Python game."""
import shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GAME=ROOT/'game'
SOURCE=ROOT.parent/'soba_manual'
GAME.mkdir(exist_ok=True)
import holidays, dateutil, six
for module in (holidays,dateutil):
    shutil.copytree(Path(module.__file__).parent,GAME/module.__name__,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(six.__file__,GAME/'six.py')
# Browser bundles have no installed distribution metadata. Freeze the pinned version.
version_file=GAME/'holidays/version.py'
version_file.write_text(version_file.read_text().replace('from importlib.metadata import version', '').replace('__version__ = version("holidays")', '__version__ = '+repr(holidays.__version__)))
(GAME/'assets').mkdir(exist_ok=True)
for name in ('DejaVuSans.ttf','DejaVuSans-Bold.ttf'):
    shutil.copy2(Path('/usr/share/fonts/truetype/dejavu')/name,GAME/'assets'/name)
shutil.copy2(SOURCE/'assets/game.png',GAME/'assets/game.png')
shutil.copy2(SOURCE/'assets/game.png',GAME/'favicon.png')
(GAME/'assets/noodle-ready.wav').unlink(missing_ok=True)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(SOURCE/'assets/noodle-ready.wav'),'-c:a','libvorbis',str(GAME/'assets/noodle-ready.ogg')],check=True)
for name in ('model.py','management.py','brand.py','vn_calendar.py','staff.py','staff_ui.py','catalog.py','audio.py','background.py','operations.py','finance.py','finance_ui.py','shifts.py','shifts_ui.py'):
    shutil.copy2(SOURCE/name,GAME/name)
(GAME/'app.py').write_text((SOURCE/'main.py').read_text().replace('noodle-ready.wav','noodle-ready.ogg'))
subprocess.run([sys.executable,'-m','pygbag','--build','--no_opt','--title','Quán Mì Của Tôi','--icon',str(GAME/'favicon.png'),str(GAME)],check=True)
p=GAME/'build/web/index.html'
s=p.read_text()
s=s.replace('lang="en-us"','lang="vi"').replace('Ready to start ! Please click/touch page','Đã sẵn sàng — bấm vào đây để chơi')
s=s.replace('Downloading...', 'Đang tải Quán Mì Của Tôi…').replace('installing {pkg}', 'Đang chuẩn bị game…')
s=s.replace('"#7f7f7f"','"#26372e"').replace('fb_ar   :  1.77','fb_ar   :  1.6').replace('fb_width : "1280"','fb_width : "1600"').replace('fb_height : "720"','fb_height : "1000"')
s=s.replace('</head>','<style>body{background:#26372e!important;color:#fff2d2;font-family:Arial,sans-serif}#pyconsole,#crt,#dlg,.iframe{display:none!important}#infobox{color:#fff2d2!important;background:#26372e!important;padding:20px;font:20px Arial}</style></head>')
s=s.replace('</body>','<script>window.addEventListener("pageshow",e=>{if(e.persisted)location.reload()});</script></body>')
s=s.replace('Loading, please wait ...','Đang tải game, vui lòng chờ…')
s=s.replace('</body>', (ROOT/'boot-status.html').read_text()+'<script type="module" src="voice.js"></script></body>')
p.write_text(s)
# Serve the game directly, without nesting a WebAssembly runtime in an iframe.
root_html=s.replace('platform.fopen("game.apk"','platform.fopen("play/game.apk"').replace('platform.fopen("game.tar.gz"','platform.fopen("play/game.tar.gz"').replace('href="favicon.png"','href="icon.png"')
(ROOT/'index.html').write_text(root_html)
print('Browser build ready:',p.parent)

shutil.copytree(ROOT/'voice',GAME/'build/web/voice',dirs_exist_ok=True)
shutil.copy2(ROOT/'voice.js',GAME/'build/web/voice.js')
