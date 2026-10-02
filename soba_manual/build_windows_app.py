"""Build the existing standalone game with an early native image splash."""
import subprocess,sys
from pathlib import Path
from brand import GAME_TITLE

args=[sys.executable,'-X','utf8','-m','PyInstaller.utils.cliutils.makespec','--onefile','--windowed','--name',GAME_TITLE,'--icon','soba_manual/assets/game.ico','--version-file','soba_manual/assets/version.txt','--add-data','soba_manual/assets;assets','--paths','soba_manual','--collect-all','holidays','--hidden-import','pyi_splash','--splash','soba_manual/assets/loading-windows.png','soba_manual/main.py']
subprocess.run(args,check=True)
spec=Path(GAME_TITLE+'.spec')
s=spec.read_text().replace('text_pos=None,','text_pos=None,\n    max_img_size=(960,540),')
spec.write_text(s)
subprocess.run([sys.executable,'-X','utf8','-m','PyInstaller','--noconfirm','--clean',str(spec)],check=True)
