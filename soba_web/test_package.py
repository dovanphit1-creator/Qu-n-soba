import os,sys,tempfile,tarfile
from pathlib import Path
from unittest.mock import patch
from importlib.metadata import PackageNotFoundError
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
with tempfile.TemporaryDirectory() as d:
 with tarfile.open('soba_web/game/build/web/game.tar.gz') as t:t.extractall(d,filter='data')
 assets=Path(d)/'assets';sys.path.insert(0,str(assets))
 with patch('importlib.metadata.version',side_effect=PackageNotFoundError('missing distribution metadata')) as query:
  from app import App
  import holidays
  from vn_calendar import holiday_name
  from datetime import date
  a=App(headless=True,persistent=False);a.draw()
  assert a.world.cash==10000000
  assert holiday_name(date(2026,1,1))
  assert holidays.__version__=='0.105'
  query.assert_not_called()
  a.persist()
  print('PASS: packaged imports, Vietnam calendar, fresh session and first game frame without installed metadata')
 assert (assets/'assets/DejaVuSans.ttf').is_file()
