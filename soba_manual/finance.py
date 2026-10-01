"""Game economy contracts and dated bills; these are simulated tariffs, not legal rates."""
import calendar
from datetime import date, timedelta

PROVIDERS = {
    'electricity': [('Điện An Phố', 3000, 'kWh'), ('Điện Minh Quang', 3400, 'kWh'), ('Điện Thành Đô', 3800, 'kWh')],
    'water': [('Nước Thanh Bình', 15000, 'm³'), ('Nước An Lành', 18000, 'm³'), ('Nước Đô Thị', 22000, 'm³')],
    'gas': [('Ga Bếp Việt', 38000, 'kg'), ('Ga Lửa Xanh', 42000, 'kg'), ('Ga Phố Mới', 46000, 'kg')],
}
STREETS = [('Phố nhỏ khu dân cư', 5_000_000), ('Phố thương mại', 10_000_000), ('Phố trung tâm', 18_000_000)]
TAX_RATE = .10
TAX_MONTHS = (6, 8, 10, 12)

def next_month(d):
    return (d.replace(day=28)+timedelta(days=4)).replace(day=1)

class FinanceMixin:
    def init_finance(self):
        today=self.now.date()
        self.meters={k:dict(provider=0,reading=0.,billed=0.,cost=0.,billed_cost=0.,
                           close_day=self.rng.randint(1,28),next_close='') for k in PROVIDERS}
        for m in self.meters.values():
            closing=today.replace(day=m['close_day'])
            if closing<=today:closing=next_month(today).replace(day=m['close_day'])
            m['next_close']=closing.isoformat()
        self.bills=[];self.next_bill=1;self.finance_cursor=today.isoformat()
        self.tax_assessments={};self.lease=None

    def invoice(self,kind,label,amount,issued,due,**details):
        b=dict(id=self.next_bill,kind=kind,label=label,amount=round(amount),issued=issued.isoformat(),
               due=due.isoformat(),paid=round(amount)==0,paid_on=issued.isoformat() if round(amount)==0 else '',reminded='',**details)
        self.next_bill+=1;self.bills.append(b)
        self.note(f'Hóa đơn {label}: {b["amount"]:,} VND; hạn {due:%d/%m/%Y}.')
        return b

    def use_utility(self,kind,quantity):
        m=self.meters[kind];rate=PROVIDERS[kind][m['provider']][1]
        cost=quantity*rate;m['reading']+=quantity;m['cost']+=cost
        self.record(kind,cost)

    def close_meter(self,kind,issued):
        m=self.meters[kind];name,rate,unit=PROVIDERS[kind][m['provider']]
        self.invoice(kind,name,m['cost']-m['billed_cost'],issued,issued+timedelta(days=7),
                     start=m['billed'],end=m['reading'],quantity=m['reading']-m['billed'],rate=rate,unit=unit)
        m['billed']=m['reading'];m['billed_cost']=m['cost']

    def change_provider(self,kind,index):
        if self.open or kind not in PROVIDERS or index not in range(len(PROVIDERS[kind])):return False
        self.process_finance();m=self.meters[kind]
        if m['provider']==index:return False
        if m['cost']>m['billed_cost']:self.close_meter(kind,self.now.date())
        m['provider']=index
        self.note('Đã chọn '+PROVIDERS[kind][index][0]+'. Giá mới chỉ áp dụng từ lúc đổi.')
        return True

    def sign_lease(self,index):
        if self.open or self.lease is not None or index not in range(len(STREETS)):return False
        today=self.now.date();name,rent=STREETS[index]
        self.lease=dict(street=index,signed=today.isoformat(),next_rent=next_month(today).isoformat())
        # First partial month, including the signing day. Later months charge the full agreed rent.
        days=calendar.monthrange(today.year,today.month)[1]
        amount=round(rent*(days-today.day+1)/days)
        self.record('rent',amount)
        self.invoice('rent','Thuê '+name,amount,today,today+timedelta(days=7))
        return True

    def assess_tax(self,year,issued):
        key=str(year)
        if key in self.tax_assessments:return
        # Profit before shop income tax. Refunded revenue, consumed stock and all operating costs count once.
        row=self.totals('year').get(str(year-1),{})
        base=max(0,row.get('profit',0)+row.get('shop_tax',0))
        amount=round(base*TAX_RATE)
        self.tax_assessments[key]=dict(source_year=year-1,profit=base,rate=TAX_RATE,total=amount)
        for i,month in enumerate(TAX_MONTHS):
            part=amount//4+(1 if i<amount%4 else 0)
            self.invoice('shop_tax',f'Thuế năm {year-1} · kỳ {i+1}/4',part,issued,date(year,month,20),source_year=year-1)
        # Accrue the annual expense on assessment, never again on payment.
        self.ledger.setdefault(issued.isoformat(),dict(revenue=0,ingredients=0,electricity=0,water=0,gas=0))['shop_tax']=amount

    def process_finance(self):
        today=self.now.date()
        for kind,m in self.meters.items():
            closing=date.fromisoformat(m['next_close'])
            if closing<=today:
                self.close_meter(kind,closing)
                # Closed application produces no utility usage. Skip empty missed cycles.
                while closing<=today:closing=next_month(closing).replace(day=m['close_day'])
                m['next_close']=closing.isoformat()
        if self.lease:
            due=date.fromisoformat(self.lease['next_rent'])
            while due<=today:
                name,rent=STREETS[self.lease['street']]
                row=self.ledger.setdefault(due.isoformat(),dict(revenue=0,ingredients=0,electricity=0,water=0,gas=0))
                row['rent']=row.get('rent',0)+rent
                self.invoice('rent','Thuê '+name,rent,due,due+timedelta(days=7));due=next_month(due)
            self.lease['next_rent']=due.isoformat()
        start=date.fromisoformat(self.finance_cursor)
        for year in range(start.year,today.year+1):
            issued=max(start,date(year,1,1))
            self.assess_tax(year,issued)
        self.finance_cursor=max(start,today).isoformat()
        for b in self.bills:
            if not b['paid'] and b['amount'] and b['due']<=today.isoformat() and b['reminded']!=today.isoformat():
                b['reminded']=today.isoformat();self.note(f'Đến hạn / quá hạn: {b["label"]}, {b["amount"]:,} VND. Vào Chi phí để thanh toán.')

    def pay_bill(self,bid):
        self.process_finance()
        b=next((b for b in self.bills if b['id']==bid),None)
        if not b or b['paid'] or self.cash<b['amount']:return False
        self.cash-=b['amount'];b['paid']=True;b['paid_on']=self.now.date().isoformat()
        self.record('bills_paid',b['amount']);self.note('Đã thanh toán '+b['label']+'.')
        return True

    def migrate_finance(self):
        # Past utility expenses remain in history; only their unpaid portion is invoiced.
        unpaid=sum(round(r.get('electricity',0))+r.get('water',0)+r.get('gas',0)-r.get('utility_paid',0) for r in self.ledger.values())
        if unpaid>0:self.invoice('legacy','Điện nước ga còn thiếu từ bản cũ',unpaid,self.now.date(),self.now.date()+timedelta(days=7))
        # Existing businesses retain their current venue, without retroactive rent.
        if self.open or self.ledger:
            self.lease=dict(street=0,signed=self.now.date().isoformat(),next_rent=next_month(self.now.date()).isoformat())
