import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from main import App
from model import World

class SessionModes(unittest.TestCase):
    def test_web_ignores_existing_save_and_never_writes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json'
            w=World();w.cash=123456;w.save(path)
            before=path.read_bytes()
            with patch('main.save_path', return_value=path) as locate:
                a=App(headless=True,persistent=False)
                self.assertEqual(a.world.cash,10000000)
                a.world.cash=99;a.persist();a.draw()
                b=App(headless=True,persistent=False)
                self.assertEqual(b.world.cash,10000000)
                locate.assert_not_called()
            self.assertEqual(path.read_bytes(),before)
    def test_desktop_saves_and_restores(self):
        with tempfile.TemporaryDirectory() as d:
            with patch('main.save_path',return_value=Path(d)/'save.json'):
                a=App(headless=True);a.world.cash=987654;a.persist()
                b=App(headless=True)
                self.assertEqual(b.world.cash,987654)
if __name__=='__main__':unittest.main()
