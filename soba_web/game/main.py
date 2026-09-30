import asyncio
import time
from pathlib import Path
import pygame as pg
from app import App

app = None

class BrowserApp(App):
    def font(self, size=22, bold=False):
        key=(size,bold)
        if key not in self.fonts:
            name='DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
            self.fonts[key]=pg.font.Font(str(Path(__file__).with_name('assets')/name),size)
        return self.fonts[key]

async def main():
    global app
    app=BrowserApp(persistent=False)
    previous=time.perf_counter()
    while app.running:
        now=time.perf_counter()
        dt=now-previous;previous=now
        for event in pg.event.get():app.event(event)
        app.step(dt)
        app.draw()
        await asyncio.sleep(0)
    pg.quit()

asyncio.run(main())
