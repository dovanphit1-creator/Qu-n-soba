"""Interview, contracts, shifts, requested leave calendars and payslips."""
from model import vnd
from staff import MIN_HOURLY,MIN_MONTHLY
from vn_calendar import WEEKDAYS
from datetime import date

class StaffUI:
    def init_staff_ui(self):
        self.staff_tab='team';self.staff_page=0;self.hire_months=12;self.staff_panel=False;self.cover_date='';self.cover_position='floor';self.cover_start=480;self.cover_hours=4

    def render_staff(self):
        w=self.world
        self.text('NHÂN SỰ · Cài ca trước khi bật tự đến làm',(60,397),24,'#26372e',True)
        tabs=[('team','Nhân viên / ca'),('hire','Tuyển dụng'),('clock','Chấm công'),('leave','Lịch nghỉ'),('coverage','Thiếu người'),('pay','Bảng lương'),('settings','Chạy nền')]
        for i,(key,label) in enumerate(tabs):
            self.button((60+i*209,435,197,36),label,('staff_tab',key),small=True,color='#426f57' if key==self.staff_tab else '#7c876d')
        if self.staff_tab=='hire':
            self.button((65,483,355,37),'Đăng bài tuyển nhân viên',('post_recruitment',),not w.candidates,small=True)
            self.text('CV tự khai có thể sai. Tối đa 8 nhân viên.',(455,494),19)
            self.button((1220,483,280,37),'Hợp đồng '+str(self.hire_months)+' tháng',('hire_months',),small=True)
            for i,c in enumerate(w.applicants()):
                y=537+i*73;role='Baito · horu / phụ bếp' if c['role']=='baito' else 'Chính thức · bếp / hỗ trợ horu'
                self.text(f'{c["name"]} #{c["id"]} · {c["birth_year"]} · {c["hometown"]} · {role}',(65,y),20,'#26372e',True)
                self.text('CV tự khai: '+', '.join(c['cv_traits'])+' · '+vnd(c['wage'])+('/giờ' if c['role']=='baito' else '/tháng'),(65,y+28),17)
                self.button((1020,y+22,55,35),'−',('offer',c['id'],-1),small=True)
                self.button((1083,y+22,55,35),'+',('offer',c['id'],1),small=True)
                self.button((1150,y+22,220,35),'Xem CV / phỏng vấn',('hire_review',c['id']),len(w.employees)<8,small=True)
                self.button((1380,y+22,120,35),'Từ chối CV',('reject_cv',c['id']),small=True,color='#8a7352')
            if not w.candidates:self.wrap('Chưa có CV. Đăng bài tuyển để nhận hồ sơ ứng viên. Không thể biết tính cách thật trước khi họ làm việc.',(65,555),1350,24)
            self.text('Baito không phạt khi nghỉ. Hợp đồng nghỉ trước hạn: phạt 1/2 lương cơ bản.',(65,855),18)
        elif self.staff_tab=='team':
            for i,e in enumerate(w.employees[self.staff_page*3:self.staff_page*3+3]):
                y=491+i*101;start=e['shift_start'];end=w.shift_end(e)
                self.text(f'{e["name"]} #{e["id"]} · '+('Baito' if e['role']=='baito' else 'Chính thức')+' · '+e['status'],(65,y),20,'#26372e',True)
                self.text('Quan sát: '+(', '.join(e['observed']) or 'Chưa biết')+' · Công nợ '+vnd(w.payroll_due(e)),(65,y+29),17)
                self.text(f'{start//60:02}:{start%60:02} – {end//60:02}:{end%60:02}',(760,y+5),21)
                self.text('Chấm máy theo giờ thực làm' if e['role']=='baito' else '8h làm + 30p nghỉ · TC '+str(e['overtime_hours'])+'h',(760,y+40),17)
                for x,label,kind,delta in [(1020,'←30p','shift_start',-30),(1110,'30p→','shift_start',30)]:
                    self.button((x,y,80,34),label,(kind,e['id'],delta),small=True)
                kind='shift_hours' if e['role']=='baito' else 'overtime'
                self.button((1020,y+40,80,34),'−1h', (kind,e['id'],-1),small=True)
                self.button((1110,y+40,80,34),'+1h', (kind,e['id'],1),small=True)
                self.button((1240,y,115,35),'Tắt ca' if e['enabled'] else 'Bật ca',('shift_toggle',e['id']),small=True)
                self.button((1370,y,135,35),'Cho nghỉ',('fire_review',e['id']),small=True,color='#ba4d3c')
            if not w.employees:self.text('Chưa có nhân viên. Sang Tuyển dụng để đăng bài.',(65,540),24)
            self.staff_pager(len(w.employees),3)
            self.text('Baito: 1–12h dự kiến, có thể muộn / nghỉ. Chính thức: 8h chuẩn, TC 0–4h; nghỉ sau 4h, đúng 30p.',(65,855),17)
        elif self.staff_tab=='clock':
            self.text('MÁY CHẤM CÔNG · Baito tự chấm lúc đến, nghỉ, quay lại và về. Chính thức chỉ chấm tăng ca.',(65,489),20)
            rows=list(reversed(w.clock_events))
            for i,r in enumerate(rows[self.staff_page*7:self.staff_page*7+7]):
                y=535+i*37
                self.text(r['at'].replace('T',' ')[:19]+' · '+r['name']+' · '+r['event']+' · '+('Tăng ca' if r['mode']=='overtime' else 'Baito'),(65,y),20)
            if not rows:self.text('Chưa có lượt chấm. Cài ca và bật lịch làm việc trước.',(65,550),23)
            self.staff_pager(len(rows),7)
            self.text('Giải lao và thời gian chưa tới / đã về không có lương. Ca chuẩn chính thức ghi công theo lịch, không chấm máy.',(65,855),17)
        elif self.staff_tab=='leave':
            self.button((65,490,550,40),'Yêu cầu tất cả gửi lịch nghỉ tháng này',('request_leave',),small=True)
            self.text('9 ngày/người/tháng · Không thứ Sáu–CN hoặc lễ',(660,503),20)
            for i,e in enumerate(w.employees[self.staff_page*5:self.staff_page*5+5]):
                y=553+i*55
                self.text(e['name']+' #'+str(e['id']),(65,y),21,'#26372e',True)
                month=w.now.date().isoformat()[:7]
                days=e['leaves'].get(month,[])
                value='Chưa gửi. Bấm yêu cầu lịch nghỉ.' if e['leave_sent']!=month else ', '.join(f'{date.fromisoformat(d).day:02} ({WEEKDAYS[date.fromisoformat(d).weekday()]})' for d in days)
                self.text(value,(265,y+2),18)
            self.staff_pager(len(w.employees),5)
        elif self.staff_tab=='coverage':
            start=w.coverage_start;end=w.coverage_end
            self.text(f'Kiểm tra giờ dự kiến mở: {start//60:02}:{start%60:02} – {end//60:02}:{end%60:02}',(65,491),21)
            for x,label,kind,delta in [(690,'Mở −30p','coverage_start',-30),(870,'Mở +30p','coverage_start',30),(1050,'Đóng −30p','coverage_end',-30),(1230,'Đóng +30p','coverage_end',30)]:
                self.button((x,484,165,35),label,(kind,delta),small=True)
            rows=w.coverage_report()
            for i,r in enumerate(rows[self.staff_page*3:self.staff_page*3+3]):
                y=541+i*63
                gaps=', '.join(f'{a//60:02}:{a%60:02}–{b//60:02}:{b%60:02}' for a,b in r['gaps'])
                self.text(r['date']+' · '+r['label']+' thiếu: '+gaps,(65,y),18,'#26372e',True)
                self.button((800,y-4,210,35),'Mời baito làm thay',('coverage_review',r['date'],r['position']),small=True)
                self.button((1030,y-4,210,35),'Theo lịch nhân viên' if r['decision']=='player' else 'Chủ quán tự làm',('decide_day',r['date'],'normal' if r['decision']=='player' else 'player'),small=True)
                self.button((1260,y-4,240,35),'Cho quán nghỉ ngày này',('decide_day',r['date'],'closed'),small=True,color='#8a7352')
                if r['decision']=='player':self.text('Đã chọn chủ quán tự làm; ngày này mở quán thủ công.',(65,y+27),16)
            if not rows:self.wrap('Yêu cầu tất cả gửi lịch ở tab Lịch nghỉ để kiểm tra. Nếu đã nhận đủ mà bảng trống: mọi vị trí có ca phủ giờ mở dự kiến.',(65,550),1380,23)
            closed=[d for d,v in w.day_decisions.items() if v=='closed' and d>=w.now.date().isoformat()]
            for i,key in enumerate(closed[:3]):
                self.text('Quán nghỉ '+key,(65,744+i*23),17)
                self.button((355+i*375,746,350,31),'Mở lại '+key,('decide_day',key,'normal'),small=True)
            self.staff_pager(len(rows),3)
            self.text('Báo thiếu theo vị trí chính, tính cả giải lao cố định. Baito làm thay có thể từ chối hoặc đến muộn.',(65,855),17)
        elif self.staff_tab=='pay':
            self.text('Chốt đến hết ngày 17 · Trả ngày 27. Công việc 18–17 thuộc cùng kỳ. Baito trả cuối ca / ngày.',(65,485),19)
            rows=list(reversed(w.payroll))
            for i,r in enumerate(rows[self.staff_page*4:self.staff_page*4+4]):
                y=535+i*72
                self.text(f'{r["name"]} · kỳ {r["period"]} · trả {r["paid"]} · {r["hours"]:.2f}h',(65,y),21,'#26372e',True)
                self.text('Gộp '+vnd(r['gross'])+' · BH người lao động '+vnd(r['insurance'])+' · Thuế '+vnd(r['tax'])+' · Thực nhận '+vnd(r['net']),(65,y+30),18)
                self.text('BH quán '+vnd(r['employer']),(1255,y),17)
            if not rows:self.text('Chưa đến kỳ chi trả. Lương đã phát sinh được ghi vào lợi nhuận hằng ngày.',(65,560),23)
            self.staff_pager(len(rows),4)
            self.text('BH người lao động: hưu trí 8% + y tế 1,5% + thất nghiệp 1%. Thuế lũy tiến 2026, giảm trừ 15,5 triệu.',(65,855),17)
        else:
            self.button((65,492,690,45),'Tự mở quán đúng ca: '+('BẬT' if w.staff_auto_open else 'TẮT'),('staff_auto_open',),small=True)
            self.button((805,492,695,45),'Windows chạy nền: '+('BẬT' if w.background_enabled else 'TẮT'),('background_toggle',),self.persistent and __import__('sys').platform=='win32',small=True)
            self.wrap('Bật ca cho từng nhân viên. Đến giờ, nhân viên tự mở khi kho có đủ nguyên liệu và bát sạch. Hết ca cuối, quán ngừng nhận khách; nhân viên chỉ làm và nhận công trong ca đã đặt. Hãy bố trí ca phủ cả thời gian phục vụ và dọn cuối ngày.',(65,565),1420,23)
            self.wrap('Windows: bật chạy nền để nút X ẩn cửa sổ xuống khay hệ thống. Game khởi động nền cùng tài khoản Windows. Chuột phải biểu tượng bát mì để mở hoặc lưu và thoát hoàn toàn. Máy phải bật và không ngủ. Tắt nền sẽ ngừng tự làm khi thoát.',(65,683),1420,23)
            self.wrap('Bản web: không lưu và không chạy khi đóng tab. Trình duyệt có thể giảm tốc độ ở tab nền. Thông số bảo hiểm / thuế là mô hình game, lịch nghỉ và khoản phạt là quy tắc của quán.',(65,810),1420,19)

    def staff_pager(self,count,size):
        self.button((1140,815,170,35),'Trước',('staff_page',-1),self.staff_page>0,small=True)
        self.button((1330,815,170,35),'Sau',('staff_page',1),(self.staff_page+1)*size<count,small=True)

    def staff_action(self,kind,args):
        w=self.world
        if kind=='clock_machine':self.staff_panel=True;self.staff_tab='clock';self.staff_page=0
        elif kind=='staff_tab':self.staff_tab=args[0];self.staff_page=0
        elif kind=='staff_page':self.staff_page=max(0,self.staff_page+args[0])
        elif kind=='staff_panel':self.staff_panel=not self.staff_panel;self.modal=None
        elif kind=='hire_months':self.hire_months={3:6,6:12,12:3}[self.hire_months]
        elif kind=='offer':
            c=next(c for c in w.applicants() if c['id']==args[0]);step=5000 if c['role']=='baito' else 500000
            c['wage']=max(MIN_HOURLY if c['role']=='baito' else MIN_MONTHLY,c['wage']+args[1]*step)
        elif kind=='hire_review':self.staff_review_id=args[0];self.modal='hire_contract'
        elif kind=='hire_confirm':
            w.hire(self.staff_review_id,months=self.hire_months);self.modal=None;self.persist()
        elif kind in ('shift_start','shift_hours','shift_toggle'):
            e=w.employee(args[0])
            if e:
                start=e['shift_start']+(args[1] if kind=='shift_start' else 0)
                hours=e['shift_hours']+(args[1] if kind=='shift_hours' else 0)
                w.set_shift(e['id'],start,hours,not e['enabled'] if kind=='shift_toggle' else e['enabled']);self.persist()
        elif kind=='post_recruitment':w.post_recruitment();self.persist()
        elif kind=='reject_cv':w.dismiss_applicant(args[0]);self.persist()
        elif kind=='overtime':
            e=w.employee(args[0])
            if e:w.set_overtime(e['id'],e['overtime_hours']+args[1]);self.persist()
        elif kind in ('coverage_start','coverage_end'):
            value=getattr(w,kind)+args[0]
            if 0<=value<=1440 and (value<w.coverage_end if kind=='coverage_start' else value>w.coverage_start):setattr(w,kind,value);self.staff_page=0;self.persist()
        elif kind=='coverage_review':
            self.cover_date,self.cover_position=args
            row=next((r for r in w.coverage_report() if r['date']==self.cover_date and r['position']==self.cover_position),None)
            if row:self.cover_start=row['gaps'][0][0];self.cover_hours=min(12,max(1,(row['gaps'][0][1]-self.cover_start+59)//60));self.modal='cover_shift'
        elif kind=='cover_start':self.cover_start=max(0,min(1440-self.cover_hours*60,self.cover_start+args[0]))
        elif kind=='cover_hours':self.cover_hours=max(1,min(12,(1440-self.cover_start)//60,self.cover_hours+args[0]))
        elif kind=='invite_cover':w.invite_cover(args[0],self.cover_date,self.cover_position,self.cover_start,self.cover_hours);self.persist()
        elif kind=='decide_day':w.decide_day(*args);self.staff_page=0;self.persist()
        elif kind=='request_leave':w.request_leave();self.persist()
        elif kind=='fire_review':self.staff_review_id=args[0];self.modal='fire_staff'
        elif kind=='fire_confirm':w.fire(self.staff_review_id);self.modal=None;self.persist()
        elif kind=='staff_auto_open':w.staff_auto_open=not w.staff_auto_open;self.persist()
        elif kind=='background_toggle':
            if self.background is not None:
                desired=not w.background_enabled
                if self.background.enable(desired):w.background_enabled=desired;self.persist()
                else:self.last_warning='Không bật được biểu tượng khay hệ thống. Game tiếp tục chạy khi cửa sổ còn mở.'
        else:return False
        return True

    def render_staff_contract(self):
        w=self.world
        if self.modal=='cover_shift':
            self.text('MỜI BAITO LÀM THAY',(310,170),34,'#26372e',True)
            start=self.cover_start;end=start+self.cover_hours*60
            self.text(self.cover_date+' · '+('Bếp' if self.cover_position=='kitchen' else 'Horu')+f' · {start//60:02}:{start%60:02}–{end//60:02}:{end%60:02}',(310,230),26)
            for x,label,kind,delta in [(310,'Bắt đầu −30p','cover_start',-30),(540,'Bắt đầu +30p','cover_start',30),(770,'−1h','cover_hours',-1),(980,'+1h','cover_hours',1)]:
                self.button((x,278,200,38),label,(kind,delta),small=True)
            for i,e in enumerate([e for e in w.employees if e['role']=='baito']):
                y=340+i*40
                result=next((r for r in w.cover_invites if r['employee']==e['id'] and r['date']==self.cover_date),None)
                busy=self.cover_date in e['cover_days'] or (e['enabled'] and self.cover_date not in w.ensure_leave(e,date.fromisoformat(self.cover_date)))
                status=('Đồng ý' if result['accepted'] else 'Từ chối') if result else ('Đã có ca' if busy else 'Chưa hỏi')
                self.text(e['name']+' · '+status,(310,y),22)
                self.button((980,y,260,34),'Xin làm thay',('invite_cover',e['id']),not result and not busy,small=True)
            if not any(e['role']=='baito' for e in w.employees):self.text('Chưa có baito. Bạn tự làm hoặc cho quán nghỉ.',(310,360),22)
            self.wrap('Lời mời chỉ hỏi một lần cho mỗi người/ngày. Đồng ý sẽ thêm ca đặc biệt cho vị trí này; vẫn chấm công theo thời gian thực làm.',(310,680),960,21)
            self.button((830,740,440,65),'Quay lại',('dismiss',),small=True,color='#8a7352');return
        if self.modal=='fire_staff':
            e=w.employee(self.staff_review_id)
            self.text('CHẤM DỨT CÔNG VIỆC',(310,170),34,'#26372e',True)
            self.wrap(f'{e["name"]}: phạt {vnd(w.termination_fee(e["id"]))}. Quán thanh toán luôn lương đã phát sinh còn nợ {vnd(w.payroll_due(e))}.', (310,275),960,27)
            self.button((330,650,440,65),'Thanh toán & cho nghỉ',('fire_confirm',),small=True,color='#ba4d3c')
        else:
            c=next(c for c in w.applicants() if c['id']==self.staff_review_id)
            self.text('THỎA THUẬN NHÂN VIÊN',(310,170),34,'#26372e',True)
            role='Baito, trả theo giờ cuối ca/ngày, không phí chấm dứt.' if c['role']=='baito' else f'Hợp đồng {self.hire_months} tháng; ca chuẩn 8h. Phạt nghỉ trước hạn: 1/2 lương cơ bản.'
            self.wrap(c['name']+f' · sinh {c["birth_year"]} · {c["hometown"]} · '+role,(310,250),960,24)
            self.text('CV tự khai: '+', '.join(c['cv_traits'])+' (có thể không đúng)',(310,335),21)
            self.wrap('Lương đã chốt: '+vnd(c['wage'])+('/giờ' if c['role']=='baito' else '/tháng')+'. Tính cách chưa biết. Lịch nghỉ 9 ngày/tháng theo quy tắc quán, không thứ Sáu–CN hoặc lễ. Baito đặt 1–12h dự kiến, nhận lương theo chấm công. Chính thức cố định 8h làm + 30p nghỉ, tăng ca đặt riêng.',(310,390),960,24)
            if c['role']=='contract':self.wrap('Chốt lương ngày 17, trả ngày 27. Tăng ca ngày thường 150%, cuối tuần 200%, lễ 300%. BH người lao động 10,5%, quán 21,5%; thuế tự khấu trừ trước thực nhận. Lương được phân bổ theo giờ làm thực tế.',(310,520),960,21)
            self.button((330,740,440,65),'Đồng ý thuê / ký',('hire_confirm',),small=True)
        self.button((830,740 if self.modal!='fire_staff' else 650,440,65),'Quay lại',('dismiss',),small=True,color='#8a7352')
