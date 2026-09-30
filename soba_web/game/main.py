import asyncio
import time
import traceback
import sys
from pathlib import Path

app = None

def status(kind, detail=''):
    if sys.platform == 'emscripten':
        import platform
        platform.window.sobaStatus(kind, detail)

async def main():
    global app
    try:
        status('loading', 'Đang mở quán…')
        import pygame as pg
        from app import App
        class BrowserApp(App):
            def font(self, size=22, bold=False):
                key=(size,bold)
                if key not in self.fonts:
                    name='DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
                    self.fonts[key]=pg.font.Font(str(Path(__file__).with_name('assets')/name),size)
                return self.fonts[key]
        app=BrowserApp(persistent=False)
        app.draw()
        status('ready')
        previous=time.perf_counter()
        while app.running:
            now=time.perf_counter()
            dt=now-previous;previous=now
            for event in pg.event.get():app.event(event)
            app.step(dt)
            app.draw()
            await asyncio.sleep(0)
        pg.quit()
        status('stopped', 'Bạn đã thoát game. Bấm tải lại để chơi ván mới.')
    except Exception:
        detail=traceback.format_exc()
        print(detail)
        status('error', detail)

asyncio.run(main())
