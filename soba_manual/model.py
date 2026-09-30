"""Rules for the manual soba game; time values are real, unscaled seconds."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import random
import calendar
from datetime import datetime, timedelta
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
SUPPLIER_PERCENT = 97

def supplier_price(name):
    return STOCK_COST[name] * SUPPLIER_PERCENT // 100

DISH_COST = 15000
TABLE_COST = 800_000
CHAIR_COST = 150_000
FLOOR_COST = {2: 3_000_000, 3: 5_000_000}
DIRT_POS = [(65, 585), (330, 510), (570, 715), (746, 868)]

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
    seats: list = field(default_factory=list)
    recipes: list = field(default_factory=list)
    prices: list = field(default_factory=list)


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
    floor: int = 0
    slot: int = 0


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
        self.tables = [Table(4)]
        self.floors = 1
        self.menu = {name: {"price": PRICES[name], "toppings": list(recipe)} for name, recipe in RECIPES.items()}
        self.stock_value = {name: 0 for name in STOCK_COST}
        self.contract_until = None
        self.deliveries = []
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
                  [self.rng.choice(list(self.menu)) for _ in range(size)],
                  [self.rng.choice(['Dễ tính', 'Bình thường', 'Khó tính']) for _ in range(size)])
        p.recipes = [self.menu[name]["toppings"][:] for name in p.orders]
        p.prices = [self.menu[name]["price"] for name in p.orders]
        self.next_group += 1
        self.parties.append(p)
        self.note(f'Nhóm {p.id:03}: Chúng tôi có {size} người. Quán còn chỗ không?')
        return p

    def at_table(self, index):
        return [p for p in self.parties if p.table == index and p.phase in ('seated', 'eating')]

    def table_position(self, index):
        t = self.tables[index]
        return TABLE_LAYOUT[t.slot][:2]

    def free_seats(self, index):
        t = self.tables[index]
        if t.dirty or t.needs_wipe:
            return []
        used = {seat for p in self.at_table(index) for seat in p.seats}
        return [seat for seat in range(t.capacity) if seat not in used]

    def can_fit(self, size):
        return any(len(self.free_seats(i)) >= size for i in range(len(self.tables)))

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
                self.note('Không đủ phần mì cho nhóm này. Hãy từ chối khách và mua thêm sau khi đóng quán.')
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
        if not 0 <= index < len(self.tables):
            return False
        t = self.tables[index]
        if not p or p.phase != 'ready' or not p.ticket_read:
            self.note('Phải nhấp nhận phiếu từ máy trước khi xếp bàn.')
            return False
        if t.dirty or t.needs_wipe:
            self.note('Bàn này chưa sẵn sàng: cần trống, dọn bát và lau sạch.')
            return False
        seats = self.free_seats(index)
        if len(seats) < p.size:
            self.note(f'Nhóm có {p.size} người nhưng bàn chỉ còn {len(seats)} ghế sạch.')
            return False
        p.seats = seats[:p.size]
        t.group = t.group or p.id
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
            self.note('Hết mì tươi. Chỉ mua thêm ở Chợ sau khi đóng quán.')
            return False
        self.consume('Mì tươi')
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
        self.consume(name)
        b.toppings.append(name)
        self.note(f'Bát {b.id}: đã thêm {name.lower()}. Sai hoặc thừa topping vẫn có thể phục vụ.')
        return True

    def serve(self, bid, index, gid=None):
        b = next((b for b in self.bowls if b.id == bid), None)
        t = self.tables[index]
        waiting = [p for p in self.at_table(index) if p.phase == 'seated' and len(p.meals) < p.size]
        p = next((p for p in waiting if p.id == gid), None) if gid is not None else (waiting[0] if len(waiting) == 1 else None)
        if not p and len(waiting) > 1:
            self.note('Bàn ghép: nhấp tên nhóm cần phục vụ rồi thả bát vào bàn.')
            return False
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
        if not t.dirty:
            return False
        self.sink += t.dirty
        t.dirty = 0
        self.note(f'Bát bẩn đã vào bồn. Nhấp bàn {index+1} để lau và nhấp Rửa bát ở bồn.')
        return True

    def wipe(self, index):
        t = self.tables[index]
        if t.dirty or not t.needs_wipe:
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
            need, actual = Counter(p.recipes[i]), Counter(meal['toppings'])
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
        self.mark_dirty(self.tables[p.table].floor)
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
            self.stock_value[name] += cost
            self.record('purchases', cost)
        self.cash -= cost
        self.note(f'Đã mua {count} {name.lower()}: {vnd(cost)}.')
        return True

    def unit_cost(self, name):
        return self.stock_value[name] / self.stock[name] if self.stock[name] else STOCK_COST[name]

    def consume(self, name):
        cost = self.unit_cost(name)
        self.stock[name] -= 1
        self.stock_value[name] = max(0, self.stock_value[name] - cost)
        self.record('ingredients', cost)

    def recipe_cost(self, toppings):
        return self.unit_cost('Mì tươi') + sum(self.unit_cost(name) for name in toppings)

    def save_menu_item(self, name, price, quantities, original=None):
        if self.open:
            self.note('Chỉ sửa menu khi đóng quán.')
            return False
        name = name.strip()
        if not name or len(name) > 28 or not isinstance(price, int) or not 1 <= price <= 999_999_999:
            self.note('Tên món cần 1–28 ký tự; giá bán là số nguyên từ 1 đến 999.999.999 VND.')
            return False
        if any(k not in STOCK_COST or k == 'Mì tươi' or type(v) is not int or not 0 <= v <= 6 for k,v in quantities.items()) or sum(quantities.values()) > 12:
            self.note('Mỗi topping tối đa 6 phần, tổng tối đa 12 phần.')
            return False
        if name in self.menu and name != original:
            self.note('Tên món đã có trong menu. Hãy dùng tên khác hoặc chọn Sửa.')
            return False
        if original is None and len(self.menu) >= 24:
            self.note('Menu tối đa 24 món. Hãy sửa hoặc xóa món cũ.')
            return False
        if original and original != name:
            self.menu.pop(original, None)
        self.menu[name] = {'price': price, 'toppings': [k for k,v in quantities.items() for _ in range(v)]}
        self.note(f'Đã lưu món {name}: {vnd(price)}. Khách có thể mua món này ở máy vé.')
        return True

    def delete_menu_item(self, name):
        if self.open or name not in self.menu or len(self.menu) <= 1:
            self.note('Menu phải còn ít nhất 1 món; chỉ xóa khi đóng quán.')
            return False
        del self.menu[name]
        self.note('Đã xóa món khỏi menu.')
        return True

    def buy_table(self, floor):
        if self.open or not 0 <= floor < self.floors:
            return False
        slots = {t.slot for t in self.tables if t.floor == floor}
        if len(slots) >= 6 or self.cash < TABLE_COST:
            self.note('Mỗi tầng tối đa 6 bàn; cần đủ ngân sách để mua.')
            return False
        self.cash -= TABLE_COST
        self.record('equipment', TABLE_COST)
        self.tables.append(Table(0, floor=floor, slot=next(i for i in range(6) if i not in slots)))
        self.note('Đã mua bàn trống. Hãy mua ghế cho bàn trước khi đón khách.')
        return True

    def buy_chair(self, index):
        if self.open or not 0 <= index < len(self.tables):
            return False
        t = self.tables[index]
        if t.capacity >= 4 or self.cash < CHAIR_COST:
            self.note('Bàn tối đa 4 ghế; cần đủ ngân sách để mua.')
            return False
        self.cash -= CHAIR_COST
        t.capacity += 1
        self.record('equipment', CHAIR_COST)
        self.note(f'Đã thêm ghế: bàn {index+1} có {t.capacity}/4 ghế.')
        return True

    def build_floor(self):
        if self.open or self.floors >= 3:
            self.note('Chỉ xây khi đóng quán, tối đa tổng cộng 3 tầng.')
            return False
        cost = FLOOR_COST[self.floors+1]
        if self.cash < cost:
            self.note('Chưa đủ ngân sách xây tầng.')
            return False
        self.cash -= cost
        self.record('equipment', cost)
        self.floors += 1
        self.note(f'Đã xây tầng {self.floors}. Mua bàn và ghế để sử dụng tầng mới.')
        return True

    @property
    def contract_active(self):
        return bool(self.contract_until and self.now.date().isoformat() < self.contract_until)

    def sign_contract(self):
        if self.open:
            return False
        if self.contract_active:
            self.note('Hợp đồng hiện tại vẫn còn hiệu lực.')
            return False
        today = self.now.date()
        month = today.month % 12 + 1
        year = today.year + (today.month == 12)
        self.contract_until = today.replace(year=year, month=month, day=min(today.day, calendar.monthrange(year,month)[1])).isoformat()
        self.note(f'Đã ký hợp đồng 1 tháng, hết hạn ngày {self.contract_until}; đơn hàng tính giá lẻ giảm 3%.')
        return True

    def place_order(self, quantities):
        now = self.now
        if self.open or not self.contract_active:
            self.note('Đóng quán và ký hợp đồng còn hiệu lực trước khi đặt hàng.')
            return False
        if now.hour >= 23:
            self.note('Đã qua hạn 23:00 Việt Nam. Hãy đặt đơn vào ngày mai.')
            return False
        if not quantities or any(k not in STOCK_COST or type(v) is not int or not 0 <= v <= 9999 for k,v in quantities.items()) or not any(quantities.values()):
            self.note('Chọn số lượng nguyên liệu cần giao (1–9.999 phần mỗi loại).')
            return False
        delivery_at = (now + timedelta(days=1)).replace(hour=8,minute=0,second=0,microsecond=0)
        today = now.date().isoformat()
        if any(order['placed'] == today for order in self.deliveries):
            self.note('Hôm nay đã đặt đơn. Mỗi ngày đặt 1 đơn cho sáng hôm sau.')
            return False
        cost = sum(supplier_price(k) * v for k,v in quantities.items())
        if self.cash < cost:
            self.note('Không đủ ngân sách thanh toán đơn hàng.')
            return False
        self.cash -= cost
        self.record('purchases', cost)
        self.deliveries.append({'placed': today, 'due': delivery_at.isoformat(),
                                'quantities': dict(quantities), 'unit_prices': {name: supplier_price(name) for name in quantities},
                                'cost': cost, 'delivered': False})
        self.note(f'Đã trả {vnd(cost)}; giao 08:00 ngày {delivery_at:%d/%m/%Y}.')
        return True

    def process_deliveries(self):
        changed = False
        now = self.now
        for order in self.deliveries:
            if not order['delivered'] and now >= datetime.fromisoformat(order['due']):
                # Old prepaid orders retain their actual purchase cost after a price change.
                retail_total = sum(STOCK_COST[k] * v for k,v in order['quantities'].items())
                for name, quantity in order['quantities'].items():
                    unit = order.get('unit_prices', {}).get(name)
                    if unit is None:
                        unit = STOCK_COST[name] * order['cost'] / retail_total
                    self.stock[name] += quantity
                    self.stock_value[name] += quantity * unit
                order['delivered'] = True
                changed = True
                self.note('Nhà cung cấp đã giao đơn ' + order['placed'] + ' vào kho, không thu thêm tiền.')
        return changed

    def open_shop(self):
        if self.open:
            return False
        from collections import Counter
        available = any(all(self.stock[name] >= qty for name,qty in Counter(['Mì tươi', *item['toppings']]).items()) for item in self.menu.values())
        if self.clean < 1 or not available:
            self.note('Cần bát sạch và đủ nguyên liệu làm ít nhất 1 món trong menu để mở quán.')
            return False
        if self.cash < 0:
            self.note('Cần thanh toán chi phí còn thiếu trước khi mở quán.')
            return False
        self.open, self.closing = True, False
        self.dirt_clock = 0
        self.note('Quán đã mở. Không mua hàng hoặc tạm dừng trong lúc kinh doanh.')
        return True

    def mark_dirty(self, floor=None):
        floor = self.rng.randrange(self.floors) if floor is None else floor
        for spot in range(floor * len(DIRT_POS), (floor+1) * len(DIRT_POS)):
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
        self.process_deliveries()
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
                    p.paid = sum(p.prices)
                    self.cash += p.paid
                    self.record('revenue', p.paid)
                    self.sold_today += p.paid
                    self.note(f'Máy in phiếu nhóm {p.id:03}. Nhấp phiếu vàng để nhận.')
            elif p.phase in ('queue', 'ready'):
                idx = lobby.index(p)
                target = (667, 452 + idx * 91)
            elif p.phase in ('seated', 'eating'):
                tx, ty = self.table_position(p.table)
                target = (tx, ty)
                if p.phase == 'eating' and p.phase_time >= 35:
                    self.review(p)
                    table = self.tables[p.table]
                    table.dirty += len(p.meals)
                    table.needs_wipe = True
                    p.phase, p.phase_time = 'leaving', 0
                    others = self.at_table(p.table)
                    table.group = others[0].id if others else 0
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
        data['version'] = 3
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        version = data.pop('version')
        if version not in (2, 3):
            raise ValueError('Phiên bản lưu không phù hợp')
        obj = cls()
        for k, v in data.items():
            if k not in obj.__dict__ or k in ('rng', '_clock'):
                raise ValueError('Dữ liệu lưu không phù hợp')
            setattr(obj, k, v)
        obj.parties = [Party(**p) for p in data['parties']]
        obj.bowls = [Bowl(**b) for b in data['bowls']]
        obj.tables = [Table(**t) for t in data['tables']]
        if version == 2:
            from shutil import copy2
            backup=Path(path).with_suffix('.v2.bak')
            if not backup.exists():copy2(path,backup)
            obj.stock_value = {name: qty * STOCK_COST[name] for name, qty in obj.stock.items()}
            for i, t in enumerate(obj.tables):
                t.floor, t.slot = divmod(i, 6)
            obj.floors = max(1, (len(obj.tables)+5)//6)
            for party in obj.parties:
                party.recipes = [list(RECIPES[name]) for name in party.orders]
                party.prices = [PRICES[name] for name in party.orders]
                if party.phase in ('seated', 'eating'):
                    party.seats = list(range(party.size))
        if len(obj.pots) != 6 or not 1 <= obj.floors <= 3 or not 1 <= len(obj.tables) <= 18 or obj.reputation < 0:
            raise ValueError('Dữ liệu lưu không hợp lệ')
        return obj


def save_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'QuanSobaManual' / 'save-vnd.json'
