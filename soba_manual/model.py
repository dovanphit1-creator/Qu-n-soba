"""Rules for the manual soba game; time values are real, unscaled seconds."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import random
from vn_calendar import vn_now, holiday_name, VIETNAM

COOK_SECONDS = 210.0
LIFT_WINDOW = 10.0
RECIPES = {
    'Kake soba': ('Nước dùng', 'Hành'),
    'Soba tôm': ('Nước dùng', 'Hành', 'Tôm'),
    'Soba bò': ('Nước dùng', 'Hành', 'Bò'),
    'Soba trứng': ('Nước dùng', 'Hành', 'Trứng'),
}
PRICES = {'Kake soba': 35000, 'Soba tôm': 45000, 'Soba bò': 50000, 'Soba trứng': 42000}
STOCK_COST = {'Mì tươi': 6000, 'Nước dùng': 3000, 'Hành': 1000, 'Tôm': 8000, 'Bò': 10000, 'Trứng': 4000}
DISH_COST = 15000
DIRT_POS = [(95, 315), (330, 510), (570, 715), (746, 868)]

def vnd(amount):
    return f'{round(amount):,}'.replace(',', '.') + ' VND'

TABLE_LAYOUT = [(180, 485, 2), (455, 485, 4), (180, 665, 4),
                (455, 665, 2), (180, 845, 4), (455, 845, 4)]
POT_POS = [(836 + col * 118, 396 + row * 102) for row in range(2) for col in range(3)]
BOWL_POS = [(835 + col * 118, 782 + row * 84) for row in range(2) for col in range(3)]


@dataclass
class Party:
    id: int
    size: int
    orders: list
    temper: list
    phase: str = 'door'
    x: float = 280
    y: float = 220
    age: float = 0
    phase_time: float = 0
    ticket_read: bool = False
    table: int = -1
    meals: list = field(default_factory=list)
    paid: int = 0


@dataclass
class Bowl:
    id: int
    slot: int
    mushy: bool = False
    toppings: list = field(default_factory=list)
    stage: str = 'lifted'


@dataclass
class Table:
    capacity: int
    group: int = 0
    dirty: int = 0
    needs_wipe: bool = False


class World:
    def __init__(self, seed=None, practice=False, clock=None):
        self._clock = clock or vn_now
        self.date_key = self.now.date().isoformat()
        self.rng = random.Random(seed)
        self.day = 1
        self.elapsed = 0.0
        self.reputation = 7.0
        self.cash = 10_000_000
        self.stock = {name: 0 for name in STOCK_COST}
        self.clean = 0
        self.dishes_owned = 0
        self.sink = 0
        self.washing = 0
        self.wash_left = 0.0
        self.pots = [None] * 6
        self.bowls = []
        self.parties = []
        self.tables = [Table(cap) for _, _, cap in TABLE_LAYOUT]
        self.walkers = []
        self.spawn_left = .2
        self.next_group = 1
        self.next_bowl = 1
        self.open = False
        self.closing = False
        self.dirt = []
        self.dirt_clock = 0.0
        self.ledger = {}
        self.last_report = None
        self.practice = practice
        self.logs = []
        self.reviews = []
        self.served = 0
        self.sold_today = 0
        self.note('Quán đang đóng. Hãy mua bát và nguyên liệu ở Chợ trước khi mở quán.')

    def note(self, text):
        self.logs.append(text)
        self.logs = self.logs[-12:]
        return text

    @property
    def now(self):
        return self._clock().astimezone(VIETNAM)

    @property
    def holiday(self):
        return holiday_name(self.now.date())

    @property
    def minute(self):
        now = self.now
        return now.hour * 60 + now.minute + now.second / 60

    @property
    def peak(self):
        return 11 * 60 <= self.minute < 14 * 60 or 17 * 60 <= self.minute < 20 * 60

    @property
    def kind(self):
        if self.holiday:
            return 'Ngày lễ'
        return 'Cuối tuần' if self.now.weekday() >= 4 else 'Ngày thường'

    @property
    def bonus(self):
        return {'Ngày thường': (-5, 0), 'Cuối tuần': (0, 5), 'Ngày lễ': (5, 10)}[self.kind][self.peak]

    @property
    def chance(self):
        return min(100.0, max(0.0, self.reputation + self.bonus))

    def group(self, gid):
        return next((p for p in self.parties if p.id == gid), None)

    def add_party(self, size=None):
        size = size or self.rng.choices([1, 2, 3, 4], [42, 32, 18, 8])[0]
        p = Party(self.next_group, size,
                  [self.rng.choice(list(RECIPES)) for _ in range(size)],
                  [self.rng.choice(['Dễ tính', 'Bình thường', 'Khó tính']) for _ in range(size)])
        self.next_group += 1
        self.parties.append(p)
        self.note(f'Nhóm {p.id:03}: Chúng tôi có {size} người. Quán còn chỗ không?')
        return p

    def can_fit(self, size):
        return any(t.capacity >= size and not t.group and not t.needs_wipe and not t.dirty for t in self.tables)

    def respond(self, gid, action):
        p = self.group(gid)
        if not p or p.phase not in ('door', 'waiting'):
            return False
        if action == 'accept':
            if not self.can_fit(p.size):
                self.note('Chưa có bàn sạch đủ chỗ cho cả nhóm. Hãy mời khách đợi.')
                return False
            if len([g for g in self.parties if g.phase in ('queue', 'buying', 'ticket', 'ready')]) >= 5:
                self.note('Khu mua phiếu đã đông. Hãy xếp bàn cho các nhóm trước.')
                return False
            if self.stock['Mì tươi'] + sum(t is not None for t in self.pots) + len(self.bowls) < p.size:
                self.note('Không đủ phần mì cho nhóm này. Có thể nhập thêm hoặc từ chối khách.')
                return False
            p.phase, p.phase_time = 'queue', 0
            self.note(f'Nhóm {p.id:03} đang đến máy mua phiếu. Đợi phiếu xuất hiện rồi nhấp nhận.')
        elif action == 'wait':
            if p.phase == 'waiting':
                self.note(f'Nhóm {p.id:03} đang đợi. Nhấp nhóm để mời vào khi có bàn.')
                return False
            p.phase, p.phase_time = 'waiting', 0
            self.note(f'Nhóm {p.id:03}: Được, chúng tôi sẽ đợi một lúc nhé.')
        elif action == 'decline':
            p.phase, p.phase_time = 'leaving', 0
            self.note(f'Bạn: Hôm nay quán đã hết nguyên liệu, xin hẹn nhóm {p.id:03} lần sau.')
        else:
            return False
        return True

    def collect(self, gid):
        p = self.group(gid)
        if not p or p.phase != 'ticket':
            return False
        p.ticket_read = True
        p.phase, p.phase_time = 'ready', 0
        self.note(f'Đã nhận phiếu nhóm {p.id:03}. Xem món bên phải, rồi kéo nhóm vào bàn đủ chỗ.')
        return True

    def seat(self, gid, index):
        p = self.group(gid)
        t = self.tables[index]
        if not p or p.phase != 'ready' or not p.ticket_read:
            self.note('Phải nhấp nhận phiếu từ máy trước khi xếp bàn.')
            return False
        if t.group or t.dirty or t.needs_wipe:
            self.note('Bàn này chưa sẵn sàng: cần trống, dọn bát và lau sạch.')
            return False
        if t.capacity < p.size:
            self.note(f'Nhóm có {p.size} người nhưng bàn chỉ có {t.capacity} ghế.')
            return False
        t.group = p.id
        p.table, p.phase, p.phase_time = index, 'seated', 0
        self.note(f'Nhóm {p.id:03} ngồi bàn {index+1}. Hãy nấu đúng từng món trên phiếu.')
        return True

    def start_pot(self, index):
        if any(b.stage == 'lifted' and b.slot == index for b in self.bowls):
            self.note('Kéo bát vừa vớt từ nồi sang quầy topping trước khi luộc phần mới.')
            return False
        if self.pots[index] is not None:
            self.note('Nồi đang có mì. Hãy vớt hoặc đổ bỏ trước.')
            return False
        if self.stock['Mì tươi'] <= 0:
            self.note('Hết mì tươi. Mở Nhập hàng để mua thêm.')
            return False
        self.stock['Mì tươi'] -= 1
        self.record('ingredients', STOCK_COST['Mì tươi'])
        self.record('gas', 800)
        self.pots[index] = 0.0
        self.note(f'Nồi {index+1}: bắt đầu luộc 3 phút 30 giây. Vớt trong 10 giây sau khi chín.')
        return True

    def pot_state(self, index):
        age = self.pots[index]
        if age is None:
            return 'empty'
        if age < COOK_SECONDS:
            return 'cooking'
        return 'ready' if age <= COOK_SECONDS + LIFT_WINDOW else 'mushy'

    def lift(self, index):
        status = self.pot_state(index)
        if status not in ('ready', 'mushy'):
            self.note('Mì chưa chín. Cần luộc đủ 3 phút 30 giây.')
            return False
        if self.clean <= 0:
            self.note('Cần bát sạch để vớt mì. Hãy rửa bát trước.')
            return False
        self.clean -= 1
        self.bowls.append(Bowl(self.next_bowl, index, status == 'mushy'))
        self.next_bowl += 1
        self.pots[index] = None
        self.note('Đã vớt mì nhão. Có thể dùng nhưng khách sẽ chấm chất lượng thấp hơn.' if status == 'mushy'
                  else 'Đã vớt mì vào bát. Kéo bát từ nồi xuống một ô quầy topping bên dưới.')
        return True

    def move_prep(self, bid, slot):
        bowl = next((b for b in self.bowls if b.id == bid), None)
        if not bowl or any(b.stage == 'prep' and b.slot == slot for b in self.bowls):
            self.note('Ô quầy này đã có bát. Hãy chọn ô trống khác.')
            return False
        bowl.stage, bowl.slot = 'prep', slot
        self.note(f'Bát {bid} đã ở quầy topping. Kéo các nguyên liệu đúng công thức xuống bát.')
        return True

    def discard_pot(self, index):
        if self.pots[index] is None:
            return False
        self.pots[index] = None
        self.note(f'Đã đổ bỏ mì nồi {index+1}. Có thể luộc phần mới.')
        return True

    def topping(self, bid, name):
        b = next((b for b in self.bowls if b.id == bid), None)
        if not b or name not in STOCK_COST or name == 'Mì tươi':
            return False
        if b.stage != 'prep':
            self.note('Kéo bát xuống quầy topping trước khi thêm nguyên liệu.')
            return False
        if self.stock[name] <= 0:
            self.note(f'Đã hết {name.lower()}.')
            return False
        if len(b.toppings) >= 12:
            self.note('Bát đã đầy topping.')
            return False
        self.stock[name] -= 1
        self.record('ingredients', STOCK_COST[name])
        b.toppings.append(name)
        self.note(f'Bát {b.id}: đã thêm {name.lower()}. Sai hoặc thừa topping vẫn có thể phục vụ.')
        return True

    def serve(self, bid, index):
        b = next((b for b in self.bowls if b.id == bid), None)
        t = self.tables[index]
        p = self.group(t.group)
        if not b or b.stage != 'prep' or not p or p.phase != 'seated' or len(p.meals) >= p.size:
            self.note('Hãy thả bát vào bàn có khách còn đang đợi món.')
            return False
        p.meals.append({'mushy': b.mushy, 'toppings': b.toppings[:]})
        self.bowls.remove(b)
        self.served += 1
        if len(p.meals) == p.size:
            p.phase, p.phase_time = 'eating', 0
            self.note(f'Bàn {index+1} đã đủ {p.size} bát. Khách đang ăn.')
        else:
            self.note(f'Đã giao bát cho khách số {len(p.meals)} nhóm {p.id:03}.')
        return True

    def discard_bowl(self, bid):
        b = next((b for b in self.bowls if b.id == bid), None)
        if not b:
            return False
        self.bowls.remove(b)
        self.sink += 1
        self.note('Đã đổ bỏ phần mì; bát bẩn chuyển đến bồn, cần nhấp Rửa bát.')
        return True

    def clear_table(self, index):
        t = self.tables[index]
        if t.group or not t.dirty:
            return False
        self.sink += t.dirty
        t.dirty = 0
        self.note(f'Bát bẩn đã vào bồn. Nhấp bàn {index+1} để lau và nhấp Rửa bát ở bồn.')
        return True

    def wipe(self, index):
        t = self.tables[index]
        if t.group or t.dirty or not t.needs_wipe:
            return False
        t.needs_wipe = False
        self.note(f'Bàn {index+1} đã sạch, có thể đón nhóm mới.')
        return True

    def wash(self):
        if self.washing or not self.sink:
            self.note('Bồn đang rửa.' if self.washing else 'Chưa có bát bẩn trong bồn.')
            return False
        self.washing = min(6, self.sink)
        self.sink -= self.washing
        self.record('water', self.washing * 200)
        self.wash_left = 2 + self.washing
        self.note(f'Bắt đầu rửa {self.washing} bát. Các mẻ sau cũng cần nhấp Rửa bát.')
        return True

    def review(self, p):
        from collections import Counter
        scores = []
        for i, meal in enumerate(p.meals):
            need, actual = Counter(RECIPES[p.orders[i]]), Counter(meal['toppings'])
            errors = sum((need - actual).values()) + sum((actual - need).values())
            strict = {'Dễ tính': .55, 'Bình thường': .9, 'Khó tính': 1.25}[p.temper[i]]
            score = max(1, min(5, round(5 - errors * strict - (1.4 * strict if meal['mushy'] else 0)
                                      - max(0, p.age - 600) / 300)))
            delta = {1: -.8, 2: -.4, 3: 0, 4: .35, 5: .7}[score]
            self.reputation = max(0, self.reputation + delta)
            reason = 'Đúng món, ngon!' if not errors and not meal['mushy'] else ', '.join(
                x for x in ('Sai/thừa/thiếu topping' if errors else '', 'Mì nhão' if meal['mushy'] else '') if x)
            if p.age > 600:
                reason += ' · Đợi hơi lâu'
            self.reviews.append(f'Nhóm {p.id:03}, khách {i+1} ({p.temper[i]}): {score}/5 — {reason}')
            scores.append(score)
        self.reviews = self.reviews[-18:]
        self.mark_dirty()
        self.note(f'Nhóm {p.id:03} ăn xong: {sum(scores)/max(1,len(scores)):.1f}/5. Danh tiếng {self.reputation:.2f}%.')

    def record(self, field, amount):
        key = self.now.date().isoformat()
        row = self.ledger.setdefault(key, {'revenue': 0, 'ingredients': 0, 'electricity': 0,
                                          'water': 0, 'gas': 0, 'purchases': 0,
                                          'equipment': 0, 'utility_paid': 0, 'closes': 0})
        row[field] += amount

    def totals(self, period='day'):
        result = {}
        for date_key, row in self.ledger.items():
            key = date_key[:{'day': 10, 'month': 7, 'year': 4}[period]]
            total = result.setdefault(key, {k: 0 for k in row})
            for k, value in row.items():
                total[k] += round(value) if k == 'electricity' else value
        for total in result.values():
            total['electricity'] = round(total['electricity'])
            total['utilities'] = total['electricity'] + total['water'] + total['gas']
            total['profit'] = total['revenue'] - total['ingredients'] - total['utilities']
        return result

    def restock(self, name, count=10):
        if self.open:
            self.note('Chợ chỉ hoạt động khi quán đã đóng hoàn toàn.')
            return False
        if not isinstance(count, int) or count <= 0 or name not in (*STOCK_COST, 'Bát/đĩa'):
            return False
        cost = (DISH_COST if name == 'Bát/đĩa' else STOCK_COST[name]) * count
        if self.cash < cost:
            self.note('Ngân sách không đủ cho lần mua này.')
            return False
        if name == 'Bát/đĩa':
            self.clean += count
            self.dishes_owned += count
            self.record('equipment', cost)
        else:
            self.stock[name] += count
            self.record('purchases', cost)
        self.cash -= cost
        self.note(f'Đã mua {count} {name.lower()}: {vnd(cost)}.')
        return True

    def open_shop(self):
        if self.open:
            return False
        if self.clean < 1 or any(self.stock[name] < 1 for name in ('Mì tươi', 'Nước dùng', 'Hành')):
            self.note('Cần ít nhất 1 bát sạch và 1 phần mì, nước dùng, hành để mở quán.')
            return False
        if self.cash < 0:
            self.note('Cần thanh toán chi phí còn thiếu trước khi mở quán.')
            return False
        self.open, self.closing = True, False
        self.dirt_clock = 0
        self.note('Quán đã mở. Không mua hàng hoặc tạm dừng trong lúc kinh doanh.')
        return True

    def mark_dirty(self):
        for spot in range(len(DIRT_POS)):
            if spot not in self.dirt:
                self.dirt.append(spot)
                break

    def sweep(self, spot):
        if spot not in self.dirt:
            return False
        self.dirt.remove(spot)
        self.record('water', 500)
        self.note(f'Đã lau sàn. Còn {len(self.dirt)} chỗ bẩn.')
        return True

    def close_shop(self):
        if not self.open:
            return False
        self.closing = True
        if any(p.phase != 'leaving' for p in self.parties):
            self.note('Đã ngừng đón nhóm mới. Phục vụ hết khách và trả lời các nhóm đang chờ.')
            return False
        if self.bowls or any(p is not None for p in self.pots):
            self.note('Cần xử lý hết mì trong nồi và các bát mì ở quầy trước khi đóng quán.')
            return False
        if any(t.dirty or t.needs_wipe for t in self.tables) or self.sink or self.washing or self.dirt:
            self.note('Chưa thể đóng: hãy rửa hết bát, lau các bàn và nhấp LAU ở các vết bẩn trên sàn.')
            return False
        payment = 0
        for row in self.ledger.values():
            total = round(row['electricity']) + row['water'] + row['gas']
            due = total - row['utility_paid']
            payment += due
            row['utility_paid'] = total
        self.cash -= payment
        self.record('closes', 1)
        key = self.now.date().isoformat()
        self.last_report = dict(self.totals()[key], date=key, cash=self.cash, payment=payment)
        self.open, self.closing = False, False
        self.note('Đã đóng quán và thanh toán điện, nước, ga. Xem tổng kết trước khi về quản lý.')
        return True

    def update(self, dt):
        if not self.open:
            return
        self.record('electricity', 6000 * dt / 3600)
        if not self.closing:
            self.dirt_clock += dt
            if self.dirt_clock >= 120:
                self.dirt_clock %= 120
                self.mark_dirty()
        self.elapsed += dt
        today = self.now.date().isoformat()
        if self.date_key != today:
            self.date_key = today
            self.sold_today = 0
            self.note(f'Đã sang ngày {self.now:%d/%m/%Y} theo giờ Việt Nam.')
        for i, age in enumerate(self.pots):
            if age is not None:
                self.pots[i] += dt
                if age < COOK_SECONDS <= self.pots[i]:
                    self.note(f'Nồi {i+1} chín! Nhấp vớt ngay trong 10 giây.')
        if self.washing:
            self.wash_left -= dt
            if self.wash_left <= 0:
                self.clean += self.washing
                self.washing = 0
                self.note('Đã rửa xong mẻ bát. Bát còn lại trong bồn cần nhấp rửa tiếp.')
        self.spawn_left -= dt
        if self.spawn_left <= 0:
            self.spawn_left += self.rng.uniform(2.0, 3.0)
            east = self.rng.random() < .5
            self.walkers.append({'x': -100 if east else 1240, 'y': self.rng.choice([155, 188]),
                                 'speed': self.rng.uniform(52, 75) * (1 if east else -1),
                                 'size': self.rng.choices([1, 2, 3, 4], [42, 32, 18, 8])[0],
                                 'checked': False, 'color': self.rng.randrange(6)})
        for w in self.walkers[:]:
            old = w['x']
            w['x'] += w['speed'] * dt
            if not w['checked'] and min(old, w['x']) <= 280 <= max(old, w['x']):
                w['checked'] = True
                if self.open and not self.closing and self.rng.random() * 100 < self.chance:
                    if len([p for p in self.parties if p.phase in ('door', 'waiting')]) < 5:
                        self.add_party(w['size'])
                        self.walkers.remove(w)
                        continue
            if w['x'] < -180 or w['x'] > 1370:
                self.walkers.remove(w)
        queued = sorted([p for p in self.parties if p.phase == 'queue'], key=lambda p:p.id)
        if queued and not any(p.phase in ('buying', 'ticket') for p in self.parties):
            queued[0].phase, queued[0].phase_time = 'buying', 0
        outside = [p for p in self.parties if p.phase in ('door', 'waiting')]
        lobby = [p for p in self.parties if p.phase in ('queue', 'ready')]
        for p in self.parties[:]:
            p.age += dt
            p.phase_time += dt
            if p.phase in ('door', 'waiting'):
                idx = outside.index(p)
                target = (260 + idx * 190, 225)
                if p.phase_time > (480 if p.phase == 'waiting' else 300):
                    p.phase, p.phase_time = 'leaving', 0
                    self.reputation = max(0, self.reputation - .15)
                    self.note(f'Nhóm {p.id:03} đã đợi quá lâu và rời đi.')
            elif p.phase in ('buying', 'ticket'):
                target = (650, 374)
                if p.phase == 'buying' and p.phase_time >= 8:
                    p.phase, p.phase_time = 'ticket', 0
                    p.paid = sum(PRICES[o] for o in p.orders)
                    self.cash += p.paid
                    self.record('revenue', p.paid)
                    self.sold_today += p.paid
                    self.note(f'Máy in phiếu nhóm {p.id:03}. Nhấp phiếu vàng để nhận.')
            elif p.phase in ('queue', 'ready'):
                idx = lobby.index(p)
                target = (667, 452 + idx * 91)
            elif p.phase in ('seated', 'eating'):
                tx, ty, _ = TABLE_LAYOUT[p.table]
                target = (tx, ty)
                if p.phase == 'eating' and p.phase_time >= 35:
                    self.review(p)
                    table = self.tables[p.table]
                    table.group, table.dirty, table.needs_wipe = 0, len(p.meals), True
                    p.phase, p.phase_time = 'leaving', 0
            else:
                target = (280, 205) if p.y > 250 else (-130, 190)
                if p.x < -95:
                    self.parties.remove(p)
            dx, dy = target[0] - p.x, target[1] - p.y
            distance = (dx * dx + dy * dy) ** .5
            if distance > .1:
                step = min(1, dt * 145 / distance)
                p.x += dx * step
                p.y += dy * step

    def save(self, path):
        data = {k: v for k, v in self.__dict__.items() if k not in ('rng', '_clock')}
        data['parties'] = [asdict(p) for p in self.parties]
        data['bowls'] = [asdict(b) for b in self.bowls]
        data['tables'] = [asdict(t) for t in self.tables]
        data['version'] = 2
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if data.pop('version') != 2:
            raise ValueError('Phiên bản lưu không phù hợp')
        obj = cls()
        for k, v in data.items():
            if k not in obj.__dict__ or k in ('rng', '_clock'):
                raise ValueError('Dữ liệu lưu không phù hợp')
            setattr(obj, k, v)
        obj.parties = [Party(**p) for p in data['parties']]
        obj.bowls = [Bowl(**b) for b in data['bowls']]
        obj.tables = [Table(**t) for t in data['tables']]
        if len(obj.pots) != 6 or len(obj.tables) != 6 or obj.reputation < 0:
            raise ValueError('Dữ liệu lưu không hợp lệ')
        return obj


def save_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'QuanSobaManual' / 'save-vnd.json'
