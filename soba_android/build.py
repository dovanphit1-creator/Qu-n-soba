"""Package the verified Python/mobile runtime as offline Android assets."""
from pathlib import Path
import io, json, shutil, tarfile, importlib.util, zipfile, gzip
ROOT=Path(__file__).resolve().parent
IOS=ROOT.parent/'soba_ios'

def build():
    spec=importlib.util.spec_from_file_location('ios_bundle',IOS/'build.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.build()
    assets=ROOT/'app/src/main/assets/game'
    if assets.exists():shutil.rmtree(assets)
    shutil.copytree(IOS/'Game', assets)
    archive=assets/'game-bundle.bin'
    (assets/'iphone.tar.gz').unlink(missing_ok=True)
    members=[]
    with zipfile.ZipFile(assets/'iphone.apk') as bundle:
        if bundle.testzip() is not None:raise ValueError('Corrupt source game bundle')
        for name in bundle.namelist():
            if name.endswith('/'):continue
            data=bundle.read(name)
            if name.endswith('/app.py'):
                data=data.decode().replace('iPhone','Android').encode()
            if name.endswith('/main.py'):
                data=data.decode().replace('iPhone','Android').replace('/ios-save','/android-save').encode()
            if name.endswith('/brand.py'):
                data=data.decode().replace("GAME_VERSION = '1.8.0'", "GAME_VERSION = '1.8.0-beta.1'").encode()
            members.append((name,data))
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w') as tar:
        for name,data in members:
            info=tarfile.TarInfo(name);info.size=len(data);tar.addfile(info,io.BytesIO(data))
    archive.write_bytes(gzip.compress(payload.getvalue(),mtime=0))
    assert gzip.decompress(archive.read_bytes())==payload.getvalue()
    # The runtime loads the tar, not its source ZIP. Remove duplicate sources.
    (assets/'iphone.apk').unlink(missing_ok=True)
    html=(assets/'index.html').read_text().replace('Bản iPhone','Bản Android').replace('iphone.tar.gz','game-bundle.bin')
    html=html.replace('/runtime/packages/', '/assets/game/runtime/packages/')
    rc=assets/'runtime/cpythonrc.py'
    rc.write_text(rc.read_text().replace('/runtime/packages/', '/assets/game/runtime/packages/'))
    html=html.replace('if(window.MM)window.MM.UME=true;', 'window.sobaStartRequested=true;if(window.MM)window.MM.UME=true;')
    html=html.replace('<head>', '<head><script src="native-bridge.js"></script>',1)
    (assets/'index.html').write_text(html)
    shutil.copy2(ROOT/'bridge.js',assets/'native-bridge.js')
    icons=ROOT/'app/src/main/res/drawable';icons.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT.parent/'soba_manual/assets/game.png',icons/'game.png')
    # Bundle dependency notices with the application, alongside the runtime.
    import importlib.metadata as metadata
    notices=assets/'licenses';shutil.copytree(ROOT/'licenses',notices,dirs_exist_ok=True)
    for name in ('pygbag','holidays','python-dateutil','six'):
        distribution=metadata.distribution(name)
        for entry in distribution.files:
            if 'license' in entry.name.lower() or entry.name=='CONTRIBUTORS':
                shutil.copy2(distribution.locate_file(entry),notices/(name+'-'+entry.name))
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',assets/'THIRD_PARTY_NOTICES.md')
    print('Android offline assets:',assets)
if __name__=='__main__':build()
