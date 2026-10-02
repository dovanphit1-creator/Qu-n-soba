"""Assemble the already-tested web build while retaining native download files."""
from pathlib import Path
import shutil,json
root=Path(__file__).resolve().parent
site=root.parent.parent/'dist'
shutil.copytree(root/'game/build/web',site/'play',dirs_exist_ok=True)
for name in ('index.html','game-audio.js','updates.js','mobile-presentation.js','manifest.webmanifest','v2-text.js'):
 shutil.copy2(root/name,site/name)
for p in (site/'version.json',site/'play/version.json'):p.write_text(json.dumps({'game_version':'2.0.0'}))
print('Packaged web 2.0.0')
