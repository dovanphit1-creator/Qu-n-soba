"""Build disposable-session browser edition from the shared Python game."""
import shutil, subprocess, sys, io, tarfile, zipfile
import soundfile
import runpy
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
shutil.copy2(SOURCE/'assets/loading-restaurant.jpg',GAME/'assets/loading-restaurant.jpg')
for old_sound in ('noodle-ready.wav','noodle-ready.ogg'):
    (GAME/'assets'/old_sound).unlink(missing_ok=True)
for name in ('model.py','management.py','brand.py','vn_calendar.py','staff.py','staff_ui.py','catalog.py','audio.py','background.py','operations.py','finance.py','finance_ui.py','shifts.py','shifts_ui.py'):
    shutil.copy2(SOURCE/name,GAME/name)
shutil.copy2(ROOT/'entry.py',GAME/'main.py')
shutil.copy2(ROOT/'camera.py',GAME/'camera.py')
(GAME/'audio.py').write_text('def speak(message,dishes=None):\n    pass  # Web edition keeps subtitles, with no spoken dish names.\n')
(GAME/'brand.py').write_text((SOURCE/'brand.py').read_text().replace("GAME_VERSION = '1.7.4'","GAME_VERSION = '1.9.0'"))
(GAME/'app.py').write_text((SOURCE/'main.py').read_text().replace("if pg.mixer.get_init():self.sound=pg.mixer.Sound(str(Path(__file__).with_name('assets')/'noodle-ready.wav'))","self.sound=None  # Web audio is managed independently by Web Audio."))
app_file=GAME/'app.py'
app_file.write_text(app_file.read_text().replace('Tự đón khách, nhận phiếu, nấu mì, phục vụ và dọn sạch khi hết ca.', 'Chạm sàn trống, giữ và kéo để đi. WASD / mũi tên dùng trên máy tính.').replace('Phím 1/2/3 đổi tầng cả khi đang kéo. Quản lý bàn/tầng, nhà cung cấp và menu khi đóng quán.', 'Chạm sàn trống, giữ và kéo: đi. Thả: dừng. WASD / mũi tên cũng đi. Phím 1/2/3 đổi tầng.'))
app_file.write_text(app_file.read_text().replace('(1207, 837), 19,','(1207, 817), 12,'))
app_file.write_text(app_file.read_text().replace("self.text(f'Sàn: {len(w.dirt)} chỗ bẩn', (1207, 817), 12, RED if w.dirt else GREEN, True)", '# Floor dirt count is displayed in the mini-map.'))
subprocess.run([sys.executable,'-m','pygbag','--build','--no_opt','--title','Quán Mì Của Tôi','--icon',str(GAME/'favicon.png'),str(GAME)],check=True)
p=GAME/'build/web/index.html'
s=p.read_text()
s=s.replace('lang="en-us"','lang="vi"').replace('Ready to start ! Please click/touch page','Đã sẵn sàng — bấm vào đây để chơi')
s=s.replace('Downloading...', 'Đang tải Quán Mì Của Tôi…').replace('installing {pkg}', 'Đang chuẩn bị game…')
s=s.replace('"#7f7f7f"','"#26372e"').replace('fb_ar   :  1.77','fb_ar   :  1.6').replace('fb_width : "1280"','fb_width : "1600"').replace('fb_height : "720"','fb_height : "1000"')
s=s.replace('</head>','<style>body{background:#26372e!important;color:#fff2d2;font-family:Arial,sans-serif}#pyconsole,#crt,#dlg,.iframe{display:none!important}#infobox{color:#fff2d2!important;background:#26372e!important;padding:20px;font:20px Arial}</style></head>')
s=s.replace('</body>','<script>window.addEventListener("pageshow",e=>{if(e.persisted)location.reload()});</script></body>')
s=s.replace('Loading, please wait ...','Đang tải game, vui lòng chờ…')
s=s.replace('</body>', (ROOT/'boot-status.html').read_text().replace('__LOADING_VERSION__','1.9.0')+'<script src="game-audio.js"></script><script src="updates.js"></script></body>')
# Start gameplay after our explicit button, independently of the legacy silent-audio test.
start=s.index('    # test/wait user media interaction')
end=s.index('    # start async top level machinery',start)
s=s[:start]+"    while not platform.window.sobaStartRequested:\n        await asyncio.sleep(.1)\n\n"+s[end:]
s=s.replace('ume_block : 1','ume_block : 0')
s=s.replace('<script src="https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js"></script>', '')
s=s.replace('asyncio.run( custom_site() )', '''async def boot_game():
    try:
        platform.window.sobaStatus('loading', 'Đang tải dữ liệu game…')
        await custom_site()
    except Exception:
        import traceback
        platform.window.sobaStatus('error', traceback.format_exc())

asyncio.run(boot_game())''')
s=s.replace('platform.fopen("game.apk"','platform.fopen("game.apk?v=1.9.0"').replace('platform.fopen("game.tar.gz"','platform.fopen("game.tar.gz?v=1.9.0"')
s=s.replace('<script src="game-audio.js">','<script src="game-audio.js?v=1.9.0">').replace('<script src="updates.js">','<script src="updates.js?v=1.9.0">')
s=s.replace('<meta name="viewport" content="width=device-width, initial-scale=1.0">','<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">').replace('<meta name="viewport" content="height=device-height, initial-scale=1.0">','')
s=s.replace('</head>','<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="theme-color" content="#18291e"><link rel="manifest" href="manifest.webmanifest"></head>')
s=s.replace('</body>',(ROOT/'mobile-presentation.html').read_text()+'<script src="mobile-presentation.js?v=1.9.0"></script></body>')
p.write_text(s)
# Write a closed archive; pygbag can leave an unfinished gzip footer.
with zipfile.ZipFile(p.parent/'game.apk') as source:
    with tarfile.open(p.parent/'game-closed.tar.gz','w:gz') as archive:
        for name in source.namelist():
            if name.endswith('/'):continue
            data=source.read(name);entry=tarfile.TarInfo(name);entry.size=len(data);archive.addfile(entry,io.BytesIO(data))
(p.parent/'game-closed.tar.gz').replace(p.parent/'game.tar.gz')
with tarfile.open(p.parent/'game.tar.gz') as check:
    for member in check:
        if member.isfile():check.extractfile(member).read()
for folder in (p.parent,ROOT):
    shutil.copy2(SOURCE/'assets/loading-restaurant.jpg',folder/'loading-restaurant.jpg')
    shutil.copy2(SOURCE/'assets/game.png',folder/'game-icon.png')
# Serve the game directly, without nesting a WebAssembly runtime in an iframe.
root_html=s.replace('platform.fopen("game.apk?v=1.9.0"','platform.fopen("play/game.apk?v=1.9.0"').replace('platform.fopen("game.tar.gz?v=1.9.0"','platform.fopen("play/game.tar.gz?v=1.9.0"').replace('href="favicon.png"','href="icon.png"')
(ROOT/'index.html').write_text(root_html)
print('Browser build ready:',p.parent)

shutil.copy2(ROOT/'game-audio.js',GAME/'build/web/game-audio.js')
shutil.copy2(ROOT/'updates.js',GAME/'build/web/updates.js')

for name in ('mobile-presentation.js','manifest.webmanifest'):
    shutil.copy2(ROOT/name,GAME/'build/web'/name)
