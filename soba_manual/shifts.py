"""Custom daily shifts, applicant preferences and immutable contract windows."""
from copy import deepcopy

def clock_label(minute):
    return f'{minute//60:02}:{minute%60:02}'

def shift_label(s):
    return s['name']+' · '+clock_label(s['start'])+'–'+clock_label(s['end'])

class ShiftMixin:
    def init_shifts(self):
        self.shifts=[dict(id=1,name='Ca ngày',start=480,end=990,enabled=True)]
        self.next_shift=2

    def create_shift(self,name,start,end):
        name=str(name).strip()
        if not name or len(name)>28 or type(start)!=int or type(end)!=int or not 0<=start<end<=1440 or not 60<=end-start<=720:return False
        if any(s['name']==name for s in self.shifts):return False
        self.shifts.append(dict(id=self.next_shift,name=name,start=start,end=end,enabled=True));self.next_shift+=1
        self.refresh_future_baito_shifts()
        self.note('Đã tạo '+shift_label(self.shifts[-1])+'. Nhân viên tự chọn theo nguyện vọng.');return True

    def shift_options(self,role):
        return [s for s in self.shifts if s['enabled'] and (role!='contract' or s['end']-s['start']>=495)]

    def refresh_future_baito_shifts(self):
        for e in self.employees:
            if e['role']=='baito' and e.get('self_select',True):
                for day in list(e['plans']):
                    if day>self.now.date().isoformat():e['plans'].pop(day)

    def assign_cv_shift(self,c):
        if c['role']=='contract' and 'requested_shift' not in c:
            options=self.shift_options('contract')
            c['requested_shift']=deepcopy(self.rng.choice(options)) if options else None

    def migrate_shifts(self):
        for c in self.candidates:self.assign_cv_shift(c)
        for e in self.employees:
            e.setdefault('self_select',True);e.setdefault('contract_breaks',{})
            if e['role']=='contract':
                e.setdefault('agreed_shift',dict(id=0,name='Ca hợp đồng cũ',start=e['shift_start'],end=e['shift_start']+510))
                e['shift_start']=e['agreed_shift']['start'];e['shift_hours']=8
                for day,p in e.get('plans',{}).items():
                    regular=[s for s in p['segments'] if s[2]=='regular']
                    if len(regular)==2 and regular[1][0]>regular[0][1]:
                        e['contract_breaks'].setdefault(day,regular[0][1]-e['shift_start'])

    def make_shift_plan(self,e,day,cover,eligible):
        key=day.isoformat();start=cover['start'] if cover else e['shift_start']
        if e['role']=='contract':
            s=e['agreed_shift'];start=s['start'];end=s['end'];rest=end-start-480
            offset=e['contract_breaks'].setdefault(key,self.rng.randint(60,420))
            segments=[[start,start+offset,'regular'],[start+offset+rest,end,'regular']]
            if e['overtime_hours']:segments.append([end,end+e['overtime_hours']*60,'overtime'])
            return dict(segments=segments if eligible else [],start=start,end=end+e['overtime_hours']*60,late=0,absence=False,early=0,
                        shift_name=s['name'],breaks=[[start+offset,start+offset+rest]])
        options=self.shift_options('baito') if e.get('self_select',True) and not cover else []
        selected=self.rng.choice(options) if options else None
        if e.get('self_select',True) and not cover and not selected:eligible=False
        if selected:start=selected['start'];end=selected['end']
        else:end=start+(cover['hours'] if cover else e['shift_hours'])*60
        lazy='Lười' in e['traits']
        absence=eligible and self.rng.random()<(.12 if lazy else .02)
        late=self.rng.randint(5,45) if eligible and self.rng.random()<(.32 if lazy else .06) else 0
        early=self.rng.randint(15,75) if eligible and self.rng.random()<(.12 if lazy else .015) else 0
        begin=min(end,start+late);finish=max(begin,end-early);segments=[];breaks=[]
        if eligible and not absence and finish>begin:
            cursor=begin
            # Unlimited number of breaks, naturally bounded by the chosen time window.
            while cursor<finish:
                stop=min(finish,cursor+self.rng.randint(45,150))
                segments.append([cursor,stop,'baito']);cursor=stop
                if cursor<finish:
                    back=min(finish,cursor+self.rng.randint(5,40 if lazy else 20))
                    breaks.append([cursor,back]);cursor=back
        return dict(segments=segments,start=start,end=end,late=late,absence=absence,early=early,
                    shift_name=selected['name'] if selected else 'Ca làm thay' if cover else 'Ca cũ',breaks=breaks)
