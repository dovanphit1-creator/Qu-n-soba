"""iOS entry point; only this edition uses the native save/keyboard bridge."""
import asyncio
import base64
import json
import os
import time
import traceback
from pathlib import Path

import pygame as pg
import platform

os.environ['LOCALAPPDATA'] = '/ios-save'
from app import App
from model import save_path


class IPhoneApp(App):
    def font(self, size=22, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
            self.fonts[key] = pg.font.Font(str(Path(__file__).with_name('assets') / name), size)
        return self.fonts[key]

    def persist(self):
        if not super().persist():
            return False
        path = save_path()
        backups = {p.name: base64.b64encode(p.read_bytes()).decode()
                   for p in path.parent.glob('*.bak')}
        platform.window.sobaIOSSave(path.read_text(), json.dumps(backups))
        return True


async def main():
    try:
        initial = str(platform.window.sobaIOSInitialSave)
        if initial:
            path = save_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(initial))
        app = IPhoneApp(persistent=True)
        app.draw()
        platform.window.sobaStatus('ready', '')
        previous = time.perf_counter()
        finger = None
        asked = None
        while app.running:
            now = time.perf_counter()
            # iOS suspends apps; never treat a long suspension as a giant frame.
            dt = min(now - previous, 0.25)
            previous = now
            for event in pg.event.get():
                if event.type in (pg.FINGERDOWN, pg.FINGERMOTION, pg.FINGERUP):
                    if event.type == pg.FINGERDOWN and finger is None:
                        finger = event.finger_id
                    if event.finger_id != finger:
                        continue
                    w, h = app.display.get_size()
                    pos = (int(event.x * w), int(event.y * h))
                    if event.type == pg.FINGERMOTION:
                        translated = pg.event.Event(pg.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(1, 0, 0))
                    else:
                        translated = pg.event.Event(pg.MOUSEBUTTONDOWN if event.type == pg.FINGERDOWN else pg.MOUSEBUTTONUP,
                                                    pos=pos, button=1)
                    app.event(translated)
                    if event.type == pg.FINGERUP:
                        finger = None
                elif event.type in (pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP) and getattr(event, 'touch', False):
                    continue  # SDL also synthesizes mouse events from the same touch.
                else:
                    app.event(event)
            for command in json.loads(str(platform.window.sobaIOSDrain())):
                if command['kind'] == 'save':
                    app.drag = app.down = app.clean_hold = None
                    app.world.player_cleaning = None
                    finger = None
                    app.persist()
                elif command['kind'] == 'saveError':
                    app.last_warning = 'Chưa lưu được trên iPhone. Hãy kiểm tra dung lượng trống.'
                elif command['kind'] == 'text':
                    field = command['field']
                    if field == app.input_focus:
                        attr = {'name': 'menu_name', 'price': 'menu_price', 'shift_name': 'shift_name'}.get(field)
                        if attr:
                            setattr(app, attr, '')
                            app.event(pg.event.Event(pg.TEXTINPUT, text=command['text']))
                        app.input_focus = None
                        pg.key.stop_text_input()
                elif command['kind'] == 'cancelText':
                    app.input_focus = None
                    pg.key.stop_text_input()
            focus = app.input_focus
            if focus and focus != asked:
                attr = {'name': 'menu_name', 'price': 'menu_price', 'shift_name': 'shift_name'}.get(focus)
                if attr:
                    platform.window.sobaIOSEdit(focus, str(getattr(app, attr)))
            asked = focus
            app.step(dt)
            app.draw()
            await asyncio.sleep(0)
        app.persist()
        pg.quit()
        platform.window.sobaStatus('stopped', 'Đã lưu game trên iPhone. Bấm mở lại để tiếp tục.')
    except Exception:
        detail = traceback.format_exc()
        print(detail)
        platform.window.sobaStatus('error', detail)


asyncio.run(main())
