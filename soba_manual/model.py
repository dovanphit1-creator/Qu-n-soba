"""Rules for the manual soba game; time values are real, unscaled seconds."""
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import random
import calendar
from datetime import datetime, timedelta
from vn_calendar import vn_now, holiday_name, VIETNAM
from staff import StaffMixin
from finance import FinanceMixin
from catalog import STOCK_COST, STOCK_UNITS, DRINKS, DRINK_PRICES

COOK_SECONDS = 210.0
LIFT_WINDOW = 10.0
SERVICE_TIME_SCALE = 0.6  # 40% shorter service actions; cooking and patience unchanged.
RECIPES = {
    'Kake soba': ('Nước dùng', 'Hành'),
    'Soba tôm': ('Nước dùng', 'Hành', 'Tôm'),
    'Soba bò': ('Nước dùng', 'Hành', 'Bò'),
    'Soba trứng': ('Nước dùng', 'Hành', 'Trứng'),
}
PRICES = {'Kake soba': 65000, 'Soba tôm': 85000, 'Soba bò': 90000, 'Soba trứng': 75000}
LEGACY_COST = {'Mì tươi':6000,'Nước dùng':3000,'Hành':1000,'Tôm':8000,'Bò':10000,'Trứng':4000}
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
    refunded: int = 0
    seats: list = field(default_factory=list)
    recipes: list = field(default_factory=list)
    prices: list = field(default_factory=list)
    eat_seconds: list = field(default_factory=list)
    choose_seconds: list = field(default_factory=list)
    door_patience: list = field(default_factory=list)
    wait_patience: list = field(default_factory=list)
    queue_patience: list = field(default_factory=list)
    buy_seconds: float = 0
    paid_age: float = 0
    drinks: list = field(default_factory=list)
    drinks_served: list = field(default_factory=list)
    wait_number: int = 0
    in_a_hurry: bool = False
    entered: bool = False


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
    soil: int = 0


class World(StaffMixin,FinanceMixin):
    def __init__(self, seed=None, practice=False, clock=None):
        self._clock = clock or vn_now
        self.date_key = self.now.date().isoformat()
        self.rng = random.Random(seed)
        self.day = 1
        self.elapsed = 0.0
        self.service_time_scale = SERVICE_TIME_SCALE
        self.init_staff()
        self.init_finance()
        self.sound_events = []
        self.speech_events = []
        self.reputation = 7.0
        self.cash = 10_000_000
        self.stock = {name: 0 for name in STOCK_COST}
        self.clean = 0
        self.dishes_owned = 0
        self.sink = 0
        self.washing = 0
        self.wash_left = 0.0
        self.wipe_table = -1
        self.wipe_left = 0.0
        self.wash_owner = "auto"
        self.wipe_owner = "auto"
        self.sweep_owner = "auto"
        self.sweep_spot = -1
        self.sweep_left = 0.0
        self.player_cleaning = None
        self.next_wait_number = 1
        self.dirt_reasons = {}
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
        from collections import Counter
        from operations import required_stock
        free=Counter(self.stock)-required_stock(self);orders=[]
        for _ in range(size):
            choices=[name for name,item in self.menu.items() if all(free[n]>=q for n,q in Counter(['Mì tươi',*item['toppings']]).items())]
            name=self.rng.choice(choices or list(self.menu));orders.append(name)
            free.subtract(Counter(['Mì tươi',*self.menu[name]['toppings']]))
        p = Party(self.next_group, size,
                  orders,
                  [self.rng.choice(['Dễ tính', 'Bình thường', 'Khó tính']) for _ in range(size)])
        p.in_a_hurry = self.rng.random()<.35
        self.assign_personality(p)
        p.recipes = [self.menu[name]["toppings"][:] for name in p.orders]
        p.prices = [self.menu[name]["price"] for name in p.orders]
        available_drinks = [name for name in DRINKS if self.stock[name] > sum(g.drinks.count(name)-g.drinks_served.count(name) for g in self.parties)]
        p.drinks = [self.rng.choice(available_drinks) if available_drinks and self.rng.random()<.35 else "" for _ in range(size)]
        p.drinks_served = ["" for _ in range(size)]
        self.next_group += 1
        self.parties.append(p)
        self.note(f'Nhóm {p.id:03}: Chúng tôi có {size} người. Quán còn chỗ không?')
        return p

    def assign_personality(self, p):
        if p.eat_seconds:return
        for temper in p.temper:
            p.eat_seconds.append(self.rng.triangular(300,1200,660)*SERVICE_TIME_SCALE)
            p.choose_seconds.append(self.rng.triangular(10,45,20)*SERVICE_TIME_SCALE)
            factor={'Dễ tính':1.25,'Bình thường':1.0,'Khó tính':.75}[temper]
            p.door_patience.append(self.rng.uniform(80,240)*factor)
            p.wait_patience.append(self.rng.uniform(240,960)*factor)
            p.queue_patience.append(self.rng.uniform(80,480)*factor)
        p.buy_seconds=sum(p.choose_seconds)+self.rng.uniform(10,25)

    def eating_remaining(self,p):
        return max((m.get('eat_left',0) for m in p.meals),default=0)

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

    def party_stock_available(self,p):
        from operations import required_stock
        from collections import Counter
        need=Counter()
        for recipe in p.recipes:need+=Counter(['Mì tươi',*recipe])
        reserved=required_stock(self)
        return all(self.stock[n]-reserved[n]>=q for n,q in need.items())

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
            if not self.party_stock_available(p):
                self.note('Không đủ phần mì cho nhóm này. Hãy từ chối khách và mua thêm sau khi đóng quán.')
                return False
            p.phase, p.phase_time = 'queue', 0
            if not p.entered:
                p.entered=True;self.record('customers',p.size);self.record('groups',1)
            if self.rng.random()<.12:self.mark_dirty(0,f'Dấu giày nhóm {p.id:03} mang bụi vào quán',0)
            self.note(f'Nhóm {p.id:03} đang đến máy mua phiếu. Đợi phiếu xuất hiện rồi nhấp nhận.')
        elif action == 'wait':
            if p.phase == 'waiting':
                self.note(f'Nhóm {p.id:03} đang đợi. Nhấp nhóm để mời vào khi có bàn.')
                return False
            if p.in_a_hurry:
                p.phase,p.phase_time='leaving',0
                self.note(f'Nhóm {p.id:03}: Chúng tôi đang vội, xin phép về luôn.');return True
            p.phase, p.phase_time = 'waiting', 0
            p.wait_number=self.next_wait_number;self.next_wait_number+=1
            self.note(f'Nhóm {p.id:03}: Nhận thẻ chờ {p.wait_number:03}, chúng tôi đợi nhé.')
        elif action == 'decline':
            p.phase, p.phase_time = 'leaving', 0
            self.note(f'Bạn: Hôm nay quán đã hết nguyên liệu, xin hẹn nhóm {p.id:03} lần sau.')
        else:
            return False
        return True

    def refund_amount(self,gid):
        p=self.group(gid)
        if not p or p.refunded or p.paid<=0 or p.phase not in ('ticket','ready','seated','eating'):return 0
        waiting=len(p.meals)<p.size or any(d and p.drinks_served[i]!=d for i,d in enumerate(p.drinks))
        return p.paid if waiting else 0

    def refund_party(self,gid):
        amount=self.refund_amount(gid)
        if not amount:
            self.note('Chỉ hoàn tiền cho nhóm đã mua phiếu và còn chờ món / đồ uống.');return False
        p=self.group(gid)
        # A paid ticket is a liability: refund even if the shop's cash goes negative.
        # Used ingredients remain expenses; full-ticket refund is the shop's apology.
        self.cash-=amount;self.record('refunds',amount);p.refunded=amount
        p.phase,p.phase_time='leaving',0
        if p.table>=0:
            t=self.tables[p.table]
            t.dirty+=len(p.meals);t.needs_wipe=True;t.soil+=max(1,len(p.meals))
            other=self.at_table(p.table);t.group=other[0].id if other else 0
        p.seats=[]
        cancelled={int(k):o for k,o in self.staff_cooking.items() if o['gid']==gid}
        bids={o['bid'] for o in cancelled.values() if 'bid' in o}
        for e in self.employees:
            action=e['job']['action'] if e['job'] else []
            if not action:continue
            kind=action[0]
            matching=(kind in ('door','collect','seat') and action[1]==gid) or (kind=='start' and action[2]==gid) or (kind in ('serve','drink') and len(action)>3 and action[3]==gid) or (kind=='lift' and action[1] in cancelled) or (kind in ('prep','top') and action[1] in bids)
            if matching:e['job']=None;e['status']='Phiếu đã hoàn tiền'
        for k in cancelled:self.staff_cooking.pop(str(k),None)
        # Pots / prepared bowls stay in the kitchen for reuse or disposal, never returned to stock.
        self.note(f'Đã hoàn {vnd(amount)} cho nhóm {gid:03}. Xin lỗi vì không đủ nguyên liệu; khách đang ra về.')
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
        self.use_utility('gas', .012)
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
        if not b or name not in STOCK_COST or name == 'Mì tươi' or name in DRINKS:
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
        duration=p.eat_seconds[len(p.meals)]
        p.meals.append({'mushy': b.mushy, 'toppings': b.toppings[:],
                        'eat_left':duration,'eat_total':duration,
                        'wait':max(0,p.age-p.paid_age),
                        'cleanliness': len(self.dirt) + int(t.needs_wipe),
                        'spill_at':duration*self.rng.uniform(.25,.75) if self.rng.random()<.18 else -1})
        if self.rng.random()<.08:
            self.mark_dirty(t.floor,f'Nước dùng rơi khi phục vụ nhóm {p.id:03}, bàn {index+1}',t.slot%4)
        self.bowls.remove(b)
        for key,job in list(self.staff_cooking.items()):
            if job.get('bid')==bid:self.staff_cooking.pop(key,None)
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
        if self.rng.random()<.12:self.mark_dirty(t.floor,f'Nước dùng nhỏ xuống khi thu bát bàn {index+1}',t.slot%4)
        self.sink += t.dirty
        t.dirty = 0
        self.note(f'Bát bẩn đã vào bồn. Nhấp bàn {index+1} để lau và nhấp Rửa bát ở bồn.')
        return True

    def wipe(self, index, owner="auto"):
        t = self.tables[index]
        if t.dirty or not t.needs_wipe or self.wipe_table>=0:
            return False
        self.wipe_table=index
        self.wipe_owner=owner
        self.wipe_left=SERVICE_TIME_SCALE*min(45,10+5*max(1,t.soil)+self.rng.uniform(5,15))
        self.note(f'Đang lau bàn {index+1}: khoảng {self.wipe_left:.0f} giây.')
        return True

    def wash(self, owner="auto"):
        if self.washing or not self.sink:
            self.note('Bồn đang rửa.' if self.washing else 'Chưa có bát bẩn trong bồn.')
            return False
        self.wash_owner=owner
        self.washing = self.sink
        self.sink = 0
        self.use_utility('water', self.washing * .005)
        self.wash_left = SERVICE_TIME_SCALE*(15 + sum(self.rng.uniform(20,40) for _ in range(self.washing)))
        self.note(f'Rửa {self.washing} bát: khoảng {self.wash_left:.0f} giây. Bát thêm sau cần bấm rửa lượt mới.')
        return True

    def serve_drink(self, name, index, gid=None):
        if name not in DRINKS or self.stock[name]<=0 or not 0<=index<len(self.tables):return False
        groups=[p for p in self.at_table(index) if any(d and p.drinks_served[i]!=d for i,d in enumerate(p.drinks))]
        p=next((p for p in groups if p.id==gid),None) if gid is not None else (groups[0] if len(groups)==1 else None)
        if not p:return False
        target=next((i for i,d in enumerate(p.drinks) if d==name and p.drinks_served[i]!=d),None)
        if target is None:
            self.note('Đồ uống không khớp phiếu của nhóm đã chọn.');return False
        self.consume(name);p.drinks_served[target]=name
        self.note(f'Đã giao {name} cho khách {target+1}, nhóm {p.id:03}.')
        return True

    def review(self, p):
        from collections import Counter
        scores=[]
        for i,meal in enumerate(p.meals):
            need,actual=Counter(p.recipes[i]),Counter(meal['toppings'])
            errors=sum((need-actual).values())+sum((actual-need).values())
            strict={'Dễ tính':.7,'Bình thường':1.0,'Khó tính':1.35}[p.temper[i]]
            wait=meal.get('wait',0)
            dirt=meal.get('cleanliness',0)
            missing_drink=bool(p.drinks and p.drinks[i] and p.drinks_served[i]!=p.drinks[i])
            deduction=(errors*.85+(1.7 if meal['mushy'] else 0)+max(0,wait-420)/420+min(1,dirt*.15)+(1 if missing_drink else 0))*strict
            score=max(0,min(5,round(4.8-deduction+self.rng.uniform(-.25,.2))))
            # Individual reviews have bounded influence, independent of current reputation.
            delta={0:-1.2,1:-.85,2:-.45,3:-.1,4:.25,5:.5}[score]
            self.reputation=max(5,self.reputation+delta)
            reasons=[]
            if errors:reasons.append('Sai/thừa/thiếu topping')
            if meal['mushy']:reasons.append('Mì nhão')
            if wait>420:reasons.append('Đợi món lâu')
            if dirt:reasons.append('Quán chưa sạch')
            if missing_drink:reasons.append('Thiếu đồ uống đã trả tiền')
            reason=' · '.join(reasons) or 'Đúng món, mì ngon, phục vụ tốt'
            self.reviews.append(f'Nhóm {p.id:03}, khách {i+1} ({p.temper[i]}): {score}/5 sao — {reason} ({delta:+.2f}%)')
            self.record('star_sum',score);self.record('rating_count',1)
            scores.append(score)
        self.reviews=self.reviews[-18:]
        self.note(f'Nhóm {p.id:03} ăn xong: {sum(scores)/max(1,len(scores)):.1f}/5 sao. Danh tiếng {self.reputation:.2f}%.')

    def record(self, field, amount):
        key = self.now.date().isoformat()
        row = self.ledger.setdefault(key, {'revenue': 0, 'ingredients': 0, 'electricity': 0,
                                          'water': 0, 'gas': 0, 'purchases': 0,
                                          'equipment': 0, 'utility_paid': 0, 'closes': 0})
        row[field] = row.get(field,0) + amount

    def totals(self, period='day'):
        result = {}
        for date_key, row in self.ledger.items():
            key = date_key[:{'day': 10, 'month': 7, 'year': 4}[period]]
            total = result.setdefault(key, {k: 0 for k in row})
            for k, value in row.items():
                total[k] = total.get(k,0) + (round(value) if k == 'electricity' else value)
        for total in result.values():
            total['electricity'] = round(total['electricity'])
            total['utilities'] = total['electricity'] + total['water'] + total['gas']
            total['customers']=total.get('customers',0)
            total['rating_count']=total.get('rating_count',0)
            total['average_stars']=total.get('star_sum',0)/total['rating_count'] if total['rating_count'] else None
            total['refunds']=total.get('refunds',0)
            total['net_revenue']=total['revenue']-total['refunds']
            total['profit'] = total['net_revenue'] - total['ingredients'] - total['utilities'] - total.get('wages',0) - total.get('employer_insurance',0) - total.get('termination',0) - total.get('rent',0) - total.get('shop_tax',0)
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
        if any(k not in STOCK_COST or k == 'Mì tươi' or k in DRINKS or type(v) is not int or not 0 <= v <= 6 for k,v in quantities.items()) or sum(quantities.values()) > 12:
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
                retail_total = sum(LEGACY_COST.get(k,STOCK_COST[k]) * v for k,v in order['quantities'].items())
                for name, quantity in order['quantities'].items():
                    unit = order.get('unit_prices', {}).get(name)
                    if unit is None:
                        unit = LEGACY_COST.get(name,STOCK_COST[name]) * order['cost'] / retail_total
                    self.stock[name] += quantity
                    self.stock_value[name] += quantity * unit
                order['delivered'] = True
                changed = True
                self.note('Nhà cung cấp đã giao đơn ' + order['placed'] + ' vào kho, không thu thêm tiền.')
        return changed

    def open_shop(self):
        if self.day_decisions.get(self.now.date().isoformat())=='closed':
            self.note('Hôm nay đã chọn cho quán nghỉ. Đổi quyết định ở Nhân sự → Thiếu người để mở lại.');return False
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
        if self.lease is None:self.sign_lease(0)
        self.open, self.closing = True, False
        self.dirt_clock = 0
        self.note('Quán đã mở. Không mua hàng hoặc tạm dừng trong lúc kinh doanh.')
        return True

    def mark_dirty(self, floor=0, reason='Vết bẩn còn lại từ phiên bản trước', preferred=0):
        floor=0 if floor is None else floor
        spots=list(range(floor*len(DIRT_POS),(floor+1)*len(DIRT_POS)))
        preferred=floor*len(DIRT_POS)+preferred%len(DIRT_POS)
        spots.sort(key=lambda spot:spot!=preferred)
        for spot in spots:
            if spot not in self.dirt:
                self.dirt.append(spot)
                self.dirt_reasons[str(spot)]=reason
                self.note('Sàn bẩn: '+reason+'.')
                return spot
        self.note('Sàn đã bẩn thêm: '+reason+'.')
        return None

    def cleanup_active(self,kind,owner):
        if owner=='auto':return True
        if owner=='player':return self.player_cleaning==kind
        e=self.employee(owner)
        return bool(e and e['present'])

    def sweep(self, spot, owner="auto"):
        if spot not in self.dirt or self.sweep_spot>=0:return False
        self.sweep_spot=spot;self.sweep_owner=owner
        self.sweep_left=self.rng.uniform(15,35)*SERVICE_TIME_SCALE
        self.note(f'Đang lau sàn: khoảng {self.sweep_left:.0f} giây.')
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
        if any(t.dirty or t.needs_wipe for t in self.tables) or self.sink or self.washing or self.wipe_table>=0 or self.dirt:
            self.note('Chưa thể đóng: hãy rửa hết bát, lau các bàn và nhấp LAU ở các vết bẩn trên sàn.')
            return False
        payment = 0
        self.record('closes', 1)
        key = self.now.date().isoformat()
        self.last_report = dict(self.totals()[key], date=key, cash=self.cash, payment=payment)
        self.open, self.closing = False, False
        self.note('Đã đóng quán. Điện nước ga được chốt theo lịch hóa đơn; xem tổng kết và Chi phí.')
        return True

    def update(self, dt):
        dt=max(0,dt)
        self.process_finance()
        self.process_deliveries()
        self.update_staff(dt)
        if not self.open:
            return
        self.use_utility('electricity', 2 * dt / 3600)
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
                    self.sound_events.append(i)
                    self.note(f'Nồi {i+1} chín! Nhấp vớt ngay trong 10 giây.')
        if self.washing and self.cleanup_active("wash",self.wash_owner):
            self.wash_left -= dt
            if self.wash_left <= 0:
                self.clean += self.washing
                self.washing = 0
                self.wash_left = 0
                if self.rng.random()<.15:self.mark_dirty(0,'Nước rửa bát bắn ra cạnh bồn',3)
                self.note('Đã rửa xong mẻ bát. Bát còn lại trong bồn cần nhấp rửa tiếp.')
        if self.wipe_table>=0 and self.cleanup_active("wipe",self.wipe_owner):
            self.wipe_left=max(0,self.wipe_left-dt)
            if self.wipe_left==0:
                t=self.tables[self.wipe_table]
                t.needs_wipe=bool(t.dirty)
                if not t.dirty:t.soil=0
                self.note(f'Đã lau xong bàn {self.wipe_table+1}.')
                self.wipe_table=-1
        if self.sweep_spot>=0 and self.cleanup_active('sweep',self.sweep_owner):
            self.sweep_left=max(0,self.sweep_left-dt)
            if not self.sweep_left:
                spot=self.sweep_spot
                if spot in self.dirt:self.dirt.remove(spot)
                self.dirt_reasons.pop(str(spot),None);self.sweep_spot=-1
                self.use_utility('water',.01);self.note('Đã lau sạch vết bẩn trên sàn.')
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
        if queued and not any(p.phase == 'buying' for p in self.parties):
            queued[0].phase, queued[0].phase_time = 'buying', 0
        for p in self.parties:
            if p.phase=='queue' and p.phase_time+dt>=min(p.queue_patience):
                p.phase,p.phase_time='leaving',0
                self.reputation=max(5,self.reputation-.15)
                self.note(f'Nhóm {p.id:03} hết kiên nhẫn xếp hàng mua phiếu và rời đi (chưa trả tiền).')
        outside = [p for p in self.parties if p.phase in ('door', 'waiting')]
        lobby = [p for p in self.parties if p.phase in ('queue', 'ready', 'ticket')]
        for p in self.parties[:]:
            p.age += dt
            p.phase_time += dt
            if p.phase in ('door', 'waiting'):
                idx = outside.index(p)
                target = (260 + idx * 190, 225)
                if p.phase_time > min(p.wait_patience if p.phase == 'waiting' else p.door_patience):
                    p.phase, p.phase_time = 'leaving', 0
                    self.reputation = max(5, self.reputation - .15)
                    self.note(f'Nhóm {p.id:03} đã đợi quá lâu và rời đi.')
            elif p.phase == 'buying':
                target = (650, 374)
                if p.phase == 'buying' and p.phase_time >= p.buy_seconds:
                    p.phase, p.phase_time = 'ticket', 0
                    p.paid_age=p.age
                    p.paid = sum(p.prices) + sum(DRINK_PRICES.get(name,0) for name in p.drinks)
                    self.cash += p.paid
                    self.record('revenue', p.paid)
                    self.sold_today += p.paid
                    self.note(f'Máy in phiếu nhóm {p.id:03}. Nhấp phiếu vàng để nhận.')
            elif p.phase in ('queue', 'ready', 'ticket'):
                idx = lobby.index(p)
                target = (667, 452 + idx * 91)
            elif p.phase in ('seated', 'eating'):
                tx, ty = self.table_position(p.table)
                target = (tx, ty)
                for i,meal in enumerate(p.meals):
                    old=meal['eat_left']
                    meal['eat_left']=max(0,old-dt)
                    if old>meal.get('spill_at',-1)>=meal['eat_left']:
                        meal['spill_at']=-1
                        self.mark_dirty(self.tables[p.table].floor,
                            f'Khách {i+1} nhóm {p.id:03} làm rơi mì/nước dùng khi ăn',self.tables[p.table].slot%4)
                if len(p.meals)==p.size and all(m['eat_left']<=0 for m in p.meals):
                    self.review(p)
                    table = self.tables[p.table]
                    table.dirty += len(p.meals)
                    table.needs_wipe = True
                    table.soil += len(p.meals)
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
        data = {k: v for k, v in self.__dict__.items() if k not in ('rng', '_clock','sound_events','speech_events','player_cleaning')}
        data['parties'] = [asdict(p) for p in self.parties]
        data['bowls'] = [asdict(b) for b in self.bowls]
        data['tables'] = [asdict(t) for t in self.tables]
        data['version'] = 9
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        temp.replace(path)

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        version = data.pop('version')
        if version not in (2, 3, 4, 5, 6, 7, 8, 9):
            raise ValueError('Phiên bản lưu không phù hợp')
        if version == 8:
            from shutil import copy2
            backup=Path(path).with_suffix('.v8.bak')
            if not backup.exists():copy2(path,backup)
        if version == 7:
            from shutil import copy2
            backup=Path(path).with_suffix('.v7.bak')
            if not backup.exists():copy2(path,backup)
        if version == 6:
            from shutil import copy2
            backup=Path(path).with_suffix('.v6.bak')
            if not backup.exists():copy2(path,backup)
        if version == 5:
            from shutil import copy2
            backup=Path(path).with_suffix('.v5.bak')
            if not backup.exists():copy2(path,backup)
        if version == 4:
            from shutil import copy2
            backup=Path(path).with_suffix('.v4.bak')
            if not backup.exists():copy2(path,backup)
        if version == 3:
            from shutil import copy2
            backup=Path(path).with_suffix('.v3.bak')
            if not backup.exists():copy2(path,backup)
        obj = cls()
        for k, v in data.items():
            if k not in obj.__dict__ or k in ('rng', '_clock'):
                raise ValueError('Dữ liệu lưu không phù hợp')
            setattr(obj, k, v)
        obj.parties = [Party(**p) for p in data['parties']]
        if version<8:
            for party in obj.parties:
                party.entered=party.phase not in ('door','waiting','leaving')
                party.in_a_hurry=obj.rng.random()<.35 if party.phase=='door' else False
                if party.phase=='waiting':party.wait_number=obj.next_wait_number;obj.next_wait_number+=1
                previous=sum(party.choose_seconds);party.choose_seconds=[v*.5 for v in party.choose_seconds]
                party.buy_seconds=max(0,party.buy_seconds-previous+sum(party.choose_seconds))
        obj.player_cleaning=None
        obj.bowls = [Bowl(**b) for b in data['bowls']]
        obj.tables = [Table(**t) for t in data['tables']]
        if version == 2:
            from shutil import copy2
            backup=Path(path).with_suffix('.v2.bak')
            if not backup.exists():copy2(path,backup)
            obj.stock_value = {name: qty * LEGACY_COST.get(name,STOCK_COST[name]) for name, qty in obj.stock.items()}
            for i, t in enumerate(obj.tables):
                t.floor, t.slot = divmod(i, 6)
            obj.floors = max(1, (len(obj.tables)+5)//6)
            for party in obj.parties:
                party.recipes = [list(RECIPES[name]) for name in party.orders]
                party.prices = [{'Kake soba':35000,'Soba tôm':45000,'Soba bò':50000,'Soba trứng':42000}[name] for name in party.orders]
                if party.phase in ('seated', 'eating'):
                    party.seats = list(range(party.size))
        # Convert stored durations once; new legacy profiles already use the new scale.
        previous_scale = data.get('service_time_scale', 1.0)
        ratio = SERVICE_TIME_SCALE / previous_scale
        if ratio != 1:
            for party in obj.parties:
                old_choices = sum(party.choose_seconds)
                party.eat_seconds = [v*ratio for v in party.eat_seconds]
                party.choose_seconds = [v*ratio for v in party.choose_seconds]
                party.buy_seconds = max(0, party.buy_seconds-old_choices+sum(party.choose_seconds))
                if party.phase == 'buying':
                    # Preserve choice progress; payment time stays unchanged.
                    elapsed_choice = min(party.phase_time, old_choices)
                    party.phase_time = elapsed_choice*ratio + max(0,party.phase_time-old_choices)
                for meal in party.meals:
                    for key in ('eat_total','eat_left','spill_at'):
                        if meal.get(key,-1)>=0:meal[key]*=ratio
            if version>=4:
                obj.wash_left*=ratio
                obj.wipe_left*=ratio
        obj.service_time_scale = SERVICE_TIME_SCALE
        obj.reputation=max(5,obj.reputation)
        for name in STOCK_COST:
            obj.stock.setdefault(name,0);obj.stock_value.setdefault(name,0)
        for party in obj.parties:
            if not party.drinks:party.drinks=['']*party.size
            if not party.drinks_served:party.drinks_served=['']*party.size
        for party in obj.parties:
            obj.assign_personality(party)
            for i,meal in enumerate(party.meals):
                duration=party.eat_seconds[i]
                meal.setdefault('eat_total',duration)
                meal.setdefault('eat_left',duration*max(0,1-party.phase_time/35) if party.phase=='eating' else duration)
                meal.setdefault('wait',max(0,party.age-party.phase_time))
                meal.setdefault('spill_at',-1)
        if version<4:
            for spot in obj.dirt:obj.dirt_reasons[str(spot)]='Vết bẩn còn lại từ phiên bản trước'
            for t in obj.tables:t.soil=max(t.dirty,1 if t.needs_wipe else 0)
            if obj.washing:
                obj.wash_left=SERVICE_TIME_SCALE*(15+30*obj.washing)*min(1,obj.wash_left/(2+obj.washing))
        if len(obj.pots) != 6 or not 1 <= obj.floors <= 3 or not 1 <= len(obj.tables) <= 18 or obj.reputation < 0:
            raise ValueError('Dữ liệu lưu không hợp lệ')
        obj.migrate_staff()
        if version<9:obj.migrate_finance()
        return obj


def save_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'QuanSobaManual' / 'save-vnd.json'
