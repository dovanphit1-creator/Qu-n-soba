"""Build an offline iOS game bundle; never changes the disposable public web build."""
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'soba_manual'
STAGE = ROOT / 'build' / 'iphone'
OUTPUT = ROOT / 'Game'


def build():
    import holidays, dateutil, six
    from PIL import Image
    STAGE.mkdir(parents=True, exist_ok=True)
    for name in ('model', 'management', 'brand', 'vn_calendar', 'staff', 'staff_ui', 'catalog',
                 'audio', 'background', 'operations', 'finance', 'finance_ui', 'shifts', 'shifts_ui'):
        shutil.copy2(SOURCE / (name + '.py'), STAGE / (name + '.py'))
    shutil.copy2(ROOT / 'main.py', STAGE / 'main.py')
    app = (SOURCE / 'main.py').read_text().replace('noodle-ready.wav', 'noodle-ready.ogg')
    app = app.replace('tài khoản Windows', 'iPhone')
    (STAGE / 'app.py').write_text(app)
    brand = (STAGE / 'brand.py').read_text().replace("GAME_VERSION = '1.7.3'", "GAME_VERSION = '1.8.0'")
    (STAGE / 'brand.py').write_text(brand)
    for module in (holidays, dateutil):
        shutil.copytree(Path(module.__file__).parent, STAGE / module.__name__, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(six.__file__, STAGE / 'six.py')
    version = STAGE / 'holidays/version.py'
    version.write_text(version.read_text().replace('from importlib.metadata import version', '')
                       .replace('__version__ = version("holidays")', '__version__ = ' + repr(holidays.__version__)))
    assets = STAGE / 'assets'; assets.mkdir(exist_ok=True)
    for name in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'):
        shutil.copy2(Path('/usr/share/fonts/truetype/dejavu') / name, assets / name)
    shutil.copy2(SOURCE / 'assets/game.png', assets / 'game.png')
    shutil.copy2(SOURCE / 'assets/game.png', STAGE / 'favicon.png')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(SOURCE / 'assets/noodle-ready.wav'),
                    '-c:a', 'libvorbis', str(assets / 'noodle-ready.ogg')], check=True)
    subprocess.run([sys.executable, '-m', 'pygbag', '--build', '--no_opt', '--title', 'Quán Mì Của Tôi', str(STAGE)], check=True)
    shutil.copytree(STAGE / 'build/web', OUTPUT, dirs_exist_ok=True)
    html = (OUTPUT / 'index.html').read_text()
    html = html.replace('https://pygame-web.github.io/cdn/0.9.3/', './runtime/')
    html = html.replace('data-os="vtx,snd,gui"', 'data-os="stdout,snd,gui"')
    html = html.replace('import json\n', 'import json\nimport os\nos.environ["PYGPI"] = str(platform.window.location.origin) + "/runtime/packages/"\n', 1)
    import re
    html = re.sub(r'<script src="[^\"]*browserfs.min.js"></script>', '', html)
    html = html.replace('navigator.serviceWorker.register(', 'Promise.reject(')
    html = html.replace('fb_ar   :  1.77', 'fb_ar   :  1.6').replace('fb_width : "1280"', 'fb_width : "1600"').replace('fb_height : "720"', 'fb_height : "1000"')
    html = html.replace('lang="en-us"', 'lang="vi"').replace('Ready to start ! Please click/touch page', 'Chạm để bắt đầu')
    html = html.replace('</head>', '<style>html,body{margin:0;overflow:hidden;background:#26372e;color:#fff2d2;touch-action:none}canvas{touch-action:none}#pyconsole,#crt,#dlg,.iframe{display:none!important}</style></head>')
    boot = (ROOT.parent / 'soba_web/boot-status.html').read_text()
    boot = re.sub(r'<a href="[^\"]+">Tải bản Windows</a>', '', boot)
    boot = boot.replace('Quán Mì của tôi', 'Quán Mì Của Tôi').replace('Bản web không lưu. Tải lại hoặc đóng trang là chơi từ đầu.', 'Bản iPhone · Tiến trình lưu riêng trên máy.')
    boot = boot.replace('Tải lại game', 'Mở lại game').replace('location.reload()', "window.webkit.messageHandlers.game.postMessage({kind:'reload'})")
    html = html.replace('</body>', boot + '<script>const nativeStatus=window.sobaStatus;window.sobaStatus=(state,detail)=>{nativeStatus(state,detail);if(state==="ready")window.webkit.messageHandlers.game.postMessage({kind:"ready"})};</script></body>')
    (OUTPUT / 'index.html').write_text(html)
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
