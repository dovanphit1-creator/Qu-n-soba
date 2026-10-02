"""Build an offline iOS game bundle; never changes the disposable public web build."""
import re
import hashlib
import json
import shutil
import subprocess
import sys
import io
import tarfile
import zipfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'soba_manual'
STAGE = ROOT / 'build' / 'iphone'
OUTPUT = ROOT / 'Game'


def build():
    import holidays, dateutil, six
    import soundfile
    from PIL import Image
    STAGE.mkdir(parents=True, exist_ok=True)
    for name in ('model', 'management', 'brand', 'vn_calendar', 'staff', 'staff_ui', 'catalog',
                 'audio', 'background', 'operations', 'finance', 'finance_ui', 'shifts', 'shifts_ui'):
        shutil.copy2(SOURCE / (name + '.py'), STAGE / (name + '.py'))
    shutil.copy2(ROOT / 'main.py', STAGE / 'main.py')
    app = (SOURCE / 'main.py').read_text().replace('noodle-ready.wav', 'noodle-ready.ogg')
    app = app.replace('tài khoản Windows', 'iPhone')
    app = app.replace('pg.display.set_mode(size, pg.RESIZABLE)', 'pg.display.set_mode((1600, 1000))')
    (STAGE / 'app.py').write_text(app)
    brand = re.sub(r"GAME_VERSION = '[^']+'", "GAME_VERSION = '1.8.0'", (STAGE / 'brand.py').read_text())
    (STAGE / 'brand.py').write_text(brand)
    for module in (holidays, dateutil):
        shutil.copytree(Path(module.__file__).parent, STAGE / module.__name__, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(six.__file__, STAGE / 'six.py')
    version = STAGE / 'holidays/version.py'
    version.write_text(version.read_text().replace('from importlib.metadata import version', '')
                       .replace('__version__ = version("holidays")', '__version__ = ' + repr(holidays.__version__)))
    assets = STAGE / 'assets'; assets.mkdir(exist_ok=True)
    font_archive = ROOT / 'build/dejavu-fonts-ttf-2.37.tar.bz2'
    font_hash = 'fa9ca4d13871dd122f61258a80d01751d603b4d3ee14095d65453b4e846e17d7'
    if not font_archive.exists() or hashlib.sha256(font_archive.read_bytes()).hexdigest() != font_hash:
        with urllib.request.urlopen('https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2', timeout=90) as response:
            font_data = response.read()
        if hashlib.sha256(font_data).hexdigest() != font_hash:
            raise ValueError('DejaVu font checksum mismatch')
        font_archive.write_bytes(font_data)
    with tarfile.open(font_archive) as fonts:
        for name in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'):
            (assets / name).write_bytes(fonts.extractfile('dejavu-fonts-ttf-2.37/ttf/' + name).read())
        (assets / 'DejaVu-LICENSE.txt').write_bytes(fonts.extractfile('dejavu-fonts-ttf-2.37/LICENSE').read())
    shutil.copy2(SOURCE / 'assets/game.png', assets / 'game.png')
    shutil.copy2(SOURCE / 'assets/loading-restaurant.jpg', assets / 'loading-restaurant.jpg')
    shutil.copy2(SOURCE / 'assets/game.png', STAGE / 'favicon.png')
    samples, rate = soundfile.read(SOURCE / 'assets/noodle-ready.wav')
    soundfile.write(assets / 'noodle-ready.ogg', samples, rate, subtype='VORBIS')
    subprocess.run([sys.executable, '-m', 'pygbag', '--build', '--no_opt', '--title', 'Quán Mì Của Tôi', str(STAGE)], check=True)
    shutil.copytree(STAGE / 'build/web', OUTPUT, dirs_exist_ok=True)
    # Pygbag's gzip writer can leave its footer unfinished on process exit.
    # Build a fully closed tar from the validated APK, then read every member.
    with zipfile.ZipFile(OUTPUT / 'iphone.apk') as archive:
        if archive.testzip() is not None:
            raise ValueError('Corrupt game APK')
        with tarfile.open(OUTPUT / 'iphone.tar.gz', 'w:gz') as tar:
            for name in archive.namelist():
                if name.endswith('/'):
                    continue
                data = archive.read(name)
                info = tarfile.TarInfo(name); info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    with tarfile.open(OUTPUT / 'iphone.tar.gz') as tar:
        for member in tar:
            if member.isfile():
                tar.extractfile(member).read()
    html = (OUTPUT / 'index.html').read_text()
    html = html.replace('https://pygame-web.github.io/cdn/0.9.3/', './runtime/')
    html = html.replace('data-os="vtx,snd,gui"', 'data-os="stdout,snd,gui"')
    html = html.replace('import json\n', 'import json\nimport os\nos.environ["PYGPI"] = str(platform.window.location.origin) + "/runtime/packages/"\n', 1)
    html = re.sub(r'<script src="[^\"]*browserfs.min.js"></script>', '', html)
    html = html.replace('navigator.serviceWorker.register(', 'Promise.reject(')
    html = html.replace('fb_ar   :  1.77', 'fb_ar   :  1.6').replace('fb_width : "1280"', 'fb_width : "1600"').replace('fb_height : "720"', 'fb_height : "1000"')
    html = html.replace('lang="en-us"', 'lang="vi"').replace('Ready to start ! Please click/touch page', 'Chạm để bắt đầu')
    html = html.replace('</head>', '<style>html,body{margin:0;overflow:hidden;background:#26372e!important;color:#fff2d2;touch-action:none}canvas{touch-action:none}#stdout,#status,#progress,#spinner,#pyconsole,#crt,#dlg,.iframe{display:none!important}</style></head>')
    boot = (ROOT.parent / 'soba_web/boot-status.html').read_text().replace('__LOADING_VERSION__','1.8.0')
    shutil.copy2(SOURCE/'assets/loading-restaurant.jpg',OUTPUT/'loading-restaurant.jpg')
    shutil.copy2(SOURCE/'assets/game.png',OUTPUT/'game-icon.png')
    boot = re.sub(r'<a href="[^\"]+">Tải bản Windows</a>', '', boot)
    boot = boot.replace('Quán Mì của tôi', 'Quán Mì Của Tôi').replace('Bản web không lưu. Tải lại hoặc đóng trang là chơi từ đầu.', 'Bản iPhone · Tiến trình lưu riêng trên máy.')
    boot = boot.replace('Tải lại game', 'Mở lại game').replace('location.reload()', "window.webkit.messageHandlers.game.postMessage({kind:'reload'})")
    html = html.replace('</body>', boot + '<script>const nativeStatus=window.sobaStatus;window.sobaStatus=(state,detail)=>{nativeStatus(state,detail);if(state==="ready")window.webkit.messageHandlers.game.postMessage({kind:"ready"})};</script><script src="mobile-ui.js"></script></body>')
    (OUTPUT / 'index.html').write_text(html)
    shutil.copy2(ROOT / 'mobile-ui.js', OUTPUT / 'mobile-ui.js')
    for entry in json.loads((ROOT / 'runtime-lock.json').read_text()):
        target = OUTPUT / entry['path']; target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != entry['sha256']:
            with urllib.request.urlopen(entry['url'], timeout=90) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Runtime checksum mismatch: ' + entry['path'])
            target.write_bytes(data)
    rc = OUTPUT / 'runtime/cpythonrc.py'
    rc.write_text(rc.read_text().replace('import __EMSCRIPTEN__ as platform\n', 'import __EMSCRIPTEN__ as platform\nos.environ["PYGPI"] = str(platform.window.location.origin) + "/runtime/packages/"\n', 1))
    (OUTPUT / 'runtime/empty.html').write_text('<!doctype html><title></title>')
    packages = OUTPUT / 'runtime/packages'
    (packages / 'index-0.9.3-cp312.json').write_text(json.dumps({
        '-CDN-': './runtime/packages/',
        'pygame': 'cp312/pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl'}))
    icons = ROOT / 'Assets.xcassets/AppIcon.appiconset'; icons.mkdir(parents=True, exist_ok=True)
    icon = Image.open(SOURCE / 'assets/game.png').convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS)
    icon.save(icons / 'AppIcon.png')
    (icons / 'Contents.json').write_text(json.dumps({'images':[{'filename':'AppIcon.png','idiom':'universal','platform':'ios','size':'1024x1024'}], 'info':{'author':'xcode','version':1}}))
    (ROOT / 'Assets.xcassets/Contents.json').write_text('{"info":{"author":"xcode","version":1}}')
    print('Offline iOS resources:', OUTPUT)


if __name__ == '__main__':
    build()
