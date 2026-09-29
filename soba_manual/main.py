"""Top-down manual restaurant game. Run: python soba_manual/main.py."""
import math
import json
import os
import sys
from pathlib import Path

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
if '--smoke-test' in sys.argv:
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame as pg
from model import (World, RECIPES, STOCK_COST, TABLE_LAYOUT, POT_POS, BOWL_POS,
                   COOK_SECONDS, LIFT_WINDOW, save_path)

from vn_calendar import WEEKDAYS

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


class App:
    def __init__(self, headless=False):
        pg.init()
        if headless:
            size = (1280, 800)
        else:
            info = pg.display.Info()
            size = (min(1440, info.current_w - 50), min(900, info.current_h - 75))
        self.display = pg.display.set_mode(size, pg.RESIZABLE)
        pg.display.set_caption('Quán Soba — Tự tay vận hành quán mì')
        self.canvas = pg.Surface((W, H))
        self.clock = pg.time.Clock()
        self.fonts = {}
        self.world = World()
        self.selected = 0
        self.drag = None
        self.down = None
        self.mouse = (0, 0)
        self.buttons = []
        self.paused = False
        self.modal = 'start'
        self.running = True
        self.auto_save = 0
        self.animation = 0
        self.load_error = ''
        self.has_save = save_path().exists()
        self.last_warning = ''
        self.scale = 1
        self.offset = (0, 0)
        self.update_size()

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
        self.text('QUÁN SOBA', (28, 15), 34, CREAM, True)
        self.text('TỰ TAY VẬN HÀNH', (30, 56), 16, '#bcd0b1')
        world = self.world
        now = world.now
        self.text(f'{now:%d/%m/%Y  %H:%M:%S}', (350, 15), 25, CREAM, True)
        self.text(WEEKDAYS[now.weekday()] + ' · VN UTC+7' + (' · Cao điểm' if world.peak else ''), (350, 52), 17, '#c4d6ba')
        self.text(f'{world.cash:,} xu', (720, 15), 28, GOLD, True)
        self.text(f'Bát sạch: {world.clean} / 24', (722, 54), 19, '#c4d6ba')
        self.text(f'Danh tiếng {world.reputation:.2f}%', (1000, 21), 25, CREAM, True)
        self.button((1386, 18, 185, 49), 'Tiếp tục' if self.paused else 'Tạm dừng', ('pause',), small=True)
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
        self.text('LỐI VÀO', (230, 293), 18, INK, True)
        self.text('KHU BÀN ĂN', (63, 329), 23, '#67492e', True)
        self.text('BẾP 6 NỒI', (844, 253), 20, CREAM, True)
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
        # Tables and chairs.
        for i, (x, y, cap) in enumerate(TABLE_LAYOUT):
            table = world.tables[i]
            chairs = self.chairs(i)
            for cx, cy in chairs:
                self.box((cx-22, cy-22, 44, 44), '#755235', 7)
                self.box((cx-17, cy-17, 34, 32), '#52765a', 5)
            self.box((x-88, y-43, 184, 96), '#92734c', 12)
            self.box((x-92, y-50, 184, 96), '#edce8e', 10, '#a27b47', 4)
            self.text(f'BÀN {i+1}', (x, y-27), 18, '#704f2e', True, True)
            p = world.group(table.group)
            if p:
                self.text(f'{len(p.meals)}/{p.size} bát', (x, y+7), 19, INK, True, True)
                for j, meal in enumerate(p.meals):
                    bx, by = chairs[j]
                    self.bowl(((bx+x)/2, (by+y)/2+4), meal['toppings'], meal['mushy'], 18)
            elif table.dirty:
                self.bowl((x-5, y+7), dirty=True, size=28)
                self.text(f'{table.dirty} bát bẩn · kéo', (x, y+65), 17, RED, True, True)
            elif table.needs_wipe:
                for dx, dy in [(-40, 3), (15, 14), (45, -5)]:
                    pg.draw.ellipse(self.canvas, '#c5995e', (x+dx, y+dy, 17, 9))
                self.text('Nhấp để LAU BÀN', (x, y+65), 17, RED, True, True)
            else:
                self.text(f'{cap} chỗ · sạch', (x, y+8), 19, GREEN, True, True)
        # Living customers and passers-by.
        for w in world.walkers:
            for j in range(w['size']):
                self.person(w['x']+j*29, w['y']+(j%2)*7, PEOPLE[(w['color']+j)%6], self.animation*8+j)
        for p in world.parties:
            if self.drag == ('party', p.id):
                continue
            if p.phase in ('seated', 'eating'):
                for j, (cx, cy) in enumerate(self.chairs(p.table)[:p.size]):
                    self.person(cx, cy, PEOPLE[(p.id+j)%6])
                x, y, _ = TABLE_LAYOUT[p.table]
                self.label_party(p, x, y-105, 'đang ăn' if p.phase == 'eating' else 'đợi món')
            else:
                for j in range(p.size):
                    self.person(p.x+(j-(p.size-1)/2)*24, p.y+(j%2)*5, PEOPLE[(p.id+j)%6], self.animation*7+j)
                status = {'door':'hỏi chỗ', 'waiting':'đợi bàn', 'queue':'đợi mua vé', 'buying':'mua phiếu',
                          'ticket':'nhận phiếu!', 'ready':'kéo vào bàn', 'leaving':'tạm biệt'}[p.phase]
                self.label_party(p, p.x, p.y-48, status)
        p = next((p for p in world.parties if p.phase == 'ticket'), None)
        if p:
            self.box(TICKET, '#fff5b2', 3, '#c08c32')
            for i in range(5):
                pg.draw.line(self.canvas, '#8e7b46', (TICKET.x+8, TICKET.y+14+i*8), (TICKET.right-8, TICKET.y+14+i*8))
            self.text('NHẬN', (TICKET.centerx, TICKET.y-13), 15, RED, True, True)
        self.box((29, 950, 1140, 37), '#334e3d', 8)
        message = world.logs[-1] if world.logs else ''
        size = 20 if self.font(20).size(message)[0] < 1112 else 17
        self.text(message, (42, 956), size, CREAM)

    def chairs(self, index):
        x, y, cap = TABLE_LAYOUT[index]
        return [(x-53, y-65), (x+53, y+65)] if cap == 2 else [(x-53,y-65),(x+53,y-65),(x-53,y+65),(x+53,y+65)]

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
        self.text(f'Danh tiếng {w.reputation:.2f}% + {w.bonus} điểm %', (1208, 196), 18, '#6b705b')
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
            self.text(f'Nhóm {p.id:03} · ' + (f'Bàn {p.table+1}' if p.table >= 0 else 'Chưa xếp bàn'), (1208, 550), 23, GREEN, True)
            y = 590
            for i, order in enumerate(p.orders):
                done = i < len(p.meals)
                self.text(f'{i+1}. {order}' + ('  [đã giao]' if done else ''), (1208, y), 19, '#7a806c' if done else INK, True)
                y += 25
                self.text(' + '.join(RECIPES[order]), (1227, y), 16, '#736b55')
                y += 31
        elif selected:
            self.wrap(f'Nhóm {selected.id:03} chưa giao phiếu. Chờ khách mua ở máy rồi nhấp phiếu màu vàng.', (1208, 551), 340, 22)
        else:
            self.wrap('Nhấp nhóm hoặc bàn để xem đúng món của từng người. Giao bát theo thứ tự 1, 2, 3, 4 trên phiếu.', (1208, 551), 340, 22)
        self.button((1207, 825, 169, 45), 'Nhập hàng', ('modal','stock'), small=True)
        self.button((1384, 825, 175, 45), 'Đánh giá', ('modal','reviews'), small=True, color='#836647')
        self.button((1207, 879, 352, 45), 'Ngừng đón khách' if w.open else 'Dọn xong · mở lại quán', ('close',), small=True, color='#785b42')
        self.button((1207, 936, 169, 35), 'F1 · Cách chơi', ('modal','help'), small=True, color='#687357')
        self.button((1384, 936, 175, 35), 'Lưu và thoát', ('quit',), small=True, color='#687357')

    def render_modal(self):
        if not self.modal and not self.paused:
            return
        shade = pg.Surface((W, H), pg.SRCALPHA)
        shade.fill((10, 28, 23, 190))
        self.canvas.blit(shade, (0, 0))
        self.buttons = []
        self.box((280, 125, 1040, 760), '#fff0d1', 20, '#bfa36b', 3)
        if self.modal == 'start':
            self.text('QUÁN SOBA', (800, 230), 58, INK, True, True)
            self.text('Đón từng nhóm khách. Tự tay làm từng bát mì.', (800, 308), 27, '#5e7354', False, True)
            self.wrap('Một quán nhỏ nhìn từ trên cao. Khách mua phiếu, bạn nhận đơn, xếp bàn và nấu mì bằng chuột. Mỗi nồi cần đúng 3 phút 30 giây.', (400, 369), 800, 25)
            self.button((480, 500, 640, 64), 'Tiếp tục quán đã lưu' if self.has_save else 'Mở quán · danh tiếng 2%', ('continue',))
            self.button((480, 582, 640, 64), 'Luyện tập · có sẵn nhóm khách đầu tiên', ('new','practice'), color='#937141')
            if self.has_save:
                self.button((480, 664, 640, 55), 'Ván mới · danh tiếng 2%', ('confirm_new',), color='#896d51')
            self.wrap('Luyện tập chỉ tạo sẵn nhóm đầu tiên; thời gian nấu và thao tác giống ván thường. Bấm Space để tạm dừng, F1 để xem cách chơi.', (400, 746), 800, 20, '#6b725a')
            if self.load_error:
                self.text(self.load_error, (400, 820), 18, RED)
        elif self.modal == 'confirm_new':
            self.text('Chơi lại từ đầu?', (800, 320), 38, INK, True, True)
            self.text('Tiến trình cũ sẽ được thay bằng ván mới.', (800, 410), 24, INK, False, True)
            self.button((460, 520, 320, 60), 'Bắt đầu ván mới', ('new','normal'))
            self.button((820, 520, 320, 60), 'Quay lại', ('modal','start'), color='#8c7856')
        elif self.modal == 'stock':
            self.text('NHẬP NGUYÊN LIỆU', (330, 162), 34, INK, True)
            self.text(f'Tiền mặt: {self.world.cash:,} xu', (330, 214), 26, GREEN, True)
            y = 278
            for name, cost in STOCK_COST.items():
                self.text(f'{name} · còn {self.world.stock[name]} phần', (337, y+9), 25)
                self.button((878, y, 370, 48), f'Mua 10 · {cost*10:,} xu', ('buy',name), self.world.cash >= cost*10)
                y += 75
            self.button((910, 795, 340, 52), 'Trở lại quán', ('dismiss',))
        elif self.modal == 'reviews':
            self.text('ĐÁNH GIÁ CỦA KHÁCH', (330, 164), 34, INK, True)
            lines = self.world.reviews[-10:] or ['Chưa có đánh giá. Khách sẽ đánh giá sau khi ăn xong.']
            y = 239
            for line in lines:
                y = self.wrap(line, (333, y), 910, 20) + 12
            self.button((910, 795, 340, 52), 'Trở lại quán', ('dismiss',))
        elif self.modal == 'help':
            self.text('MỘT CA LÀM Ở QUÁN SOBA', (330, 160), 34, INK, True)
            lines = [
                '1  Trả lời khách ở cửa: mời vào, mời đợi hoặc từ chối vì hết nguyên liệu.',
                '2  Khách tự mua vé. Nhấp phiếu vàng bên máy, xem đơn ở bên phải.',
                '3  Kéo nhóm đã nhận phiếu vào bàn sạch đủ ghế. Tên nhóm đánh số thứ tự.',
                '4  Kéo mì tươi vào 1 trong 6 nồi. Đợi 3:30, nhấp nồi để vớt trong 10 giây.',
                '5  Mì nhão vẫn vớt dùng được. Nhấp phải nồi để đổ bỏ và luộc lại.',
                '6  Kéo bát vừa vớt xuống quầy, thêm topping rồi kéo từng bát ra bàn.',
                '7  Khách ăn xong: kéo bát bẩn vào bồn, nhấp bàn để lau, nhấp Rửa bát.',
                'Giờ cao điểm: 11–14h và 17–20h. Cuối tuần: thứ Sáu, Bảy, Chủ nhật.',
                'Đồng hồ và lịch theo ngày giờ Việt Nam (UTC+7), tính cả ngày lễ âm lịch.',
                'Khách thường: +0/+10; cuối tuần: +5/+20; ngày lễ: +15/+30 điểm phần trăm.',
                'Mỗi nhóm đi ngang cửa được xét một lần. Danh tiếng ≥ 0, không có trần.',
                'Space: tạm dừng. F1: trợ giúp. Esc: đóng bảng. Tiến trình tự lưu mỗi 15 giây.',
            ]
            y = 226
            for line in lines:
                y = self.wrap(line, (332, y), 930, 20, INK) + 11
            self.button((910, 806, 340, 49), 'Đã hiểu · trở lại quán', ('dismiss',))
        else:
            self.text('QUÁN ĐANG TẠM DỪNG', (800, 385), 39, INK, True, True)
            self.text('Khách và nồi mì dừng. Ngày giờ Việt Nam vẫn theo thực tế.', (800, 455), 24, '#697459', False, True)
            self.button((530, 555, 540, 63), 'Tiếp tục chơi', ('pause',))

    def draw(self):
        self.buttons = []
        self.render_floor()
        self.render_side()
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
        self.update_size()
        scaled = pg.transform.smoothscale(self.canvas, (int(W*self.scale),int(H*self.scale)))
        self.display.fill('#18291e')
        self.display.blit(scaled, self.offset)
        pg.display.flip()

    def hit_table(self, point):
        for i,(x,y,_) in enumerate(TABLE_LAYOUT):
            if pg.Rect(x-100,y-58,200,116).collidepoint(point):
                return i
        return None

    def hit_party(self, point):
        for p in reversed(self.world.parties):
            if p.phase in ('seated','eating'):
                x,y,_ = TABLE_LAYOUT[p.table]
                if pg.Rect(x-88,y-123,176,41).collidepoint(point):
                    return p
            else:
                x,y = p.x,p.y
            if pg.Rect(x-81,y-68,162,103).collidepoint(point):
                return p
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
        if self.modal or self.paused:
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
            if not t.group and not t.dirty and t.needs_wipe:
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
                self.world.serve(ident,table)
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
        try:
            path = save_path().with_name('practice.json') if self.world.practice else save_path()
            self.world.save(path)
            self.last_warning = ''
        except OSError:
            self.last_warning = 'Không lưu được tiến trình. Kiểm tra quyền ghi trong thư mục tài khoản Windows.'

    def action(self, action):
        kind, *args = action
        if kind == 'pause':
            self.paused = not self.paused
            self.drag = None
        elif kind == 'modal':
            self.modal = args[0]
        elif kind == 'dismiss':
            self.modal = None
        elif kind == 'continue':
            if self.has_save:
                try:
                    self.world = World.load(save_path())
                except (OSError, ValueError, KeyError, TypeError):
                    self.load_error = 'Không đọc được bản lưu. Chọn ván mới nếu muốn chơi lại.'
                    return
            self.modal = None
        elif kind == 'confirm_new':
            self.modal = 'confirm_new'
        elif kind == 'new':
            if self.has_save and args[0] == 'practice' and self.modal != 'confirm_new':
                # Practice is separate and does not overwrite an existing normal save.
                self.world = World(practice=True)
            else:
                self.world = World(practice=args[0]=='practice')
            self.selected = self.world.parties[0].id if self.world.parties else 0
            self.modal = None
        elif kind == 'answer':
            self.selected = args[0]
            self.world.respond(*args)
        elif kind == 'wash':
            self.world.wash()
        elif kind == 'buy':
            self.world.restock(args[0])
        elif kind == 'close':
            if self.world.open:
                self.world.open = False
                self.world.note('Đã ngừng nhận khách mới. Phục vụ và dọn xong rồi nhấp mở lại quán.')
            else:
                self.world.next_day()
        elif kind == 'quit':
            self.persist()
            self.running = False

    def event(self, event):
        if event.type == pg.QUIT:
            if self.modal != 'start':
                self.persist()
            self.running = False
        elif event.type == pg.WINDOWFOCUSLOST and self.modal != 'start':
            self.paused = True
            self.drag = None
        elif event.type == pg.VIDEORESIZE:
            self.display = pg.display.set_mode((max(800,event.w),max(500,event.h)),pg.RESIZABLE)
            self.update_size()
        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_F1:
                self.modal = None if self.modal == 'help' else 'help'
            elif event.key == pg.K_ESCAPE:
                if self.modal and self.modal != 'start':
                    self.modal = None
                else:
                    self.paused = not self.paused
            elif event.key == pg.K_SPACE and not self.modal:
                self.paused = not self.paused
            self.drag = None
        elif event.type == pg.MOUSEMOTION:
            self.mouse = self.point(event.pos)
            if self.down and not self.modal and not self.paused and dist(self.mouse,self.down)>7:
                if self.drag is None:
                    self.drag = self.pending_drag
        elif event.type == pg.MOUSEBUTTONDOWN:
            self.mouse = self.point(event.pos)
            if event.button == 1:
                self.down = self.mouse
                self.pending_drag = self.source(self.mouse) if not self.modal and not self.paused else None
            elif event.button == 3 and not self.modal and not self.paused:
                self.click(self.mouse,True)
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.mouse = self.point(event.pos)
            if self.drag and not self.modal and not self.paused:
                self.drop(self.drag,self.mouse)
            else:
                self.click(self.mouse)
            self.drag = self.down = None

    def run(self):
        while self.running:
            dt = min(.1,self.clock.tick(60)/1000)
            for event in pg.event.get():
                self.event(event)
            if not self.modal and not self.paused:
                self.world.update(dt)
                self.animation += dt
                self.auto_save += dt
                if self.auto_save >= 15:
                    self.persist()
                    self.auto_save = 0
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
    app.world = World(seed=7, practice=True)
    app.world.spawn_left = 100000
    app.modal = None
    app.draw()
    app.click((1300, 360))
    app.world.update(8)
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
    app.world.update(209)
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
    app.world.update(35)
    app.drop(('dirty', 0), SINK.center)
    app.draw()
    app.click(TABLE_LAYOUT[0][:2])
    app.draw()
    app.click((1050, 310))
    app.world.update(4)
    assert app.world.clean == 24 and not app.world.tables[0].needs_wipe
    app.draw()
    pg.image.save(app.canvas, str(Path(output).with_suffix('.png')))
    pg.quit()
    Path(output).write_text(json.dumps({'ok': True, 'platform': sys.platform,
                                      'frozen': bool(getattr(sys, 'frozen', False)),
                                      'checks': ['vietnam-clock', 'lunar-holidays', 'render', 'accept', 'ticket', 'drag-seat',
                                                 '210-second-cook', 'toppings', 'serve',
                                                 'clear', 'wipe', 'manual-wash']}), encoding='utf-8')


if __name__ == '__main__':
    if '--smoke-test' in sys.argv:
        smoke_test(sys.argv[sys.argv.index('--smoke-test')+1])
    else:
        App().run()
