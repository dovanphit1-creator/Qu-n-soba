"""Package the verified Python/mobile runtime as offline Android assets."""
from pathlib import Path
import io, json, shutil, tarfile, importlib.util
ROOT=Path(__file__).resolve().parent
IOS=ROOT.parent/'soba_ios'

def build():
    spec=importlib.util.spec_from_file_location('ios_bundle',IOS/'build.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.build()
    assets=ROOT/'app/src/main/assets/game'
    if assets.exists():shutil.rmtree(assets)
    shutil.copytree(IOS/'Game', assets)
    archive=assets/'iphone.tar.gz'
    members=[]
    with tarfile.open(archive) as tar:
        for member in tar:
            if not member.isfile():continue
            data=tar.extractfile(member).read()
            if member.name.endswith('/main.py'):
                data=data.decode().replace('iPhone','Android').replace('/ios-save','/android-save').encode()
            if member.name.endswith('/brand.py'):
                data=data.decode().replace("GAME_VERSION = '1.8.0'", "GAME_VERSION = '1.8.0-beta.1'").encode()
            members.append((member.name,data))
    with tarfile.open(archive,'w:gz') as tar:
        for name,data in members:
            info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
    # The runtime loads the tar, not its source ZIP. Remove duplicate sources.
    (assets/'iphone.apk').unlink(missing_ok=True)
    html=(assets/'index.html').read_text().replace('Bản iPhone','Bản Android')
    html=html.replace('/runtime/packages/', '/assets/game/runtime/packages/')
    rc=assets/'runtime/cpythonrc.py'
    rc.write_text(rc.read_text().replace('/runtime/packages/', '/assets/game/runtime/packages/'))
    html=html.replace('<head>', '<head><script src="native-bridge.js"></script>',1)
    (assets/'index.html').write_text(html)
    shutil.copy2(ROOT/'bridge.js',assets/'native-bridge.js')
    icons=ROOT/'app/src/main/res/drawable';icons.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT.parent/'soba_manual/assets/game.png',icons/'game.png')
    print('Android offline assets:',assets)
if __name__=='__main__':build()
