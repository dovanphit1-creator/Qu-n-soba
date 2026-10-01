"""Staff shifts and actual-action automation; no offline catch-up simulation."""
import calendar
from datetime import datetime, timedelta, date
from collections import Counter
from vn_calendar import holiday_name
from catalog import DRINKS
from shifts import ShiftMixin

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


class StaffMixin(ShiftMixin):
    def init_staff(self):
        self.init_shifts()
        self.employees=[]
        self.candidates=[]
        self.next_employee=1
        self.staff_cooking={}
        self.payroll=[]
        self.staff_purchases=[]
        self.staff_reports=[]
        self.staff_shutdown_date=""
        self.background_enabled=False
        self.player_idle=False
        self.staff_auto_open=True
        self.staff_opened_shop=False
        self.leave_requested=''
        self.staff_calendar_date=''
        self.recruitment_posted=False
        self.recruitment_round=0
        self.coverage_start=8*60
        self.coverage_end=18*60
        self.day_decisions={}
        self.cover_invites=[]
        self.clock_events=[]

    def post_recruitment(self):
        if self.candidates:
            self.note('Bài tuyển đang có ứng viên. Hãy xử lý CV trước khi đăng đợt mới.');return False
        self.recruitment_posted=True;self.recruitment_round+=1
        for role in ('baito','contract'):
            for _ in range(2):
                traits=[self.rng.choice(['Chăm','Lười']),self.rng.choice(['Cẩn thận','Hậu đậu']),self.rng.choice(['Nhanh','Chậm'])]
                claims=list(traits) if self.rng.random()<.4 else ['Chăm','Cẩn thận','Nhanh']
                self.candidates.append({'id':self.next_employee,'name':NAMES[self.rng.randrange(len(NAMES))],
                    'birth_year':self.now.year-self.rng.randint(19,45),'hometown':self.rng.choice(['Hà Nội','Đà Nẵng','Huế','Nghệ An','TP. Hồ Chí Minh','Cần Thơ','Hải Phòng','Bình Định']),
                    'cv_traits':claims,'role':role,'wage':self.rng.choice([30000,35000,40000,45000,50000]) if role=='baito' else self.rng.choice([6500000,8000000,9500000,11000000]),'traits':traits})
                self.assign_cv_shift(self.candidates[-1])
                self.next_employee+=1
        self.note('Đã đăng bài tuyển. Có 4 CV ứng tuyển; tính cách tự khai cần kiểm chứng khi làm.');return True

    def applicants(self):
        return self.candidates

    def dismiss_applicant(self,cid):
        c=next((c for c in self.candidates if c['id']==cid),None)
        if not c:return False
        self.candidates.remove(c);return True

    def migrate_staff(self):
        # Keep wages, accrued attendance, hidden traits and progress from 1.2.
        self.recruitment_posted=bool(self.candidates) or self.recruitment_posted
        for c in self.candidates:
            c.setdefault('birth_year',self.now.year-25);c.setdefault('hometown','Hà Nội');c.setdefault('cv_traits',['Chăm','Cẩn thận'])
        for e in self.employees:
            e.setdefault('agreed_wage',e['wage']);e['wage']=e['agreed_wage']
            e.setdefault('birth_year',self.now.year-25);e.setdefault('hometown','Hà Nội');e.setdefault('cv_traits',['Chăm','Cẩn thận'])
            e.setdefault('overtime_hours',max(0,e['shift_hours']-8) if e['role']=='contract' else 0)
            if e['role']=='contract':
                e['shift_hours']=8
                e['shift_start']=min(e['shift_start'],int(1440-510-e['overtime_hours']*60))
            e.setdefault('plans',{});e.setdefault('clocked_in',False);e.setdefault('clock_mode','');e.setdefault('clock_date','')
            e.setdefault('cover_days',{});e.setdefault('announced_plan','');e.setdefault('kitchen_support',True);e.setdefault('shortage_policy',self.rng.choice(['restock','close']))

        self.migrate_shifts()

    def hire(self, cid, wage=None, months=12):
        c=next((c for c in self.applicants() if c['id']==cid),None)
        if not c or len(self.employees)>=8:return False
        if wage is not None and wage!=c['wage']:
            self.note('Lương mong muốn trong CV là cố định. Chỉ có thể đồng ý hoặc từ chối.');return False
        wage=c['wage']
        if type(wage)!=int or wage<(MIN_HOURLY if c['role']=='baito' else MIN_MONTHLY):return False
        if c['role']=='contract' and not c.get('requested_shift'):
            self.note('Chưa có ca phù hợp trong CV; hãy tạo ca đủ 8h làm và nghỉ trước khi đăng tuyển.');return False
        if months not in (3,6,12):return False
        today=self.now.date();until=(today.replace(day=1)+timedelta(days=32*months)).replace(day=1)
        # Exact calendar-month contract anniversary, including short months.
        index=today.year*12+today.month-1+months
        year,month=divmod(index,12);month+=1
        until=today.replace(year=year,month=month,day=min(today.day,calendar.monthrange(year,month)[1]))
        e=dict(c,wage=wage,agreed_wage=wage,hired=today.isoformat(),contract_until=until.isoformat(),
               shift_start=8*60,shift_hours=8,enabled=False,leaves={},leave_sent='',
               attendance={},paid_days=[],present=False,job=None,tasks=0,observed=[],
               x=700.,y=450.,floor=0,last_work_date='',status='Chưa bật lịch',
               overtime_hours=0,plans={},clocked_in=False,clock_mode='',clock_date='',cover_days={},announced_plan='',kitchen_support=True,shortage_policy=self.rng.choice(['restock','close']))
        e.update(self_select=True,contract_breaks={})
        if e['role']=='contract':
            e['agreed_shift']=dict(c['requested_shift']);e['shift_start']=e['agreed_shift']['start']
        self.employees.append(e);self.candidates.remove(c)
        self.ensure_leave(e,today)
        self.note(f'Đã thuê {e["name"]} · {"Baito" if e["role"]=="baito" else "Hợp đồng"}. Xem ca đã chọn và bật lịch làm việc.')
        return True

    def employee(self,eid):return next((e for e in self.employees if e['id']==eid),None)

    def shift_end(self,e):
        return e['agreed_shift']['end']+e.get('overtime_hours',0)*60 if e['role']=='contract' else e['shift_start']+e['shift_hours']*60

    def set_shift(self,eid,start,hours,enabled=True):
        e=self.employee(eid)
        if not e or type(start)!=int or not 0<=start<1440 or type(hours)!=int:return False
        if e['role']=='contract' and (hours!=8 or start!=e['agreed_shift']['start']):
            self.note('Ca chính thức đã chốt trong CV, không thể đổi sau tuyển. Đặt tăng ca riêng.');return False
        if not 1<=hours<=12:return False
        end=self.shift_end(e) if e['role']=='contract' else start+hours*60
        if end>1440:
            self.note('Ca gồm giải lao / tăng ca phải kết thúc chậm nhất 24:00.');return False
        if e['role']=='baito':e['self_select']=False
        e.update(shift_start=start,shift_hours=hours,enabled=bool(enabled))
        e['plans'].pop(self.now.date().isoformat(),None)
        self.note(f'Ca {e["name"]}: {start//60:02}:{start%60:02}–{end//60:02}:{end%60:02}.'+(' 8h làm và một lần nghỉ giữa ca.' if e['role']=='contract' else ' Lương theo chấm công thực tế.'))
        return True

    def set_overtime(self,eid,hours):
        e=self.employee(eid)
        if not e or e['role']!='contract' or type(hours)!=int or not 0<=hours<=4:return False
        if e['agreed_shift']['end']+hours*60>1440:return False
        e['overtime_hours']=hours;e['plans'].pop(self.now.date().isoformat(),None)
        self.note(f'{e["name"]}: tăng ca {hours}h, phải chấm máy vào/ra tăng ca.');return True

    def clock_event(self,e,event,at,mode):
        row=dict(employee=e['id'],name=e['name'],event=event,at=at.isoformat(),mode=mode)
        if self.clock_events and self.clock_events[-1]==row:return
        self.clock_events.append(row);self.clock_events=self.clock_events[-500:]
        e['x'],e['y'],e['floor']=675.,305.,0
        self.note(f'Máy chấm công · {e["name"]} · {event} · {at:%H:%M:%S}')

    def day_plan(self,e,day):
        key=day.isoformat()
        if key in e['plans']:return self.apply_day_release(e['plans'][key],key)
        cover=e['cover_days'].get(key)
        eligible=self.day_decisions.get(key)!='closed' and (bool(cover) or (e['enabled'] and key not in self.ensure_leave(e,day)))
        start=cover['start'] if cover else e['shift_start']
        plan=self.make_shift_plan(e,day,cover,eligible)
        e['plans'][key]=plan
        # Bound plans; attendance and all actual clock entries remain separate.
        for old in sorted(e['plans'])[:-62]:e['plans'].pop(old,None)
        return self.apply_day_release(plan,key)

    def apply_day_release(self,plan,key):
        release=next((r for r in reversed(self.staff_reports) if r.get('reason')=='staff_released' and r['date']==key),None)
        if release and not plan.get('released_at'):
            at=datetime.fromisoformat(release['at'])
            minute=at.hour*60+at.minute+at.second/60+at.microsecond/60_000_000
            plan['released_at']=release['at']
            plan['segments']=[[start,min(stop,minute),mode] for start,stop,mode in plan['segments'] if start<minute]
        return plan

    def clock_state(self,e,now):
        plan=self.day_plan(e,now.date());minute=now.hour*60+now.minute+now.second/60+now.microsecond/60_000_000
        segment=next((s for s in plan['segments'] if s[0]<=minute<s[1]),None)
        mode=segment[2] if segment else ''
        if e['clock_mode']!=mode or e['clock_date']!=now.date().isoformat():
            if e['clock_mode'] in ('baito','overtime'):
                self.clock_event(e,'Chốt công',now,e['clock_mode'])
            if mode in ('baito','overtime'):self.clock_event(e,'Điểm danh' if mode=='baito' else 'Vào tăng ca',now,mode)
            if e['clock_mode']=='baito':self.pay_baito_day(e,e['clock_date'])
            e['clock_mode']=mode;e['clock_date']=now.date().isoformat();e['clocked_in']=mode in ('baito','overtime')
        if e['role']=='baito' and plan['late'] and mode and e['announced_plan']!=now.date().isoformat():
            self.note(f'{e["name"]} đến muộn {plan["late"]} phút. Chỉ trả từ lúc điểm danh.');e['announced_plan']=now.date().isoformat()
        if not mode:
            if plan.get('released_at') and now>=datetime.fromisoformat(plan['released_at']):
                return False,'Đã nghỉ hôm nay · quán đóng sớm'
            if plan['absence'] and plan['start']<=minute<plan['end']:return False,'Nghỉ đột xuất'
            if plan['late'] and plan['start']<=minute<plan['start']+plan['late']:return False,'Chưa tới / đến muộn'
            if plan['segments'] and plan['segments'][0][0]<=minute<plan['segments'][-1][1]:return False,'Giải lao · không tính công'
            if plan['early'] and plan['end']-plan['early']<=minute<plan['end']:return False,'Đã về sớm'
            return False,'Ngày nghỉ' if now.date().isoformat() in self.ensure_leave(e,now.date()) else ('Ngoài ca' if e['enabled'] else 'Chưa bật ca')
        return True,'Tăng ca' if mode=='overtime' else 'Đang làm'

    def work_overlap(self,e,begin,end):
        total=0.;day=begin.date()
        self.clock_state(e,begin)
        while day<=end.date():
            base=datetime.combine(day,datetime.min.time(),tzinfo=end.tzinfo)
            for start,stop,mode in self.day_plan(e,day)['segments']:
                segment_start=base+timedelta(minutes=start);segment_end=base+timedelta(minutes=stop)
                left=max(begin,segment_start);right=min(end,segment_end)
                if right<=left:continue
                self.clock_state(e,left)
                seconds=(right-left).total_seconds()
                self.accrue_wages(e,seconds,day,overtime=(mode=='overtime'))
                total+=seconds
                self.clock_state(e,right)
            day+=timedelta(days=1)
        return total

    def release_staff_day(self,at):
        """Finish today's actual work; preserve tomorrow's shifts and signed CVs."""
        key=at.date().isoformat()
        first=not any(r.get('reason')=='staff_released' and r['date']==key for r in self.staff_reports)
        if first:self.staff_reports.append({'date':key,'at':at.isoformat(),'reason':'staff_released','text':'Quán đóng sớm: đã chốt công, kết thúc các ca còn lại và cho nhân viên nghỉ hôm nay.'})
        for e in self.employees:
            plan=self.day_plan(e,at.date())
            if first:self.note(f'{e["name"]}: đã chốt ca và về nghỉ vì quán đóng sớm hôm nay.')
            self.clock_state(e,at)
            e['present']=False;e['job']=None;e['status']='Đã nghỉ hôm nay · quán đóng sớm'

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
        gaps=self.coverage_report()
        self.note(f'Đã nhận đủ lịch nghỉ. Có {len(gaps)} ngày / vị trí thiếu người. Xem tab Thiếu người.')
        self.note('Nhân viên đã gửi lịch nghỉ tháng '+self.leave_requested+'. Mỗi người chọn 9 ngày, không chọn thứ Sáu–CN hoặc ngày lễ.')

    def coverage_report(self):
        month=self.now.date().isoformat()[:7]
        if self.leave_requested!=month or any(e['leave_sent']!=month for e in self.employees):return []
        rows=[]
        for d in range(1,calendar.monthrange(self.now.year,self.now.month)[1]+1):
            day=date(self.now.year,self.now.month,d);key=day.isoformat()
            if day<self.now.date() or self.day_decisions.get(key)=='closed':continue
            for role,label in (('floor','Horu'),('kitchen','Bếp')):
                intervals=[]
                for e in self.employees:
                    cover=e['cover_days'].get(key)
                    primary=cover['position'] if cover else ('floor' if e['role']=='baito' else 'kitchen')
                    if primary!=role:continue
                    if cover or (e['enabled'] and key not in self.ensure_leave(e,day)):
                        intervals.extend((a,b) for a,b,mode in self.day_plan(e,day)['segments'])
                cursor=self.coverage_start;gaps=[]
                for left,right in sorted(intervals):
                    if right<=cursor or left>=self.coverage_end:continue
                    if left>cursor:gaps.append([cursor,min(left,self.coverage_end)])
                    cursor=max(cursor,min(right,self.coverage_end))
                if cursor<self.coverage_end:gaps.append([cursor,self.coverage_end])
                if gaps:rows.append(dict(date=key,position=role,label=label,gaps=gaps,decision=self.day_decisions.get(key,'')))
        return rows

    def invite_cover(self,eid,key,position,start,hours):
        e=self.employee(eid)
        try:day=date.fromisoformat(key)
        except (ValueError,TypeError):return False
        if not e or e['role']!='baito' or day<self.now.date() or position not in ('floor','kitchen'):return False
        if type(start)!=int or type(hours)!=int or not 0<=start<1440 or not 1<=hours<=12 or start+hours*60>1440:return False
        if any(r['employee']==eid and r['date']==key for r in self.cover_invites):
            self.note('Baito này đã trả lời lời mời cho ngày đó. Hãy mời người khác.');return False
        if key in e['cover_days'] or (e['enabled'] and key not in self.ensure_leave(e,day)):
            self.note('Baito đã có ca ngày này; không xếp trùng ca.');return False
        accepted=self.rng.random()<(.45 if 'Lười' in e['traits'] else .8)
        self.cover_invites.append(dict(employee=eid,name=e['name'],date=key,position=position,accepted=accepted))
        if accepted:
            e['cover_days'][key]=dict(start=start,hours=hours,position=position)
            e['plans'].pop(key,None)
        self.note(f'{e["name"]} '+('đồng ý' if accepted else 'từ chối')+f' làm thay {key} tại '+('bếp' if position=='kitchen' else 'horu')+'.')
        return accepted

    def decide_day(self,key,decision):
        try:day=date.fromisoformat(key)
        except (ValueError,TypeError):return False
        if day<self.now.date() or decision not in ('player','closed','normal'):return False
        if decision=='normal':self.day_decisions.pop(key,None)
        else:self.day_decisions[key]=decision
        for e in self.employees:e['plans'].pop(key,None)
        if day==self.now.date() and decision=='closed' and self.open:self.closing=True
        self.note(key+': '+{'player':'Chủ quán tự làm phần thiếu; mở quán thủ công.','closed':'Nghỉ kinh doanh.','normal':'Theo lịch nhân viên.'}[decision]);return True

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
        from operations import reimburse
        reimburse(self,e,'',force=True)
        self.employees.remove(e)
        self.note(f'Đã cho {e["name"]} nghỉ. Phạt hợp đồng: {fee:,.0f} VND.')
        return True

    def pay_baito_day(self,e,key):
        if key not in e['attendance']:return
        row=e['attendance'][key]
        total=round(row['gross']);gross=total-row.get('paid_gross',0)
        from operations import reimburse
        advance=reimburse(self,e,key)
        if gross<=0 and not advance:return
        hours=(row['seconds']-row.get('paid_seconds',0))/3600
        row['paid_gross']=total;row['paid_seconds']=row['seconds']
        # Daily short-term payment usually below the 2026 withholding threshold.
        tax=round(gross*.1) if gross>=5_000_000 else 0
        self.cash-=gross
        if key not in e['paid_days']:e['paid_days'].append(key)
        self.payroll.append(dict(employee=e['id'],name=e['name'],role='baito',period=key,paid=self.now.date().isoformat(),
                                 gross=gross,insurance=0,employer=0,tax=tax,net=gross-tax+advance,hours=hours,reimbursement=advance))
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
        from operations import reimburse
        advance=reimburse(self,e,key)
        self.cash-=gross+employer;e['paid_days'].append(key)
        self.payroll.append(dict(employee=e['id'],name=e['name'],role='contract',period=key,paid=self.now.date().isoformat(),
                                 gross=gross,insurance=insurance,employer=employer,tax=tax,net=gross-insurance-tax+advance,reimbursement=advance,
                                 hours=sum(r['seconds'] for r in rows)/3600))
        self.note(f'Thanh toán kỳ {key} cho {e["name"]}: thực nhận {gross-insurance-tax:,.0f} VND.')

    def payroll_due(self,e):
        if e['role']=='baito':return round(sum(r['gross']-r.get('paid_gross',0) for r in e['attendance'].values()))
        paid=set(e['paid_days'])
        return round(sum(r['gross']+r.get('employer',0) for key,r in e['attendance'].items()
                         if (key if e['role']=='baito' else cycle_key(date.fromisoformat(key))) not in paid))

    def accrue_wages(self,e,dt,day,overtime=None):
        key=day.isoformat()
        row=e['attendance'].setdefault(key,dict(seconds=0.,gross=0.,insurance=0.,employer=0.,ot_premium=0.))
        old=row['seconds'];normal=(0 if overtime else dt) if overtime is not None else min(dt,max(0,8*3600-old));overtime=dt-normal
        e['wage']=e['agreed_wage']
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
        now=self.now;day=now.date();key=day.isoformat()
        # Recover already-closed 1.7.1 saves before accounting for this frame.
        if not self.open and self.staff_shutdown_date==key and any(r.get('reason')=='stock_shutdown' and r['date']==key for r in self.staff_reports):
            self.release_staff_day(max(datetime.combine(day,datetime.min.time(),tzinfo=now.tzinfo),now-timedelta(seconds=dt)))
        for e in self.employees:
            self.ensure_leave(e,day)
            # Only elapsed running time is paid. No wages for time the program was closed.
            if dt:self.work_overlap(e,now-timedelta(seconds=dt),now)
            for past in list(e['attendance']):
                if e['role']=='baito' and past<key:self.pay_baito_day(e,past)
            if e['role']=='contract':
                for period in sorted({cycle_key(date.fromisoformat(d)) for d in e['attendance']}):self.settle_contract(e,period)
            was=e['present'];scheduled,status=self.clock_state(e,now)
            if self.day_decisions.get(key)=='closed':scheduled=False;status='Quán nghỉ hôm nay'
            e['present']=scheduled
            if not scheduled:
                if was:
                    e['job']=None
                    if e['role']=='baito':self.pay_baito_day(e,key)
                    self.note(f'{e["name"]}: {status}.')
                e['status']=status
                continue
            if not was:self.note(f'{e["name"]} đến nhận việc.')
        active=[e for e in self.employees if e['present']]
        if active and not self.open:
            reason=self.opening_blocker(automatic=True)
            if not reason:
                if self.open_shop():self.staff_opened_shop=True
            else:
                for e in active:
                    status='Chờ mở quán: '+reason
                    if e['status']!=status:
                        e['status']=status
                        self.note(e['name']+': '+status)
        more_today=any(any(stop>self.minute for start,stop,mode in self.day_plan(e,day)['segments']) for e in self.employees)
        if self.staff_opened_shop and not active and not more_today and self.open:
            self.closing=True
        if not self.open:return
        from operations import manage_shortage
        manage_shortage(self,active)
        if self.closing and self.staff_shutdown_date==key:
            from operations import refund_unservable
            refund_unservable(self)
        for e in active:
            if e['job']:
                job=e['job'];job['left']-=dt
                tx,ty,floor=job['target'];dx=tx-e['x'];dy=ty-e['y'];distance=(dx*dx+dy*dy)**.5
                if distance:e['x']+=dx*min(1,dt*100/distance);e['y']+=dy*min(1,dt*100/distance)
                e['floor']=floor
                if job['left']<=0:
                    e['job']=None;self.finish_staff_job(e,job)
            else:
                job=self.choose_staff_job(e,active)
                if job:
                    action,target,seconds=job
                    speed=(.7 if 'Nhanh' in e['traits'] else 1.3)*(1.15 if 'Lười' in e['traits'] else 1)
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
                    if self.close_shop(automatic=True):
                        self.staff_opened_shop=False
                        row=self.last_report;stars=row.get('average_stars')
                        score=f'{stars:.2f}/5' if stars is not None else 'chưa có'
                        self.staff_reports.append({'date':key,'text':f'Đã dọn sạch và đóng quán. {row.get("customers",0)} khách, sao TB {score}; lợi nhuận {row["profit"]:,.0f} VND.'})

    @staticmethod
    def job_label(action):
        return {'door':'Đón khách','collect':'Nhận / đọc phiếu','seat':'Xếp bàn','start':'Cho mì vào nồi','lift':'Vớt mì',
                'prep':'Đưa mì vào quầy','top':'Thêm topping','serve':'Bưng mì','drink':'Bưng đồ uống','clear':'Bê bát bẩn',
                'wipe':'Lau bàn','wash':'Rửa bát','sweep':'Lau sàn','discard':'Đổ phần thừa','shop':'Đi mua nguyên liệu','clean_wait':'Đang dọn dẹp','idle':'Nghỉ tay'}.get(action[0],'Làm việc')

    def reserved_action(self,action):
        return any(e['job'] and e['job']['action']==list(action) for e in self.employees)

    def set_kitchen_support(self,eid,enabled):
        e=self.employee(eid)
        if not e or e['role']!='baito' or type(enabled)!=bool:return False
        e['kitchen_support']=enabled
        self.note(f'{e["name"]}: hỗ trợ toàn bộ bếp '+('BẬT' if enabled else 'TẮT')+'. Công việc đang làm sẽ hoàn thành trước khi đổi.')
        return True

    def choose_staff_job(self,e,active):
        from model import POT_POS,BOWL_POS,DIRT_POS
        def job(action,target,seconds):
            return None if self.reserved_action(action) else (action,target,seconds)
        def table_target(i):return (*self.table_position(i),self.tables[i].floor)
        has_floor=any(x['role']=='baito' for x in active)
        cover=e['cover_days'].get(self.now.date().isoformat(),{})
        primary=cover.get('position','floor' if e['role']=='baito' else 'kitchen')
        def position(worker):
            return worker['cover_days'].get(self.now.date().isoformat(),{}).get('position','floor' if worker['role']=='baito' else 'kitchen')
        def needs_help(where):
            peers=[x for x in active if x['id']!=e['id'] and position(x)==where]
            if not peers:return True
            if any(not x['job'] for x in peers):return False
            if where=='kitchen':backlog=sum(p.size-len(p.meals) for p in self.parties if p.phase=='seated')
            else:backlog=sum(p.phase in ('door','waiting','ticket','ready') for p in self.parties)+sum(t.dirty>0 or t.needs_wipe for t in self.tables)+len(self.dirt)+bool(self.sink)+sum(bool(o.get('done')) for o in self.staff_cooking.values())
            return backlog>len(peers)
        kitchen=primary=='kitchen' or (e.get('kitchen_support',True) and needs_help('kitchen'))
        floor=primary=='floor' or needs_help('floor')
        def cleanup_job(kind,owner,left,target):
            if owner==e['id'] or not self.cleanup_active(kind,owner):
                setattr(self,kind+'_owner',e['id'])
                return job(('clean_wait',kind),target,max(.1,left))
            return None
        def kitchen_job():
            # Lifting is always first priority to preserve the ten-second window.
            for key,order in list(self.staff_cooking.items()):
                pot=int(key);p=self.group(order['gid'])
                b=next((b for b in self.bowls if b.id==order.get('bid')),None)
                if not p or p.phase not in ('seated','eating') or order['index']<len(p.meals):
                    if b:yield job(('discard',b.id),(*BOWL_POS[b.slot],0),2)
                    if self.pots[pot] is None:self.staff_cooking.pop(key,None)
                    continue
                if not b and self.pot_state(pot) in ('ready','mushy'):
                    if self.clean:yield job(('lift',pot),(*POT_POS[pot],0),.2)
                elif b:
                    if b.stage=='lifted':
                        slot=next((i for i in range(6) if not any(x.stage=='prep' and x.slot==i for x in self.bowls)),None)
                        if slot is not None:yield job(('prep',b.id,slot),(*BOWL_POS[slot],0),1)
                    else:
                        missing=Counter(p.recipes[order['index']])-Counter(b.toppings)
                        if missing:
                            name=next(iter(missing))
                            if self.stock[name]>0:yield job(('top',b.id,name),(*BOWL_POS[b.slot],0),2)
                        else:
                            order['done']=True
                            if floor and order['index']==len(p.meals):yield job(('serve',b.id,p.table,p.id),table_target(p.table),2)
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
                    if pot is not None:yield job(('start',pot,p.id,idx),(*POT_POS[pot],0),2)
            if self.sink and not self.washing and (self.clean<=2 or not has_floor):yield job(('wash',), (965,320,0),2)
            return None

        def floor_job():
            pending=[]
            if self.washing:pending.append(('wash',self.wash_owner,self.wash_left,(965,320,0)))
            if self.wipe_table>=0:pending.append(('wipe',self.wipe_owner,self.wipe_left,table_target(self.wipe_table)))
            if self.sweep_spot>=0:pending.append(('sweep',self.sweep_owner,self.sweep_left,(*DIRT_POS[self.sweep_spot%len(DIRT_POS)],self.sweep_spot//len(DIRT_POS))))
            for kind,owner,left,target in pending:
                task=cleanup_job(kind,owner,left,target)
                if task:yield task
            for p in sorted(self.parties,key=lambda p:p.id):
                if p.phase in ('door','waiting'):
                    if any(x['job'] and x['job']['action'][:2]==['door',p.id] for x in active):continue
                    if self.closing or not self.party_stock_available(p):
                        yield job(('door',p.id,'decline'),(p.x,p.y,0),2)
                        continue
                    reserved_seats=sum(q.size for q in self.parties if q.phase in ('queue','buying','ticket','ready'))
                    free=sum(len(self.free_seats(i)) for i in range(len(self.tables)))
                    if self.can_fit(p.size) and free-reserved_seats>=p.size:yield job(('door',p.id,'accept'),(p.x,p.y,0),2)
                    if p.phase=='door':yield job(('door',p.id,'wait'),(p.x,p.y,0),2)
                if p.phase=='ticket':yield job(('collect',p.id),(725,350,0),3)
                if p.phase=='ready':
                    table=next((i for i in range(len(self.tables)) if len(self.free_seats(i))>=p.size),None)
                    if table is not None:yield job(('seat',p.id,table),table_target(table),2)
            for key,order in self.staff_cooking.items():
                p=self.group(order['gid']);b=next((b for b in self.bowls if b.id==order.get('bid')),None)
                if order.get('done') and b and p and order['index']==len(p.meals):yield job(('serve',b.id,p.table,p.id),table_target(p.table),2)
            # Baito may carry correctly prepared bowls made manually as well.
            for p in self.parties:
                if p.phase=='seated' and len(p.meals)<p.size:
                    bowl=next((b for b in self.bowls if b.stage=='prep' and Counter(b.toppings)==Counter(p.recipes[len(p.meals)])),None)
                    if bowl:yield job(('serve',bowl.id,p.table,p.id),table_target(p.table),2)
                if p.phase in ('seated','eating'):
                    for i,name in enumerate(p.drinks):
                        if name and p.drinks_served[i]!=name and self.stock[name]>0:yield job(('drink',name,p.table,p.id),table_target(p.table),2)
            for i,t in enumerate(self.tables):
                if t.dirty:yield job(('clear',i),table_target(i),3)
                if not t.dirty and t.needs_wipe and self.wipe_table<0:yield job(('wipe',i),table_target(i),1)
            if self.sink and not self.washing:yield job(('wash',),(965,320,0),2)
            if self.dirt and self.sweep_spot<0:
                spot=self.dirt[0];yield job(('sweep',spot),(*DIRT_POS[spot%len(DIRT_POS)],spot//len(DIRT_POS)),15)
            if self.closing and not any(p.phase in ('seated','eating','ready','ticket','buying','queue') for p in self.parties):
                if self.bowls:yield job(('discard',self.bowls[0].id),(1000,590,0),2)
                for i,age in enumerate(self.pots):
                    if age is not None:yield job(('discard_pot',i),(*POT_POS[i],0),2)
            return None

        for kind,left,target in [('wash',self.wash_left,(965,320,0)),('wipe',self.wipe_left,table_target(self.wipe_table) if self.wipe_table>=0 else (0,0,0)),('sweep',self.sweep_left,(*DIRT_POS[self.sweep_spot%len(DIRT_POS)],self.sweep_spot//len(DIRT_POS)) if self.sweep_spot>=0 else (0,0,0))]:
            if left>0 and getattr(self,kind+'_owner')==e['id']:
                return job(('clean_wait',kind),target,left)
        # Baito prioritise actionable horu work, then support the complete kitchen cycle.
        priorities=((floor,floor_job),(kitchen,kitchen_job)) if primary=='floor' else ((kitchen,kitchen_job),(floor,floor_job))
        for allowed,choose in priorities:
            if allowed:
                for task in choose():
                    if task:return task
        return None

    def finish_staff_job(self,e,job):
        action=job['action'];kind,*args=action
        if kind in ('idle','clean_wait'):return
        if kind=='shop':
            from operations import complete_purchase
            complete_purchase(self,e,args[0]);return
        if kind in ('wash','wipe','sweep'):
            fn={'wash':self.wash,'wipe':self.wipe,'sweep':self.sweep}[kind]
            if fn(*args,owner=e['id']):
                left=getattr(self,kind+'_left')
                e['job']={'action':['clean_wait',kind],'target':job['target'],'left':left}
                e['status']=self.job_label(action);e['tasks']+=1
            return
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
                self.note(message);self.speech_events.append({'text':message,'dishes':p.orders+[d for d in p.drinks if d]})
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
