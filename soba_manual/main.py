"""Top-down manual restaurant game. Run: python soba_manual/main.py."""
import math
import json
import os
import sys
from pathlib import Path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
if '--smoke-test' in sys.argv or '--verify-new-player' in sys.argv:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame as pg
from model import (World, RECIPES, STOCK_COST, TABLE_LAYOUT, POT_POS, BOWL_POS,
                   COOK_SECONDS, LIFT_WINDOW, save_path, vnd, DISH_COST, DIRT_POS)

from vn_calendar import WEEKDAYS
from management import ManagementUI
from brand import GAME_TITLE, WINDOWS_APP_ID, GAME_VERSION, PUBLISHER

W, H = 1600, 1000
INK = '#26372e'
CREAM = '#fff2d2'
GOLD = '#f4ba53'
GREEN = '#426f57'
RED = '#ba4d3c'
TOPPING_COLOR = {'Nước dùng': '#b77b32', 'Hành': '#64a950', 'Tôm': '#ee9060', 'Bò': '#8e5443', 'Trứng': '#f6d15d'}
PEOPLE = ['#487c98', '#b65e4b', '#728855', '#9b7ba0', '#e0a444', '#617894']
SINK = pg.Rect(799, 281, 347, 66)
RAW = pg.Rect(793, 558, 191, 62)
TRASH = pg.Rect(1001, 558, 143, 62)
MACHINE = pg.Rect(617, 286, 101, 100)
TICKET = pg.Rect(719, 326, 47, 66)
TOPPING_RECTS = {name: pg.Rect(793 + i * 71, 650, 65, 68) for i, name in enumerate(TOPPING_COLOR)}


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class App(ManagementUI):
    def __init__(self, headless=False, persistent=True):
        self.persistent=persistent
        self.update_queue=None
        self.available_update=None
        self.update_notified=False
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
        pg.init()
        if headless:
            size = (1280, 800)
        else:
            info = pg.display.Info()
            size = (min(1440, info.current_w - 50), min(900, info.current_h - 75))
        self.display = pg.display.set_mode(size, pg.RESIZABLE)
        pg.display.set_caption(GAME_TITLE)
        pg.display.set_icon(pg.image.load(str(Path(__file__).with_name('assets')/'game.png')))
        self.canvas = pg.Surface((W, H))
        self.clock = pg.time.Clock()
        self.fonts = {}
        self.world = World()
        self.selected = 0
        self.drag = None
        self.down = None
        self.mouse = (0, 0)
        self.buttons = []
        self.modal = None
        self.manager_tab = 'overview'
        self.history_page = 0
        self.init_management()
        self.running = True
        self.auto_save = 0
        self.animation = 0
        self.load_error = ''
        self.has_save = self.persistent and save_path().exists()
        if not self.has_save:self.modal='welcome'
        self.last_warning = ''
        self.scale = 1
        self.offset = (0, 0)
        self.update_size()
        if self.has_save:
            try:
                self.world = World.load(save_path())
            except (OSError, ValueError, KeyError, TypeError):
                self.last_warning = 'Không đọc được bản lưu VND; hãy sao lưu tệp trước khi tạo ván mới.'

    def poll_updates(self):
        if self.update_queue is not None:
            from queue import Empty
            try:
                self.available_update=self.update_queue.get_nowait()
                self.update_queue=None
            except Empty:pass
        if self.available_update and not self.update_notified and self.modal is None and not self.drag:
            self.modal='update'
            self.update_notified=True

    def font(self, size=22, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pg.font.SysFont('segoeui,arial,dejavusans', size, bold=bold)
        return self.fonts[key]

    def text(self, value, xy, size=22, color=INK, bold=False, center=False):
        surface = self.font(size, bold).render(str(value), True, color)
        rect = surface.get_rect(center=xy) if center else surface.get_rect(topleft=xy)
        self.canvas.blit(surface, rect)
        return rect

    def wrap(self, value, xy, width, size=21, color=INK, bold=False, line_gap=5):
        x, y = xy
        for para in str(value).split('\n'):
            line = ''
            for word in para.split():
                test = line + (' ' if line else '') + word
                if self.font(size, bold).size(test)[0] > width and line:
                    self.text(line, (x, y), size, color, bold)
                    y += size + line_gap
                    line = word
                else:
                    line = test
            self.text(line, (x, y), size, color, bold)
            y += size + line_gap
        return y

    def box(self, rect, color, radius=10, border=None, width=2):
        pg.draw.rect(self.canvas, color, rect, border_radius=radius)
        if border:
            pg.draw.rect(self.canvas, border, rect, width, border_radius=radius)

    def button(self, rect, label, action, enabled=True, color=GREEN, small=False):
        rect = pg.Rect(rect)
        hover = rect.collidepoint(self.mouse)
        base = color if enabled else '#a7aa9c'
        if hover and enabled:
            base = pg.Color(base).lerp(pg.Color('white'), .15)
        self.box(rect, base, 9)
        size = 19 if small else 22
        while self.font(size, True).size(label)[0] > rect.width - 16 and size > 14:
            size -= 1
        self.text(label, rect.center, size, 'white', True, center=True)
        if enabled:
            self.buttons.append((rect, action))

    def update_size(self):
        dw, dh = self.display.get_size()
        self.scale = min(dw / W, dh / H)
        self.offset = ((dw - W * self.scale) / 2, (dh - H * self.scale) / 2)

    def point(self, point):
        return ((point[0] - self.offset[0]) / self.scale, (point[1] - self.offset[1]) / self.scale)

    def person(self, x, y, color, step=0, scale=1):
        x, y = int(x), int(y)
        def ell(c, r):
            pg.draw.ellipse(self.canvas, c, r)
        ell('#536853', (x-14*scale, y+8*scale, 30*scale, 13*scale))
        swing = math.sin(step) * 4 * scale
        ell('#343b3d', (x-10*scale, y+5*scale+swing, 8*scale, 15*scale))
        ell('#343b3d', (x+2*scale, y+5*scale-swing, 8*scale, 15*scale))
        ell(color, (x-14*scale, y-8*scale, 28*scale, 24*scale))
        pg.draw.circle(self.canvas, '#452f27', (x, int(y-12*scale)), int(12*scale))
        ell('#ebbd91', (x-9*scale, y-16*scale, 18*scale, 14*scale))
        ell('#452f27', (x-10*scale, y-23*scale, 20*scale, 10*scale))

    def bowl(self, xy, toppings=(), mushy=False, size=30, dirty=False):
        x, y = map(int, xy)
        pg.draw.ellipse(self.canvas, '#77654d', (x-size-2, y-size*.7+5, size*2+4, size*1.4))
        pg.draw.ellipse(self.canvas, '#faf7e9', (x-size, y-size*.7, size*2, size*1.4))
        pg.draw.ellipse(self.canvas, '#aa8560' if dirty else '#c68e43', (x-size+6, y-size*.7+5, size*2-12, size*1.4-10))
        if dirty:
            for dx, dy in [(-8, 0), (4, 3), (10, -4)]:
                pg.draw.circle(self.canvas, '#527445', (x+dx, y+dy), 3)
            return
        for i in range(5):
            pg.draw.arc(self.canvas, '#d9c499' if mushy else '#f3da8c',
                        (x-size+10+i*3, y-10+i*2, size+5, 13), .1, 5.6, 2)
        for i, name in enumerate(toppings):
            dx = [-12, 9, -2, 13, -7, 2][i % 6]
            dy = [-5, 3, 8, -6, 2, -10][i % 6]
            if name == 'Nước dùng':
                continue
            if name == 'Trứng':
                pg.draw.ellipse(self.canvas, '#fff8df', (x+dx-6, y+dy-4, 14, 10))
                pg.draw.circle(self.canvas, '#e6ac35', (x+dx, y+dy), 3)
            elif name == 'Hành':
                for j in range(5):
                    pg.draw.circle(self.canvas, '#5c9d4e', (x+dx+j*3-6, y+dy+(j%2)*4), 2)
            else:
                pg.draw.ellipse(self.canvas, TOPPING_COLOR[name], (x+dx-7, y+dy-3, 16, 8))
        if mushy:
            pg.draw.circle(self.canvas, RED, (x+size-2, y-12), 5)

    def render_floor(self):
        self.canvas.fill('#dce5d0')
        self.box((0, 0, W, 87), '#233d32', 0)
        self.text(GAME_TITLE, (28, 15), 31, CREAM, True)
        self.text('TỰ TAY VẬN HÀNH', (30, 56), 16, '#bcd0b1')
        world = self.world
        now = world.now
        self.text(f'{now:%d/%m/%Y  %H:%M:%S}', (350, 15), 25, CREAM, True)
        self.text(WEEKDAYS[now.weekday()] + ' · VN UTC+7' + (' · Cao điểm' if world.peak else ''), (350, 52), 17, '#c4d6ba')
        self.text(vnd(world.cash), (720, 15), 23, GOLD, True)
        self.text(f'Bát sạch: {world.clean} / {world.dishes_owned}', (722, 54), 19, '#c4d6ba')
        self.text(f'Danh tiếng {world.reputation:.2f}%', (1000, 21), 25, CREAM, True)
        self.button((1386, 18, 185, 49), 'Đóng quán', ('close',), small=True, color=RED)
        # Street and sidewalk.
        self.box((0, 97, 1177, 48), '#6c7876', 0)
        for x in range(8, 1177, 95):
            self.box((x, 117, 52, 5), '#dadac8', 0)
        self.box((0, 145, 1177, 111), '#c7c9b6', 0)
        for x in range(0, 1177, 54):
            pg.draw.line(self.canvas, '#b8bbaa', (x, 145), (x, 252))
        for y in [173, 205, 237]:
            pg.draw.line(self.canvas, '#b8bbaa', (0, y), (1177, y))
        for x in (50, 1110):
            self.box((x-22, 165, 45, 32), '#966b46', 4)
            for dx, dy in [(-15, -10), (8, -20), (0, -2)]:
                pg.draw.circle(self.canvas, '#608250', (x+dx, 158+dy), 21)
                pg.draw.circle(self.canvas, '#7a965d', (x+dx-6, 155+dy), 13)
        # Interior floor with wood boards.
        self.box((22, 259, 1155, 677), '#8a5b3c', 12)
        self.box((35, 270, 1130, 654), '#d6b980', 4)
        for y in range(276, 925, 42):
            pg.draw.line(self.canvas, '#bea070', (36, y), (1164, y), 2)
            for x in range(40 + ((y//42)%2)*100, 1165, 210):
                pg.draw.line(self.canvas, '#bea070', (x, y), (x, y+41), 1)
        self.box((775, 273, 380, 647), '#bcc2af', 4)
        for x in range(780, 1155, 45):
            pg.draw.line(self.canvas, '#a8b4a5', (x, 275), (x, 920))
        for y in range(280, 920, 45):
            pg.draw.line(self.canvas, '#a8b4a5', (778, y), (1155, y))
        self.box((30, 251, 190, 27), '#705036', 3)
        self.box((354, 251, 820, 27), '#705036', 3)
        self.box((222, 251, 131, 11), '#c45643', 0)
        # Floor navigation remains clear of the first row of diners.
        self.text(f'TẦNG {self.floor+1} · KHU BÀN ĂN', (63, 329), 21, '#67492e', True)
        for floor in range(world.floors):
            self.button((63+floor*173,290,160,34),f'Tầng {floor+1} [phím {floor+1}]',('floor',floor),small=True,color=GREEN if floor==self.floor else '#92734c')
        self.text('Đang kéo: phím 1 / 2 / 3 để đổi tầng', (63,364),16)

        self.text('BẾP 6 NỒI', (844, 253), 20, CREAM, True)
        for spot in world.dirt:
            if spot // len(DIRT_POS) != self.floor: continue
            x, y = DIRT_POS[spot % len(DIRT_POS)]
            for dx, dy in [(-12, 2), (3, -4), (12, 5)]:
                pg.draw.ellipse(self.canvas, '#907049', (x+dx-8, y+dy-5, 19, 12))
            self.box((x-24, y+12, 48, 23), '#8e553f', 4)
            self.text('LAU', (x, y+24), 14, 'white', True, True)
        # Ticket machine.
        self.box(MACHINE.move(5, 5), '#6c624e', 8)
        self.box(MACHINE, '#345854', 8, '#203d35')
        self.box((631, 298, 73, 34), '#d9e6b4', 4)
        self.text('MUA PHIẾU', (667, 312), 13, INK, True, True)
        for i, color in enumerate(['#e5c679', '#ce9672', '#e5c679']):
            self.box((630+i*26, 339, 19, 17), color, 3)
        self.box((641, 366, 49, 9), '#172c29', 2)
        self.text('Máy bán vé', (612, 395), 18, INK, True)
        # Sink.
        self.box(SINK, '#687f7b', 8)
        self.box((809, 292, 139, 43), '#314e50', 8, '#bccdc6')
        for i in range(min(world.sink, 5)):
            self.bowl((833+i*19, 314), dirty=True, size=13)
        self.text(f'Bồn: {world.sink} bát', (815, 323), 16, 'white')
        self.button((970, 292, 165, 43), f'Đang rửa {max(0,math.ceil(world.wash_left))}s' if world.washing else 'Rửa bát',
                    ('wash',), not world.washing and world.sink > 0, small=True)
        # Pots: exact remaining seconds.
        for i, (x, y) in enumerate(POT_POS):
            state = world.pot_state(i)
            lifted = next((b for b in world.bowls if b.stage == 'lifted' and b.slot == i), None)
            self.box((x-51, y-40, 102, 86), '#7b8980', 6)
            pg.draw.circle(self.canvas, '#364641', (x, y), 34)
            pg.draw.circle(self.canvas, '#b9cbc7', (x, y-4), 29)
            pg.draw.circle(self.canvas, '#698e97' if state == 'empty' else '#b4bf94', (x, y-4), 23)
            pg.draw.line(self.canvas, '#354a42', (x-44, y-2), (x-29, y-2), 7)
            pg.draw.line(self.canvas, '#354a42', (x+29, y-2), (x+44, y-2), 7)
            if state != 'empty':
                for j in range(5):
                    pg.draw.arc(self.canvas, '#eed59c', (x-19+j*3, y-18+j*3, 23, 15), .3, 5.3, 2)
                for j in range(3):
                    sy = y-27-((self.animation*20+j*13)%28)
                    pg.draw.circle(self.canvas, '#e7ede0', (x-13+j*12, int(sy)), 3)
            if state == 'empty':
                label, col = f'{i+1} · Trống', '#344b41'
            elif state == 'cooking':
                left = max(0, math.ceil(COOK_SECONDS-world.pots[i]))
                label, col = f'{left//60}:{left%60:02}', INK
            elif state == 'ready':
                left = max(0, math.ceil(COOK_SECONDS+LIFT_WINDOW-world.pots[i]))
                label, col = f'VỚT! {left}s', GREEN
                pg.draw.circle(self.canvas, '#6ab464', (x, y-4), 34, 4)
            else:
                label, col = 'NHÃO', RED
                pg.draw.circle(self.canvas, RED, (x, y-4), 34, 4)
            self.text(label, (x, y+33), 17, col, True, True)
            if lifted and self.drag != ('bowl', lifted.id):
                self.box((x-49, y-39, 98, 85), '#bfa67f', 6)
                self.bowl((x, y-5), mushy=lifted.mushy)
                self.text('Kéo xuống', (x, y+22), 15, INK, True, True)
                self.text('quầy topping', (x, y+39), 13, INK, False, True)
        # Ingredient bin and waste.
        self.box(RAW, '#eadbb8', 8, '#887551')
        for i in range(7):
            pg.draw.line(self.canvas, '#c8a661', (808+i*6, 574), (811+i*6, 601), 3)
        self.text('MÌ TƯƠI', (865, 565), 19, INK, True)
        self.text(f'{world.stock["Mì tươi"]} phần · kéo', (865, 591), 16)
        self.box(TRASH, '#686958', 8)
        self.text('THÙNG RÁC', TRASH.center, 18, 'white', True, True)
        self.text('Nhấp phải nồi để đổ bỏ mì', (800, 622), 16, '#405649')
        # Toppings.
        for name, rect in TOPPING_RECTS.items():
            self.box(rect, '#8b795b', 5)
            self.box(rect.inflate(-8, -22).move(0, -5), TOPPING_COLOR[name], 5)
            short = 'Dùng' if name == 'Nước dùng' else name
            self.text(short, (rect.centerx, rect.y+18), 17, 'white', True, True)
            self.text(str(world.stock[name]), (rect.centerx, rect.bottom-12), 16, 'white', True, True)
        self.text('Kéo topping xuống bát · kéo bát ra bàn', (795, 723), 17, '#405649')
        for i, (x, y) in enumerate(BOWL_POS):
            self.box((x-49, y-30, 98, 76), '#a58b64', 6, '#86704d')
            pg.draw.ellipse(self.canvas, '#bba37c', (x-31, y-18, 62, 37), 2)
            b = next((b for b in world.bowls if b.slot == i and b.stage == 'prep'), None)
            if b and self.drag != ('bowl', b.id):
                self.bowl((x, y), b.toppings, b.mushy)
                self.text(f'Bát {b.id} · {len(b.toppings)} vị', (x, y+32), 15, INK, True, True)
        # Shared tables; each group retains its own seats, ticket and meals.
        for i, table in enumerate(world.tables):
            if table.floor != self.floor: continue
            x,y=world.table_position(i)
            chairs=self.chairs(i)
            for cx,cy in chairs:
                self.box((cx-22,cy-22,44,44),'#755235',7)
                self.box((cx-17,cy-17,34,32),'#52765a',5)
            self.box((x-92,y-50,184,96),'#edce8e',10,'#a27b47',4)
            label=f'B{i+1} · {table.dirty} bát bẩn' if table.dirty else (f'B{i+1} · LAU BÀN' if table.needs_wipe else f'B{i+1} · {len(world.free_seats(i))}/{table.capacity} trống')
            if world.wipe_table==i:label=f'B{i+1} · Lau {math.ceil(world.wipe_left)}s'
            self.text(label,(x,y-32),14,RED if table.dirty or table.needs_wipe else INK,True,True)
            groups=world.at_table(i)
            if groups:
                for n,party in enumerate(groups):
                    rect=self.table_group_rect(i,n)
                    self.box(rect,'#f5c56b' if self.selected==party.id else '#fff4d8',4)
                    self.text(f'N{party.id:03} {len(party.meals)}/{party.size}',rect.center,13,INK,True,True)
            elif not table.dirty and not table.needs_wipe:
                self.text('Bàn sạch' if table.capacity else 'Chưa có ghế',(x,y),19,GREEN,True,True)
            if table.dirty and not groups:
                self.bowl((x,y+8),dirty=True,size=24)
        # Living customers and passers-by.
        for w in world.walkers:
            for j in range(w['size']):
                self.person(w['x']+j*29, w['y']+(j%2)*7, PEOPLE[(w['color']+j)%6], self.animation*8+j)
        for p in world.parties:
            if self.drag == ('party', p.id):
                continue
            if p.phase in ('seated', 'eating'):
                if world.tables[p.table].floor != self.floor: continue
                for j,seat in enumerate(p.seats):
                    cx,cy=self.chairs(p.table)[seat]
                    self.person(cx,cy,PEOPLE[(p.id+j)%6])
                    if j < len(p.meals):
                        tx,ty=world.table_position(p.table)
                        meal=p.meals[j]
                        self.bowl((cx+(25 if cx<tx else -25),cy+(14 if cy<ty else -14)),meal['toppings'],meal['mushy'],12)
                        left=math.ceil(meal['eat_left'])
                        self.text(f'{left//60}:{left%60:02}' if left else 'Ăn xong',(cx,cy-36 if cy<ty else cy+32),13,GREEN,True,True)

            else:
                for j in range(p.size):
                    self.person(p.x+(j-(p.size-1)/2)*24, p.y+(j%2)*5, PEOPLE[(p.id+j)%6], self.animation*7+j)
                status = {'door':'hỏi chỗ', 'waiting':'đợi bàn', 'queue':'đợi mua vé', 'buying':'mua phiếu',
                          'ticket':'nhận phiếu!', 'ready':'kéo vào bàn', 'leaving':'tạm biệt'}[p.phase]
                if p.phase=='buying':status=f'Chọn món / trả tiền {math.ceil(max(0,p.buy_seconds-p.phase_time))}s'
                elif p.phase in ('door','waiting','queue'):
                    patience={'door':p.door_patience,'waiting':p.wait_patience,'queue':p.queue_patience}[p.phase]
                    status+=f' · {math.ceil(max(0,min(patience)-p.phase_time))}s'
                elif p.phase=='ticket':status='Đã trả tiền · nhận phiếu'
                elif p.phase=='ready':status='Đã trả tiền · xếp bàn'
                self.label_party(p, p.x, p.y-48, status)
        p = next((p for p in world.parties if p.phase == 'ticket'), None)
        if p:
            self.box(TICKET, '#fff5b2', 3, '#c08c32')
            for i in range(5):
                pg.draw.line(self.canvas, '#8e7b46', (TICKET.x+8, TICKET.y+14+i*8), (TICKET.right-8, TICKET.y+14+i*8))
            self.text('NHẬN', (TICKET.centerx, TICKET.y-13), 15, RED, True, True)
        self.box((29, 950, 1140, 37), '#334e3d', 8)
        message = world.logs[-1] if world.logs else ''
        for spot in world.dirt:
            if spot//len(DIRT_POS)==self.floor and dist(self.mouse,DIRT_POS[spot%len(DIRT_POS)])<40:
                message=world.dirt_reasons.get(str(spot),'Vết bẩn từ phiên bản trước')+' · Nhấp LAU để dọn'
        size = 20 if self.font(20).size(message)[0] < 1112 else 17
        self.text(message, (42, 956), size, CREAM)

    def chairs(self, index):
        x,y=self.world.table_position(index)
        return [(x-53,y-65),(x+53,y-65),(x-53,y+65),(x+53,y+65)][:self.world.tables[index].capacity]

    def table_group_rect(self,index,number):
        x,y=self.world.table_position(index)
        return pg.Rect(x-87+(number%2)*89,y-12+(number//2)*27,85,24)

    def label_party(self, p, x, y, status):
        rect = pg.Rect(x-88, y-18, 176, 41)
        self.box(rect, '#fff4d8' if p.id != self.selected else '#f5c56b', 6, '#9f8b66')
        self.text(f'Nhóm {p.id:03} · {p.size} người', (x, y-7), 15, INK, True, True)
        self.text(status, (x, y+11), 14, '#725538', False, True)

    def render_side(self):
        w = self.world
        self.box((1189, 105, 389, 881), '#fff3d9', 14, '#b7b793')
        self.text('KHÁCH & PHIẾU ĂN', (1207, 120), 25, INK, True)
        self.text(f'Tỷ lệ ghé quán: {w.chance:.2f}%', (1208, 165), 23, GREEN, True)
        self.text(f'Danh tiếng {w.reputation:.2f}% {w.bonus:+d} điểm %', (1208, 196), 18, '#6b705b')
        self.text((w.holiday or w.kind)[:43], (1208, 222), 16, '#6b705b')
        waiting = [p for p in w.parties if p.phase in ('door', 'waiting')]
        selected = w.group(self.selected)
        door = selected if selected and selected.phase in ('door','waiting') else (waiting[0] if waiting else None)
        self.box((1203, 262, 361, 236), '#e9dfbd', 9)
        if door:
            self.text(f'Nhóm {door.id:03} · {door.size} người', (1216, 274), 23, INK, True)
            self.text('"Quán còn chỗ cho chúng tôi không?"', (1216, 311), 17)
            self.button((1215, 342, 337, 42), 'Còn chỗ, mời khách vào', ('answer',door.id,'accept'), small=True)
            self.button((1215, 389, 337, 42), 'Hết chỗ, khách có thể đợi không?', ('answer',door.id,'wait'), small=True, color='#97713b')
            self.button((1215, 436, 337, 44), 'Hết nguyên liệu, hẹn lần sau', ('answer',door.id,'decline'), small=True, color=RED)
        else:
            self.wrap('Chưa có khách hỏi chỗ. Bạn có thể chuẩn bị mì trước.', (1220, 282), 319, 23)
            self.wrap('Nhấp tên nhóm bất kỳ để xem phiếu hoặc trả lời khách đang đợi.', (1220, 381), 319, 20, '#687259')
        self.text('PHIẾU ĐANG XEM', (1208, 516), 22, INK, True)
        if selected and selected.ticket_read:
            p = selected
            self.text(f'Nhóm {p.id:03} · ' + (f'T{w.tables[p.table].floor+1} Bàn {p.table+1}' if p.table >= 0 else 'Chưa xếp bàn'), (1208, 550), 23, GREEN, True)
            y = 590
            for i, order in enumerate(p.orders):
                done = i < len(p.meals)
                self.text(f'{i+1}. {order}' + (' ✓' if done else ''), (1208, y), 16, '#7a806c' if done else INK, True)
                y += 25
                self.text(' · '.join((name.replace('Nước dùng','Dùng') + '×' + str(p.recipes[i].count(name))) for name in dict.fromkeys(p.recipes[i])), (1210, y), 13, '#736b55')
                y += 31
        elif selected:
            self.wrap(f'Nhóm {selected.id:03} chưa giao phiếu. Chờ khách mua ở máy rồi nhấp phiếu màu vàng.', (1208, 551), 340, 22)
        else:
            self.wrap('Nhấp nhóm hoặc bàn để xem đúng món của từng người. Giao bát theo thứ tự 1, 2, 3, 4 trên phiếu.', (1208, 551), 340, 22)
        self.text(f'Sàn: {len(w.dirt)} chỗ bẩn', (1207, 837), 19, RED if w.dirt else GREEN, True)
        self.button((1384, 825, 175, 45), 'Đánh giá', ('modal','reviews'), small=True, color='#836647')
        self.button((1207, 879, 352, 45), 'Dọn xong · xác nhận đóng' if w.closing else 'Đóng quán / kết thúc ca', ('close',), small=True, color='#785b42')
        self.button((1207, 936, 169, 35), 'F1 · Cách chơi', ('modal','help'), small=True, color='#687357')
        self.text('Đang dọn cuối ca' if w.closing else 'Quán đang mở', (1384, 945), 16, GREEN, True)

    def render_closed(self):
        w = self.world
        self.canvas.fill('#e6e9da')
        self.box((0, 0, W, 135), '#233d32', 0)
        self.text(GAME_TITLE+' · QUẢN LÝ', (45, 25), 35, CREAM, True)
        self.text('ĐANG ĐÓNG CỬA', (47, 83), 21, GOLD, True)
        self.text(f'{w.now:%d/%m/%Y  %H:%M:%S} · Việt Nam', (1025, 34), 23, CREAM)
        self.text(WEEKDAYS[w.now.weekday()] + ' · ' + (w.holiday or w.kind), (1025, 80), 18, '#c4d6ba')
        self.box((35, 155, 960, 128), '#fff3d9', 12)
        self.text('NGÂN SÁCH HIỆN TẠI', (57, 172), 18, '#6b7357', True)
        self.text(vnd(w.cash), (55, 207), 40, INK, True)
        self.text(f'Danh tiếng {w.reputation:.2f}%', (650, 214), 26, GREEN, True)
        self.button((1030, 173, 260, 82), 'MỞ QUÁN', ('open',))
        self.button((1305, 173, 253, 82), 'Lưu và thoát' if self.persistent else 'Chơi lại từ đầu', ('quit',) if self.persistent else ('modal','confirm_new'), color='#7c674b')
        tabs = [('overview','Tổng quan'), ('inventory','Kho nguyên liệu'), ('market','Chợ'),
                ('expansion','Bàn / tầng'), ('supplier','Nhà cung cấp'), ('menu','Tạo menu'),
                ('day','Theo ngày'), ('month','Theo tháng'), ('year','Theo năm')]
        for i, (key, label) in enumerate(tabs):
            self.button((36+i*170, 305, 161, 52), label, ('tab',key),
                        color=GREEN if self.manager_tab==key else '#7c876d')
        self.box((35, 380, 1525, 520), '#fff3d9', 12)
        if self.manager_tab=='expansion':
            self.render_expansion()
        elif self.manager_tab=='supplier':
            self.render_supplier()
        elif self.manager_tab=='menu':
            self.render_menu()
        elif self.manager_tab in ('inventory','market'):
            market = self.manager_tab=='market'
            self.text('CHỢ · CHỈ MUA KHI ĐÓNG QUÁN' if market else 'KHO NGUYÊN LIỆU TỒN', (60, 398), 25, INK, True)
            for i, name in enumerate(['Bát/đĩa', *STOCK_COST]):
                y = 448+i*61
                count = w.clean if name=='Bát/đĩa' else w.stock[name]
                cost = DISH_COST if name=='Bát/đĩa' else STOCK_COST[name]
                self.text(name, (62, y+8), 23, INK, True)
                self.text(f'Tồn: {count}', (285, y+9), 22, GREEN)
                self.text(vnd(cost) + '/cái' if name=='Bát/đĩa' else vnd(cost)+'/phần', (440, y+10), 19)
                if market:
                    for j, amount in enumerate([1,10,50]):
                        self.button((755+j*252,y,240,44), f'Mua {amount} · {vnd(cost*amount)}',
                                    ('buy',name,amount), w.cash>=cost*amount, small=True)
            if not market:
                self.wrap('Bát/đĩa là dụng cụ dùng lại sau khi rửa. Nguyên liệu tồn chưa sử dụng không bị tính vào giá vốn hôm nay.',
                          (880, 475), 580, 25, '#687259')
                self.button((885, 650, 450, 57), 'Đến chợ mua hàng', ('tab','market'))
        elif self.manager_tab in ('day','month','year'):
            rows = sorted(w.totals(self.manager_tab).items(), reverse=True)
            self.text('LỊCH SỬ KINH DOANH · VND', (60, 398), 25, INK, True)
            for text, x in [('Kỳ',60),('Doanh thu',310),('Nguyên liệu đã dùng',590),('Điện + nước + ga',925),('Lợi nhuận',1270)]:
                self.text(text, (x,455), 20, GREEN, True)
            start = self.history_page*7
            for i,(key,row) in enumerate(rows[start:start+7]):
                y=501+i*43
                values=[key,vnd(row['revenue']),vnd(row['ingredients']),vnd(row['utilities']),vnd(row['profit'])]
                for value,x in zip(values,[60,310,590,925,1270]):
                    self.text(value,(x,y),20, RED if x==1270 and row['profit']<0 else INK)
            if not rows:
                self.text('Chưa có giao dịch. Mua nguyên liệu ở Chợ để bắt đầu.',(62, 532),24)
            self.text('Giá vốn gồm phần đã nấu / thêm topping, kể cả phần đổ bỏ. Không trừ lại tiền mua kho.',(60,851),18,'#6b7357')
            self.button((1210,834,145,43),'Trước',('page',-1),self.history_page>0,small=True)
            self.button((1380,834,145,43),'Sau',('page',1),start+7<len(rows),small=True)
        else:
            today=w.totals().get(w.now.date().isoformat(),{})
            self.text('HÔM NAY', (60,410),28,INK,True)
            y=470
            for label, key in [('Doanh thu','revenue'),('Nguyên liệu đã sử dụng','ingredients'),('Điện, nước, ga','utilities'),('Lợi nhuận','profit')]:
                self.text(label,(60,y),24)
                self.text(vnd(today.get(key,0)),(480,y),24,GREEN,True)
                y+=67
            self.wrap('Chuẩn bị trước khi mở quán', (880, 415),570,28,INK,True)
            self.wrap('Mua bát/đĩa và nguyên liệu ở Chợ. Khi mở quán, bạn phải tự vận hành và không thể mua thêm hàng.',(880,470),585,25)
            self.wrap('Kết ca: bấm Đóng quán để ngừng nhận nhóm mới, phục vụ hết khách, xử lý hết mì, rửa bát và lau bàn/sàn. Bấm xác nhận đóng để nhận tổng kết.',(880,605),585,23)
            self.text(f'Tiền mua kho hôm nay: {vnd(today.get("purchases",0))}',(60,779),20)
            self.text(f'Tiền mua dụng cụ: {vnd(today.get("equipment",0))}',(60,815),20)
            self.button((950,803,265,46),'Cách chơi',('modal','help'),small=True)
            self.button((1230,803,265,46),'Tạo ván mới',('modal','confirm_new'),small=True,color='#98734c')
        self.box((35,924,1525,52),'#334e3d',8)
        self.text(w.logs[-1] if w.logs else '',(51,938),20,CREAM)

    def render_modal(self):
        if not self.modal:
            return
        shade=pg.Surface((W,H),pg.SRCALPHA); shade.fill((10,28,23,190)); self.canvas.blit(shade,(0,0))
        self.buttons=[]
        self.box((260,110,1080,785),'#fff0d1',20,'#bfa36b',3)
        if self.modal=='welcome':
            self.text(GAME_TITLE,(800,185),43,INK,True,True)
            self.text('CHÀO MỪNG CHỦ QUÁN MỚI',(800,253),28,GREEN,True,True)
            lines=[
                'Bạn bắt đầu với 10.000.000 VND và danh tiếng 7%.',
                'Quán có 1 tầng, 1 bàn và 4 ghế. Kho nguyên liệu và bát đĩa đang trống.',
                'Vào Chợ mua bát, mì và topping trước khi mở quán.',
                'Tự đón khách, nhận phiếu, nấu mì, phục vụ và dọn sạch khi kết ca.',
                'Tiến trình được lưu riêng trên tài khoản Windows của bạn.' if self.persistent else 'Bản web không lưu. Đóng tab hoặc tải lại trang sẽ chơi từ đầu.',
                'Giờ và ngày lễ theo Việt Nam. Không có chế độ tạm dừng.',
            ]
            y=329
            for line in lines:y=self.wrap(line,(325,y),945,24)+24
            self.button((535,760,530,68),'Bắt đầu quản lý quán',('begin',))
        elif self.modal=='update':
            info=self.available_update
            self.text('ĐÃ CÓ PHIÊN BẢN MỚI',(800,195),36,INK,True,True)
            self.text(GAME_TITLE,(800,258),29,GREEN,True,True)
            self.text('Đang dùng '+GAME_VERSION+'   ·   Bản mới '+info['version'],(320,328),25,INK,True)
            self.wrap(info['notes'],(320,392),950,23)
            self.wrap('Tải bản mới từ GitHub Releases. Tiến trình trên máy được giữ lại.',(320,653),950,22)
            if self.world.open:self.text('Quán vẫn hoạt động khi thông báo này đang mở.',(320,707),20,RED)
            self.button((330,790,440,61),'Tải bản mới',('download_update',))
            self.button((830,790,440,61),'Để sau',('dismiss',),color='#8a7352')
        elif self.modal=='report':
            row=self.world.last_report
            self.text('TỔNG KẾT KINH DOANH HÔM NAY',(310,149),34,INK,True)
            self.text(row['date']+' · Đã đóng quán',(310,207),24,GREEN,True)
            y=262
            for label,key in [('Doanh thu bán phiếu','revenue'),('Giá vốn nguyên liệu đã dùng / hỏng','ingredients'),
                              ('Điện','electricity'),('Nước','water'),('Ga','gas'),('LỢI NHUẬN','profit')]:
                self.text(label,(312,y),24,INK,key=='profit')
                self.text(vnd(row[key]),(995,y),25,GREEN if row[key]>=0 else RED,True)
                y+=57
            self.text('Ngân sách còn lại: '+vnd(row['cash']),(310,625),27,GREEN,True)
            self.wrap('Tiền nhập kho đã trừ khi mua; giá vốn không bị trừ lần nữa. Điện/nước/ga thanh toán lần này: '+vnd(row['payment']), (312,677),960,20)
            self.button((855,811,420,55),'Về trang đóng quán',('dismiss',))
        elif self.modal=='confirm_new':
            self.text('TẠO VÁN VND MỚI?',(800,280),36,INK,True,True)
            self.wrap('Thay tiến trình VND hiện tại bằng 10.000.000 VND, danh tiếng 7%, không có nguyên liệu hoặc bát.',(440,365),730,25)
            self.button((440,540,340,63),'Tạo ván mới',('new',))
            self.button((825,540,340,63),'Quay lại',('dismiss',),color='#8a7352')
        elif self.modal=='reviews':
            self.text('ĐÁNH GIÁ CỦA KHÁCH',(310,155),32,INK,True)
            y=225
            for line in self.world.reviews[-9:] or ['Chưa có đánh giá.']:
                y=self.wrap(line,(310,y),970,20)+10
            self.button((950,817,330,49),'Trở lại quán',('dismiss',))
        else:
            self.text('CÁCH CHƠI · QUÁN KHÔNG TẠM DỪNG',(308,152),30,INK,True)
            lines=[
                '1. Khi đóng quán: mua bát, mì và topping tại Chợ rồi bấm Mở quán.',
                '2. Nhận phiếu, kéo nhóm vào bàn đủ ghế trống. Có thể ghép nhiều nhóm.',
                '3. Kéo mì vào 6 nồi. Luộc 210 giây, vớt trong 10 giây, quá giờ sẽ nhão.',
                '4. Thêm topping. Bàn ghép: nhấp N001/N002 chọn nhóm rồi kéo bát ra bàn.',
                '5. Khách ăn 5–20 phút. Dọn bát vào bồn, nhấp rửa (20–40s/bát + 15s), lau bàn 20–45s.',
                '6. Bấm Đóng quán: ngừng đón nhóm mới nhưng khách và bếp vẫn hoạt động.',
                '7. Dọn sạch, xử lý hết khách và mì rồi xác nhận đóng để xem lợi nhuận.',
                'Giờ và lịch theo Việt Nam. Cao điểm: 11–14h, 17–20h. Cuối tuần: thứ Sáu–CN.',
                'Tỷ lệ: ngày thường -5/0; cuối tuần 0/+5; ngày lễ +5/+10 điểm phần trăm.',
                'Giá giả lập: điện 6.000 VND/giờ; ga 800 VND/nồi; nước 200 VND/bát rửa.',
                'Lau sàn dùng nước 500 VND/vết. Tiền mua bát ghi riêng là mua dụng cụ.',
                'Không có tạm dừng: khách và nồi vẫn chạy khi xem bảng hoặc chuyển cửa sổ.',
                'Phím 1/2/3 đổi tầng cả khi đang kéo. Quản lý bàn/tầng, nhà cung cấp và menu khi đóng quán.',
            ]
            y=219
            for line in lines:y=self.wrap(line,(310,y),970,20)+11
            self.button((950,819,330,49),'Trở lại',('dismiss',))

    def draw(self):
        self.buttons = []
        if self.world.open:
            self.render_floor()
            self.render_side()
        else:
            self.render_closed()
        if self.drag:
            kind, ident = self.drag
            x, y = self.mouse
            if kind == 'bowl':
                b = next((b for b in self.world.bowls if b.id == ident), None)
                if b:
                    self.bowl((x,y), b.toppings, b.mushy, 35)
            elif kind == 'dirty':
                self.bowl((x,y), dirty=True, size=32)
            elif kind == 'party':
                p = self.world.group(ident)
                for j in range(p.size):
                    self.person(x+(j-(p.size-1)/2)*25, y, PEOPLE[(p.id+j)%6])
                self.label_party(p, x, y-55, 'thả vào bàn')
            elif kind == 'raw':
                self.box((x-27,y-20,54,40), '#e8d399', 5)
                for j in range(7):
                    pg.draw.line(self.canvas, '#b99b64', (x-18+j*5,y-14),(x-18+j*5,y+14),2)
            else:
                pg.draw.circle(self.canvas, TOPPING_COLOR[ident], (int(x),int(y)), 18)
                self.text(ident, (x,y-32), 18, INK, True, True)
        self.render_modal()
        if self.last_warning:
            self.box((280, 897, 1040, 43), RED, 6)
            self.text(self.last_warning, (300, 906), 18, 'white')
        self.text(f'Phiên bản {GAME_VERSION} · Nhà phát hành {PUBLISHER}',
                  (W//2,989),14,'#aeb8a8' if self.modal else '#596b56',center=True)
        self.update_size()
        scaled = pg.transform.smoothscale(self.canvas, (int(W*self.scale),int(H*self.scale)))
        self.display.fill('#18291e')
        self.display.blit(scaled, self.offset)
        pg.display.flip()

    def hit_table(self, point):
        for i,t in enumerate(self.world.tables):
            if t.floor != self.floor: continue
            x,y=self.world.table_position(i)
            if pg.Rect(x-100,y-58,200,116).collidepoint(point):return i
        return None

    def hit_party(self, point):
        for i,t in enumerate(self.world.tables):
            if t.floor!=self.floor:continue
            for n,p in enumerate(self.world.at_table(i)):
                if self.table_group_rect(i,n).collidepoint(point):return p
                if any(dist(point,self.chairs(i)[seat])<26 for seat in p.seats):return p
        for p in reversed(self.world.parties):
            if p.phase in ('seated','eating'):continue
            if pg.Rect(p.x-81,p.y-68,162,103).collidepoint(point):return p
        return None

    def source(self, point):
        p = self.hit_party(point)
        if p:
            self.selected = p.id
            if p.phase == 'ready':
                return ('party',p.id)
        if RAW.collidepoint(point):
            return ('raw',0)
        for name, rect in TOPPING_RECTS.items():
            if rect.collidepoint(point):
                return ('topping',name)
        for b in self.world.bowls:
            position = BOWL_POS[b.slot] if b.stage == 'prep' else POT_POS[b.slot]
            if dist(point, position) < 46:
                return ('bowl',b.id)
        index = self.hit_table(point)
        if index is not None and self.world.tables[index].dirty:
            return ('dirty',index)
        return None

    def click(self, point, right=False):
        if right:
            for i,pos in enumerate(POT_POS):
                if dist(point,pos) < 45:
                    self.world.discard_pot(i)
            return
        for rect, action in reversed(self.buttons):
            if rect.collidepoint(point):
                self.action(action)
                return
        if self.modal or not self.world.open:
            return
        for spot in self.world.dirt[:]:
            if spot // len(DIRT_POS)==self.floor and dist(point,DIRT_POS[spot % len(DIRT_POS)]) < 35:
                self.world.sweep(spot)
                return
        if TICKET.collidepoint(point):
            p = next((p for p in self.world.parties if p.phase == 'ticket'), None)
            if p:
                self.world.collect(p.id)
                self.selected = p.id
                return
        for i,pos in enumerate(POT_POS):
            if dist(point,pos) < 46:
                self.world.lift(i)
                return
        index = self.hit_table(point)
        if index is not None:
            t = self.world.tables[index]
            if not t.dirty and t.needs_wipe:
                self.world.wipe(index)
                return
        p = self.hit_party(point)
        if p:
            self.selected = p.id
            return
        index = self.hit_table(point)
        if index is not None:
            t = self.world.tables[index]
            if t.group:
                self.selected = t.group
            else:
                self.world.wipe(index)

    def drop(self, source, point):
        kind, ident = source
        table = self.hit_table(point)
        if kind == 'party' and table is not None:
            self.world.seat(ident, table)
        elif kind == 'raw':
            for i,pos in enumerate(POT_POS):
                if dist(point,pos) < 53:
                    self.world.start_pot(i)
                    break
        elif kind == 'topping':
            for b in self.world.bowls:
                if b.stage == 'prep' and dist(point,BOWL_POS[b.slot]) < 45:
                    self.world.topping(b.id,ident)
                    break
        elif kind == 'bowl':
            if table is not None:
                groups=self.world.at_table(table)
                gid=self.selected if len(groups)>1 else None
                self.world.serve(ident,table,gid)
            elif TRASH.collidepoint(point):
                self.world.discard_bowl(ident)
            else:
                b = next((b for b in self.world.bowls if b.id==ident),None)
                for i,pos in enumerate(BOWL_POS):
                    if b and dist(point,pos)<43:
                        self.world.move_prep(b.id, i)
                        break
        elif kind == 'dirty' and SINK.collidepoint(point):
            self.world.clear_table(ident)

    def persist(self):
        if not self.persistent:return
        try:
            path = save_path()
            self.world.save(path)
            self.last_warning = ''
        except OSError:
            self.last_warning = 'Không lưu được tiến trình. Kiểm tra quyền ghi trong thư mục tài khoản Windows.'

    def action(self, action):
        kind,*args=action
        if self.extra_action(kind,args):return
        if kind=='tab':
            self.manager_tab=args[0]; self.history_page=0; self.input_focus=None; pg.key.stop_text_input()
        elif kind=='page':
            self.history_page=max(0,self.history_page+args[0])
        elif kind=='modal':
            self.modal=args[0]
        elif kind=='begin':
            self.modal=None; self.manager_tab='overview'; self.persist()
        elif kind=='download_update':
            if self.available_update:
                import webbrowser
                self.persist()
                try:
                    if not webbrowser.open(self.available_update['url']):
                        self.last_warning='Không mở được trình duyệt. Hãy vào GitHub Releases của Quán Mì Của Tôi.'
                except Exception:
                    self.last_warning='Không mở được trình duyệt. Hãy vào GitHub Releases của Quán Mì Của Tôi.'
            self.modal=None
        elif kind=='dismiss':
            self.modal=None
        elif kind=='new' and not self.world.open:
            self.world=World(); self.modal=None; self.manager_tab='overview'; self.init_management(); self.persist()
        elif kind=='open':
            if self.world.open_shop():self.persist()
        elif kind=='answer':
            self.selected=args[0]; self.world.respond(*args)
        elif kind=='wash':
            self.world.wash()
        elif kind=='buy':
            if self.world.restock(args[0],args[1]):self.persist()
        elif kind=='close':
            if self.world.close_shop():
                self.modal='report'; self.manager_tab='overview'; self.persist()
        elif kind=='quit':
            # Exiting the application saves the active shift; it does not close the shop.
            self.persist()
            self.running=False

    def event(self,event):
        if self.management_input(event):return
        if event.type==pg.QUIT:
            self.action(('quit',))
        elif event.type==pg.WINDOWFOCUSLOST:
            self.drag=self.down=None
            self.persist()
        elif event.type==pg.VIDEORESIZE:
            self.display=pg.display.set_mode((max(800,event.w),max(500,event.h)),pg.RESIZABLE)
            self.update_size()
        elif event.type==pg.KEYDOWN:
            if event.key in (pg.K_1,pg.K_2,pg.K_3) and not self.modal:
                floor=event.key-pg.K_1
                if floor<self.world.floors:self.floor=floor
                return
            if event.key==pg.K_F1 and self.modal not in ('report','welcome'):
                self.modal=None if self.modal=='help' else 'help'
            elif event.key==pg.K_ESCAPE and self.modal not in ('report','welcome'):
                self.modal=None
            self.drag=None
        elif event.type==pg.MOUSEMOTION:
            self.mouse=self.point(event.pos)
            if self.down and not self.modal and self.world.open and dist(self.mouse,self.down)>7:
                if self.drag is None:self.drag=self.pending_drag
        elif event.type==pg.MOUSEBUTTONDOWN:
            self.mouse=self.point(event.pos)
            if event.button==1:
                self.down=self.mouse
                self.pending_drag=self.source(self.mouse) if not self.modal and self.world.open else None
            elif event.button==3 and not self.modal and self.world.open:
                self.click(self.mouse,True)
        elif event.type==pg.MOUSEBUTTONUP and event.button==1:
            self.mouse=self.point(event.pos)
            if self.drag and not self.modal and self.world.open:self.drop(self.drag,self.mouse)
            else:self.click(self.mouse)
            self.drag=self.down=None

    def step(self,dt):
        self.poll_updates()
        # Help panels and lost window focus never pause an open restaurant.
        if self.world.process_deliveries():self.persist()
        self.world.update(dt)
        if self.world.open:self.animation+=dt
        self.auto_save+=dt
        if self.auto_save>=15:
            self.persist(); self.auto_save=0

    def run(self):
        if self.persistent and not any(flag in sys.argv for flag in ('--smoke-test','--verify-new-player')):
            from updates import start_check
            self.update_queue=start_check()
        while self.running:
            dt=self.clock.tick(60)/1000
            for event in pg.event.get():
                self.event(event)
                if not self.running:break
            if not self.running:break
            self.step(dt)
            self.draw()
        pg.quit()


def smoke_test(output):
    """Exercise the actual bundled executable on Windows without a display."""
    from datetime import date, datetime, timezone
    from vn_calendar import holiday_name
    assert 'Tết' in holiday_name(date(2026, 2, 17))
    assert 'Hùng Vương' in holiday_name(date(2026, 4, 26))
    probe = World(clock=lambda: datetime(2026, 9, 29, 17, 30, tzinfo=timezone.utc))
    assert probe.now.date() == date(2026, 9, 30) and probe.minute == 30
    app = App(headless=True)
    assert pg.display.get_caption()[0] == GAME_TITLE
    assert (Path(__file__).with_name('assets')/'game.png').exists()
    app.world = World(seed=7)
    assert app.world.cash == 10000000 and app.world.clean == 0 and not app.world.open
    app.draw()
    for name in ['Bát/đĩa', *STOCK_COST]:
        app.world.restock(name,24)
    assert app.world.open_shop()
    assert not app.world.restock('Mì tươi',1)
    app.world.add_party(2)
    app.world.spawn_left = 100000
    app.modal = None
    app.draw()
    app.click((1300, 360))
    app.world.update(app.world.parties[0].buy_seconds)
    app.draw()
    app.click(TICKET.center)
    party = app.world.parties[0]
    assert party.ticket_read
    app.world.update(2)
    assert app.source((party.x, party.y)) == ('party', 1)
    app.drop(('party', 1), TABLE_LAYOUT[0][:2])
    assert app.world.tables[0].group == 1
    for i in range(2):
        app.drop(('raw', 0), POT_POS[i])
    app.modal='help'
    app.step(209)
    app.modal=None
    assert app.world.pot_state(0) == 'cooking'
    app.world.update(1)
    assert app.world.pot_state(0) == 'ready'
    app.draw()
    for i in range(2):
        app.click(POT_POS[i])
        bowl = app.world.bowls[-1]
        app.drop(('bowl', bowl.id), BOWL_POS[0])
        for topping in RECIPES[party.orders[i]]:
            app.drop(('topping', topping), BOWL_POS[bowl.slot])
        app.drop(('bowl', bowl.id), TABLE_LAYOUT[0][:2])
    assert party.phase == 'eating'
    app.world.update(app.world.eating_remaining(party)+1)
    app.drop(('dirty', 0), SINK.center)
    app.draw()
    app.click(TABLE_LAYOUT[0][:2])
    app.draw()
    app.click((1050, 310))
    app.world.update(app.world.wash_left+1)
    assert app.world.clean == 24 and not app.world.tables[0].needs_wipe
    assert not app.world.close_shop()
    for spot in app.world.dirt[:]:
        app.click(DIRT_POS[spot])
    app.action(('close',))
    assert not app.world.open and app.modal == 'report'
    assert 'profit' in app.world.last_report
    app.draw()
    pg.image.save(app.canvas, str(Path(output).with_name('report-preview.png')))
    app.action(('dismiss',))
    app.draw()
    pg.image.save(app.canvas, str(Path(output).with_suffix('.png')))
    from expansion_smoke import check_expansion_ui
    check_expansion_ui(app,output)
    from exit_smoke import check_window_exit
    check_window_exit(App)
    from update_smoke import check_update_ui
    check_update_ui(App)
    pg.quit()
    Path(output).write_text(json.dumps({'ok': True, 'platform': sys.platform,
                                      'frozen': bool(getattr(sys, 'frozen', False)),
                                      'checks': ['update-notification-ui','quit-open-shop','resume-active-shift','quit-closed-shop','permanent-game-name','bundled-noodle-icon','shared-tables','buy-tables-chairs','floor-navigation','supplier-8am-delivery','custom-menu-input','expanded-save', 'vnd-economy','empty-stock','closed-market','no-pause','cleanup-close','profit-report','vietnam-clock', 'lunar-holidays', 'render', 'accept', 'ticket', 'drag-seat',
                                                 '210-second-cook', 'toppings', 'serve',
                                                 'clear', 'wipe', 'manual-wash']}), encoding='utf-8')


def verify_new_player(output):
    """Verify two independent user profiles and a restart without injecting a World."""
    import tempfile
    def initial(w):
        assert w.cash==10_000_000 and w.reputation==7 and not w.open
        assert w.floors==1 and len(w.tables)==1 and w.tables[0].capacity==4
        assert all(q==0 for q in w.stock.values()) and w.clean==0 and w.dishes_owned==0
        assert not w.parties and not w.ledger and not w.deliveries and not w.contract_until
    app=App(headless=True)
    assert not app.has_save and app.modal=='welcome'
    initial(app.world)
    app.draw()
    pg.image.save(app.canvas,str(Path(output).with_suffix('.png')))
    app.action(('begin',));app.world.restock('Mì tươi',1);app.persist()
    budget=app.world.cash
    pg.quit()
    again=App(headless=True)
    assert again.has_save and again.world.cash==budget and again.world.stock['Mì tươi']==1
    pg.quit()
    profile=os.environ['LOCALAPPDATA']
    with tempfile.TemporaryDirectory(prefix='quanmi-second-player-') as other:
        os.environ['LOCALAPPDATA']=other
        another=App(headless=True)
        initial(another.world)
        assert another.modal=='welcome'
        pg.quit()
    os.environ['LOCALAPPDATA']=profile
    Path(output).write_text(json.dumps({'ok':True,'platform':sys.platform,
        'frozen':bool(getattr(sys,'frozen',False)),
        'checks':['fresh-start','empty-inventory','one-table-four-chairs','independent-users','resume-own-save']}),encoding='utf-8')


if __name__ == '__main__':
    flag=next((arg for arg in ('--smoke-test','--verify-new-player') if arg in sys.argv),None)
    if flag:
        import tempfile
        # Verification must never read, change or ship a player's actual save.
        with tempfile.TemporaryDirectory(prefix='quanmi-verification-') as profile:
            os.environ['LOCALAPPDATA']=profile
            output=str(Path(sys.argv[sys.argv.index(flag)+1]).resolve())
            (smoke_test if flag=='--smoke-test' else verify_new_player)(output)
    else:
        App().run()
