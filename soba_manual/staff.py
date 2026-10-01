"""Staff shifts and actual-action automation; no offline catch-up simulation."""
import calendar
from datetime import datetime, timedelta, date
from collections import Counter
from vn_calendar import holiday_name
from catalog import DRINKS

MIN_HOURLY = 25500
MIN_MONTHLY = 5310000
EMPLOYEE_INSURANCE = .105
EMPLOYER_INSURANCE = .215
INSURANCE_CAP = 50_600_000
NAMES = ['An','Bình','Chi','Dũng','Hà','Hải','Hương','Lan','Linh','Minh','Nam','Ngọc','Phúc','Sơn','Trang','Tuấn','Vy']


def income_tax(gross, insurance=0, dependents=0):
    taxable=max(0,gross-insurance-15_500_000-6_200_000*dependents)
    tax=0
    for width,rate in ((10_000_000,.05),(20_000_000,.10),(30_000_000,.20),(40_000_000,.30),(float('inf'),.35)):
        part=min(width,taxable);tax+=part*rate;taxable-=part
        if taxable<=0:break
    return round(tax)


def cycle_key(day):
    """Work from the 18th through the 17th is paid on the following 27th."""
    if day.day<=17:return day.replace(day=1).isoformat()[:7]
    nxt=(day.replace(day=28)+timedelta(days=4)).replace(day=1)
    return nxt.isoformat()[:7]


class StaffMixin:
    def init_staff(self):
        self.employees=[]
        self.candidates=[]
        self.next_employee=1
        self.staff_cooking={}
        self.payroll=[]
        self.background_enabled=False
        self.player_idle=False
        self.staff_auto_open=True
        self.staff_opened_shop=False
        self.leave_requested=''
        self.staff_calendar_date=''

    def applicants(self):
        if not self.candidates:
            for role in ('baito','contract'):
                for _ in range(2):
                    name=NAMES[self.rng.randrange(len(NAMES))]
                    self.candidates.append({'id':self.next_employee,'name':name,'role':role,
                        'wage':35000 if role=='baito' else 8_000_000,
                        'traits':[self.rng.choice(['Chăm','Lười']),self.rng.choice(['Cẩn thận','Hậu đậu']),self.rng.choice(['Nhanh','Chậm'])]})
                    self.next_employee+=1
        return self.candidates

    def hire(self, cid, wage=None, months=12):
        c=next((c for c in self.applicants() if c['id']==cid),None)
        if not c or len(self.employees)>=8:return False
        wage=c['wage'] if wage is None else wage
        if type(wage)!=int or wage<(MIN_HOURLY if c['role']=='baito' else MIN_MONTHLY):return False
        if months not in (3,6,12):return False
        today=self.now.date();until=(today.replace(day=1)+timedelta(days=32*months)).replace(day=1)
        # Exact calendar-month contract anniversary, including short months.
        index=today.year*12+today.month-1+months
        year,month=divmod(index,12);month+=1
        until=today.replace(year=year,month=month,day=min(today.day,calendar.monthrange(year,month)[1]))
        e=dict(c,wage=wage,hired=today.isoformat(),contract_until=until.isoformat(),
               shift_start=8*60,shift_hours=8,enabled=False,leaves={},leave_sent='',
               attendance={},paid_days=[],present=False,job=None,tasks=0,observed=[],
               x=700.,y=450.,floor=0,last_work_date='',status='Chưa cài ca')
        self.employees.append(e);self.candidates.remove(c)
        self.ensure_leave(e,today)
        self.note(f'Đã thuê {e["name"]} · {"Baito" if e["role"]=="baito" else "Hợp đồng"}. Cài ca và bật lịch làm việc.')
        return True

    def employee(self,eid):return next((e for e in self.employees if e['id']==eid),None)

    def set_shift(self,eid,start,hours,enabled=True):
        e=self.employee(eid)
        if not e or type(start)!=int or not 0<=start<1440 or type(hours)!=int or not 1<=hours<=12:return False
        if start+hours*60>1440:
            self.note('Ca làm phải kết thúc trong cùng ngày, chậm nhất 24:00.');return False
        e.update(shift_start=start,shift_hours=hours,enabled=bool(enabled))
        self.note(f'Ca {e["name"]}: {start//60:02}:{start%60:02}–{(start+hours*60)//60:02}:{(start+hours*60)%60:02}.')
        return True

    def ensure_leave(self,e,day):
        month=day.isoformat()[:7]
        if month not in e['leaves']:
            eligible=[date(day.year,day.month,d) for d in range(1,calendar.monthrange(day.year,day.month)[1]+1)
                      if date(day.year,day.month,d).weekday()<4 and not holiday_name(date(day.year,day.month,d))]
            picked=sorted(self.rng.sample(eligible,min(9,len(eligible))))
            e['leaves'][month]=[d.isoformat() for d in picked]
        return e['leaves'][month]

    def request_leave(self):
        self.leave_requested=self.now.date().isoformat()[:7]
        for e in self.employees:
            self.ensure_leave(e,self.now.date());e['leave_sent']=self.leave_requested
        self.note('Nhân viên đã gửi lịch nghỉ tháng '+self.leave_requested+'. Mỗi người chọn 9 ngày, không chọn thứ Sáu–CN hoặc ngày lễ.')

    def termination_fee(self,eid):
        e=self.employee(eid)
        return round(e['wage']*.5) if e and e['role']=='contract' and self.now.date().isoformat()<e['contract_until'] else 0

    def fire(self,eid):
        e=self.employee(eid)
        if not e:return False
        fee=self.termination_fee(eid)
        if e['present'] and self.open:
            self.note('Nhân viên đang làm: có thể cho nghỉ, công việc còn lại sẽ giao lại cho quán.')
        if fee and self.cash<fee:
            self.note('Không đủ tiền thanh toán khoản phạt chấm dứt hợp đồng.');return False
        if e['role']=='baito':
            for key in list(e['attendance']):self.pay_baito_day(e,key)
        else:
            # Immediate final settlement of all unpaid wages, including an unfinished cycle.
            cycles={cycle_key(date.fromisoformat(d)) for d in e['attendance']}
            for key in sorted(cycles):self.settle_contract(e,key,force=True)
        self.cash-=fee
        if fee:self.record('termination',fee)
        self.employees.remove(e)
        self.note(f'Đã cho {e["name"]} nghỉ. Phạt hợp đồng: {fee:,.0f} VND.')
        return True

    def pay_baito_day(self,e,key):
        if key not in e['attendance']:return
        row=e['attendance'][key]
        total=round(row['gross']);gross=total-row.get('paid_gross',0)
        if gross<=0:return
        hours=(row['seconds']-row.get('paid_seconds',0))/3600
        row['paid_gross']=total;row['paid_seconds']=row['seconds']
        # Daily short-term payment usually below the 2026 withholding threshold.
        tax=round(gross*.1) if gross>=5_000_000 else 0
        self.cash-=gross
        if key not in e['paid_days']:e['paid_days'].append(key)
        self.payroll.append(dict(employee=e['id'],name=e['name'],role='baito',period=key,paid=self.now.date().isoformat(),
                                 gross=gross,insurance=0,employer=0,tax=tax,net=gross-tax,hours=hours))
        self.note(f'Đã trả công {e["name"]} ngày {key}: {gross-tax:,.0f} VND (khấu trừ {tax:,.0f}).')

    def settle_contract(self,e,key,force=False):
        if key in e['paid_days']:return
        due=date.fromisoformat(key+'-27')
        if not force and self.now.date()<due:return
        rows=[v for d,v in e['attendance'].items() if cycle_key(date.fromisoformat(d))==key]
        if not rows:return
        gross=round(sum(r['gross'] for r in rows))
        insurance=round(sum(r['insurance'] for r in rows));employer=round(sum(r['employer'] for r in rows))
        # Overtime premium is exempt from PIT; ordinary hourly component is taxable.
        premium=sum(r.get('ot_premium',0) for r in rows)
        tax=income_tax(gross-premium,insurance)
        self.cash-=gross+employer;e['paid_days'].append(key)
        self.payroll.append(dict(employee=e['id'],name=e['name'],role='contract',period=key,paid=self.now.date().isoformat(),
                                 gross=gross,insurance=insurance,employer=employer,tax=tax,net=gross-insurance-tax,
                                 hours=sum(r['seconds'] for r in rows)/3600))
        self.note(f'Thanh toán kỳ {key} cho {e["name"]}: thực nhận {gross-insurance-tax:,.0f} VND.')

    def payroll_due(self,e):
        if e['role']=='baito':return round(sum(r['gross']-r.get('paid_gross',0) for r in e['attendance'].values()))
        paid=set(e['paid_days'])
        return round(sum(r['gross']+r.get('employer',0) for key,r in e['attendance'].items()
                         if (key if e['role']=='baito' else cycle_key(date.fromisoformat(key))) not in paid))

    def accrue_wages(self,e,dt,day):
        key=day.isoformat()
        row=e['attendance'].setdefault(key,dict(seconds=0.,gross=0.,insurance=0.,employer=0.,ot_premium=0.))
        old=row['seconds'];normal=min(dt,max(0,8*3600-old));overtime=dt-normal
        if e['role']=='baito':gross=e['wage']*dt/3600;premium=0;ins=emp=0
        else:
            hour=e['wage']/max(1,calendar.monthrange(day.year,day.month)[1]-9)/8
            rate=3 if holiday_name(day) else (2 if day.weekday()>=4 else 1.5)
            gross=hour*(normal+overtime*rate)/3600;premium=hour*overtime*(rate-1)/3600
            # Accrue contributions against the agreed base wage, excluding overtime.
            covered=min(e['wage'],INSURANCE_CAP)/max(1,calendar.monthrange(day.year,day.month)[1]-9)/8*normal/3600
            ins=covered*EMPLOYEE_INSURANCE;emp=covered*EMPLOYER_INSURANCE
        row['seconds']+=dt;row['gross']+=gross;row['insurance']+=ins;row['employer']+=emp;row['ot_premium']+=premium
        self.record('wages',gross);self.record('employer_insurance',emp)

    def update_staff(self,dt):
        day=self.now.date();key=day.isoformat();minute=self.minute
        for e in self.employees:
            leaves=self.ensure_leave(e,day)
            for past in e['attendance']:
                if e['role']=='baito' and past<key:self.pay_baito_day(e,past)
            if e['role']=='contract':
                for period in sorted({cycle_key(date.fromisoformat(d)) for d in e['attendance']}):self.settle_contract(e,period)
            scheduled=e['enabled'] and key not in leaves and e['shift_start']<=minute<e['shift_start']+e['shift_hours']*60
            was=e['present'];e['present']=scheduled
            if not scheduled:
                if was:
                    e['job']=None
                    if e['role']=='baito':self.pay_baito_day(e,key)
                    self.note(f'{e["name"]} kết ca.')
                e['status']='Ngày nghỉ' if key in leaves else ('Ngoài ca' if e['enabled'] else 'Chưa bật ca')
                continue
            if not was:self.note(f'{e["name"]} đến nhận ca.')
            self.accrue_wages(e,dt,day)
        active=[e for e in self.employees if e['present']]
        if active and self.staff_auto_open and not self.open and not self.closing:
            if self.open_shop():self.staff_opened_shop=True
        if self.staff_opened_shop and not active and self.open:
            self.closing=True
        if not self.open:return
        for e in active:
            if e['job']:
                job=e['job'];job['left']-=dt
                tx,ty,floor=job['target'];dx=tx-e['x'];dy=ty-e['y'];distance=(dx*dx+dy*dy)**.5
                if distance:e['x']+=dx*min(1,dt*100/distance);e['y']+=dy*min(1,dt*100/distance)
                e['floor']=floor
                if job['left']<=0:
                    e['job']=None;self.finish_staff_job(e,job)
            else:
                if 'Lười' in e['traits'] and self.rng.random()<.008:
                    e['job']={'action':['idle'],'left':self.rng.uniform(10,35),'target':[e['x'],e['y'],e['floor']]};e['status']='Đang nghỉ tay'
                    continue
                job=self.choose_staff_job(e,active)
                if job:
                    action,target,seconds=job
                    speed=.7 if 'Nhanh' in e['traits'] else 1.3
                    travel=((target[0]-e['x'])**2+(target[1]-e['y'])**2)**.5/130
                    e['job']={'action':list(action),'target':list(target),'left':(seconds+travel)*speed}
                    e['status']=self.job_label(action)
                else:e['status']='Chờ việc'
        # At the end of the last shift, nobody works unpaid. Clean restaurant may close.
        if self.closing:
            for p in list(self.parties):
                if p.phase in ('door','waiting'):self.respond(p.id,'decline')
            if self.staff_opened_shop and not any(p.phase!='leaving' for p in self.parties) and not self.bowls and not any(x is not None for x in self.pots):
                if not self.dirt and not self.sink and not self.washing and self.wipe_table<0 and not any(t.dirty or t.needs_wipe for t in self.tables):
                    if self.close_shop():self.staff_opened_shop=False

    @staticmethod
    def job_label(action):
        return {'door':'Đón khách','collect':'Nhận / đọc phiếu','seat':'Xếp bàn','start':'Cho mì vào nồi','lift':'Vớt mì',
                'prep':'Đưa mì vào quầy','top':'Thêm topping','serve':'Bưng mì','drink':'Bưng đồ uống','clear':'Bê bát bẩn',
                'wipe':'Lau bàn','wash':'Rửa bát','sweep':'Lau sàn','discard':'Đổ phần thừa','idle':'Nghỉ tay'}.get(action[0],'Làm việc')

    def reserved_action(self,action):
        return any(e['job'] and e['job']['action']==list(action) for e in self.employees)

    def choose_staff_job(self,e,active):
        from model import POT_POS,BOWL_POS,DIRT_POS
        def job(action,target,seconds):
            return None if self.reserved_action(action) else (action,target,seconds)
        def table_target(i):return (*self.table_position(i),self.tables[i].floor)
        has_floor=any(x['role']=='baito' for x in active)
        kitchen=e['role']=='contract'
        floor=e['role']=='baito' or not has_floor or self.player_idle
        if kitchen:
            # Lifting is always first priority to preserve the ten-second window.
            for key,order in list(self.staff_cooking.items()):
                pot=int(key);p=self.group(order['gid'])
                b=next((b for b in self.bowls if b.id==order.get('bid')),None)
                if not p or p.phase not in ('seated','eating') or order['index']<len(p.meals):
                    if b:return job(('discard',b.id),(*BOWL_POS[b.slot],0),2)
                    if self.pots[pot] is None:self.staff_cooking.pop(key,None)
                    continue
                if not b and self.pot_state(pot) in ('ready','mushy'):
                    if self.clean:return job(('lift',pot),(*POT_POS[pot],0),.2)
                elif b:
                    if b.stage=='lifted':
                        slot=next((i for i in range(6) if not any(x.stage=='prep' and x.slot==i for x in self.bowls)),None)
                        if slot is not None:return job(('prep',b.id,slot),(*BOWL_POS[slot],0),1)
                    else:
                        missing=Counter(p.recipes[order['index']])-Counter(b.toppings)
                        if missing:
                            name=next(iter(missing))
                            if self.stock[name]>0:return job(('top',b.id,name),(*BOWL_POS[b.slot],0),2)
                        else:
                            order['done']=True
                            if floor and order['index']==len(p.meals):return job(('serve',b.id,p.table,p.id),table_target(p.table),2)
            # Start several pots in parallel, only when a complete recipe remains in stock.
            planned={(x['gid'],x['index']) for x in self.staff_cooking.values()}
            planned|={(x['job']['action'][2],x['job']['action'][3]) for x in active if x['job'] and x['job']['action'][0]=='start'}
            for p in sorted(self.parties,key=lambda p:p.id):
                if p.phase!='seated':continue
                for idx in range(len(p.meals),p.size):
                    if (p.id,idx) in planned:continue
                    need=Counter(['Mì tươi',*p.recipes[idx]])
                    reserved=Counter()
                    for order in self.staff_cooking.values():
                        other=self.group(order['gid'])
                        if other:
                            bowl=next((b for b in self.bowls if b.id==order.get('bid')),None)
                            reserved+=Counter(other.recipes[order['index']])-Counter(bowl.toppings if bowl else [])
                    if not all(self.stock[n]-reserved[n]>=q for n,q in need.items()):continue
                    pot=next((i for i,v in enumerate(self.pots) if v is None and str(i) not in self.staff_cooking and not any(x['job'] and x['job']['action'][:2]==['start',i] for x in active) and not any(b.stage=='lifted' and b.slot==i for b in self.bowls)),None)
                    if pot is not None:return job(('start',pot,p.id,idx),(*POT_POS[pot],0),2)
            if self.sink and not self.washing and (self.clean<=2 or not has_floor):return job(('wash',), (965,320,0),2)
        if floor:
            for p in sorted(self.parties,key=lambda p:p.id):
                if p.phase in ('door','waiting'):
                    if self.closing or self.stock['Mì tươi']<p.size:return job(('door',p.id,'decline'),(p.x,p.y,0),2)
                    reserved_seats=sum(q.size for q in self.parties if q.phase in ('queue','buying','ticket','ready'))
                    free=sum(len(self.free_seats(i)) for i in range(len(self.tables)))
                    if self.can_fit(p.size) and free-reserved_seats>=p.size:return job(('door',p.id,'accept'),(p.x,p.y,0),2)
                    if p.phase=='door':return job(('door',p.id,'wait'),(p.x,p.y,0),2)
                if p.phase=='ticket':return job(('collect',p.id),(725,350,0),3)
                if p.phase=='ready':
                    table=next((i for i in range(len(self.tables)) if len(self.free_seats(i))>=p.size),None)
                    if table is not None:return job(('seat',p.id,table),table_target(table),2)
            for key,order in self.staff_cooking.items():
                p=self.group(order['gid']);b=next((b for b in self.bowls if b.id==order.get('bid')),None)
                if order.get('done') and b and p and order['index']==len(p.meals):return job(('serve',b.id,p.table,p.id),table_target(p.table),2)
            # Baito may carry correctly prepared bowls made manually as well.
            for p in self.parties:
                if p.phase=='seated' and len(p.meals)<p.size:
                    bowl=next((b for b in self.bowls if b.stage=='prep' and Counter(b.toppings)==Counter(p.recipes[len(p.meals)])),None)
                    if bowl:return job(('serve',bowl.id,p.table,p.id),table_target(p.table),2)
                if p.phase in ('seated','eating'):
                    for i,name in enumerate(p.drinks):
                        if name and p.drinks_served[i]!=name and self.stock[name]>0:return job(('drink',name,p.table,p.id),table_target(p.table),2)
            for i,t in enumerate(self.tables):
                if t.dirty:return job(('clear',i),table_target(i),3)
                if t.needs_wipe and self.wipe_table<0:return job(('wipe',i),table_target(i),1)
            if self.sink and not self.washing:return job(('wash',),(965,320,0),2)
            if self.dirt:
                spot=self.dirt[0];return job(('sweep',spot),(*DIRT_POS[spot%len(DIRT_POS)],spot//len(DIRT_POS)),15)
            if self.closing and not any(p.phase in ('seated','eating','ready','ticket','buying','queue') for p in self.parties):
                if self.bowls:return job(('discard',self.bowls[0].id),(1000,590,0),2)
                for i,age in enumerate(self.pots):
                    if age is not None:return job(('discard_pot',i),(*POT_POS[i],0),2)
        return None

    def finish_staff_job(self,e,job):
        action=job['action'];kind,*args=action
        if kind=='idle':return
        # Breakage has a concrete cause, destroys one owned bowl and dirties the floor.
        carrying=kind in ('serve','clear','prep')
        chance=.018 if 'Hậu đậu' in e['traits'] else .001
        if carrying and self.rng.random()<chance:
            broken=False
            if kind in ('serve','prep'):
                b=next((b for b in self.bowls if b.id==args[0]),None)
                if b:
                    self.bowls.remove(b);broken=True
                    for key,order in list(self.staff_cooking.items()):
                        if order.get('bid')==b.id:self.staff_cooking.pop(key,None)
            elif self.tables[args[0]].dirty:
                self.tables[args[0]].dirty-=1;broken=True
            if broken:
                self.dishes_owned=max(0,self.dishes_owned-1)
                self.mark_dirty(e['floor'],f'{e["name"]} làm rơi vỡ bát khi {self.job_label(action).lower()}')
                if 'Hậu đậu' not in e['observed']:e['observed'].append('Hậu đậu')
                return
        done=False
        if kind=='start':
            pot,gid,index=args;p=self.group(gid)
            if p and p.phase=='seated' and index>=len(p.meals) and (gid,index) not in {(o['gid'],o['index']) for o in self.staff_cooking.values()}:
                if self.start_pot(pot):self.staff_cooking[str(pot)]={'gid':gid,'index':index};done=True
        elif kind=='lift':
            if self.lift(args[0]):
                order=self.staff_cooking.get(str(args[0]))
                if order:order['bid']=self.bowls[-1].id
                done=True
        elif kind=='door':done=self.respond(*args)
        elif kind=='collect':
            done=self.collect(*args)
            p=self.group(args[0])
            if done and p:
                message=f'{e["name"]}: Phiếu nhóm {p.id}, '+', '.join(p.orders)+'. '+', '.join(d for d in p.drinks if d)
                self.note(message);self.speech_events.append(message)
        else:
            fn={'seat':self.seat,'prep':self.move_prep,'top':self.topping,'serve':self.serve,'drink':self.serve_drink,
                'clear':self.clear_table,'wipe':self.wipe,'wash':self.wash,'sweep':self.sweep,'discard':self.discard_bowl,'discard_pot':self.discard_pot}.get(kind)
            if fn:done=fn(*args)
        if done:
            e['tasks']+=1
            if e['tasks']>=10 and not e['observed']:e['observed'].append(e['traits'][0])
            if e['tasks']>=30 and e['traits'][2] not in e['observed']:e['observed'].append(e['traits'][2])
            if e['tasks']>=70 and e['traits'][1] not in e['observed']:e['observed'].append(e['traits'][1])
            if e['role']=='contract' and self.player_idle and any(x['present'] and x['role']=='baito' for x in self.employees) and e['tasks']%12==0:
                message=f'{e["name"]}: Baito ưu tiên bưng món và dọn bàn nhé, tôi lo bếp.'
                self.note(message);self.speech_events.append(message)
