"""Interview, contracts, shifts, requested leave calendars and payslips."""
from model import vnd
from staff import MIN_HOURLY,MIN_MONTHLY
from vn_calendar import WEEKDAYS
from datetime import date

class StaffUI:
    def init_staff_ui(self):
        self.staff_tab='team';self.staff_page=0;self.hire_months=12;self.staff_panel=False

    def render_staff(self):
        w=self.world
        self.text('NHÂN SỰ · Cài ca trước khi bật tự đến làm',(60,397),24,'#26372e',True)
        tabs=[('team','Nhân viên / ca'),('hire','Phỏng vấn'),('leave','Lịch nghỉ'),('pay','Bảng lương'),('settings','Vận hành nền')]
        for i,(key,label) in enumerate(tabs):
            self.button((60+i*295,435,280,36),label,('staff_tab',key),small=True,color='#426f57' if key==self.staff_tab else '#7c876d')
        if self.staff_tab=='hire':
            self.text('Tính cách chỉ bộc lộ khi làm. Tối đa 8 người. Hợp đồng: '+str(self.hire_months)+' tháng',(65,485),19)
            self.button((1250,482,250,34),'Đổi thời hạn hợp đồng',('hire_months',),small=True)
            for i,c in enumerate(w.applicants()):
                y=535+i*77;role='Baito · phục vụ' if c['role']=='baito' else 'Chính thức · bếp / quản lý'
                self.text(f'{c["name"]} #{c["id"]} · {role}',(65,y+3),22,'#26372e',True)
                self.text(vnd(c['wage'])+('/giờ' if c['role']=='baito' else '/tháng'),(670,y+7),20)
                self.button((1015,y,55,38),'−',('offer',c['id'],-1),small=True)
                self.button((1080,y,55,38),'+',('offer',c['id'],1),small=True)
                self.button((1160,y,340,38),'Thuê' if c['role']=='baito' else 'Đọc & ký hợp đồng',('hire_review',c['id']),len(w.employees)<8,small=True)
            self.text('Baito không phạt khi nghỉ. Hợp đồng nghỉ trước hạn: phạt 1/2 lương cơ bản.',(65,855),18)
        elif self.staff_tab=='team':
            for i,e in enumerate(w.employees[self.staff_page*4:self.staff_page*4+4]):
                y=491+i*85;start=e['shift_start'];end=start+e['shift_hours']*60
                self.text(f'{e["name"]} #{e["id"]} · '+('Baito' if e['role']=='baito' else 'Hợp đồng')+' · '+e['status'],(65,y),20,'#26372e',True)
                self.text('Quan sát: '+(', '.join(e['observed']) or 'Chưa biết')+' · Công nợ '+vnd(w.payroll_due(e)),(65,y+29),17)
                self.text(f'{start//60:02}:{start%60:02} – {end//60:02}:{end%60:02}',(713,y+5),21)
                for x,label,kind,delta in [(895,'←30p','shift_start',-30),(985,'30p→','shift_start',30),(1080,'−1h','shift_hours',-1),(1150,'+1h','shift_hours',1)]:
                    self.button((x,y,65 if x>=1080 else 80,35),label,(kind,e['id'],delta),small=True)
                self.button((1240,y,115,35),'Tắt ca' if e['enabled'] else 'Bật ca',('shift_toggle',e['id']),small=True)
                self.button((1370,y,135,35),'Cho nghỉ',('fire_review',e['id']),small=True,color='#ba4d3c')
            if not w.employees:self.text('Chưa có nhân viên. Sang Phỏng vấn để tuyển người.',(65,540),24)
            self.staff_pager(len(w.employees),4)
            self.text('Ca cùng ngày, tối đa 12h. Chính thức: 8h chuẩn; phần dư tính tăng ca. Chế độ nền ở tab Vận hành nền.',(65,855),17)
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
        if kind=='staff_tab':self.staff_tab=args[0];self.staff_page=0
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
        if self.modal=='fire_staff':
            e=w.employee(self.staff_review_id)
            self.text('CHẤM DỨT CÔNG VIỆC',(310,170),34,'#26372e',True)
            self.wrap(f'{e["name"]}: phạt {vnd(w.termination_fee(e["id"]))}. Quán thanh toán luôn lương đã phát sinh còn nợ {vnd(w.payroll_due(e))}.', (310,275),960,27)
            self.button((330,650,440,65),'Thanh toán & cho nghỉ',('fire_confirm',),small=True,color='#ba4d3c')
        else:
            c=next(c for c in w.applicants() if c['id']==self.staff_review_id)
            self.text('THỎA THUẬN NHÂN VIÊN',(310,170),34,'#26372e',True)
            role='Baito, trả theo giờ cuối ca/ngày, không phí chấm dứt.' if c['role']=='baito' else f'Hợp đồng {self.hire_months} tháng; ca chuẩn 8h. Phạt nghỉ trước hạn: 1/2 lương cơ bản.'
            self.wrap(c['name']+' · '+role,(310,260),960,26)
            self.wrap('Lương đã chốt: '+vnd(c['wage'])+('/giờ' if c['role']=='baito' else '/tháng')+'. Tính cách chưa biết. Lịch nghỉ 9 ngày/tháng theo quy tắc quán, không thứ Sáu–CN hoặc lễ. Bạn đặt giờ bắt đầu và số giờ mỗi ca sau khi thuê.',(310,390),960,24)
            if c['role']=='contract':self.wrap('Chốt lương ngày 17, trả ngày 27. Tăng ca ngày thường 150%, cuối tuần 200%, lễ 300%. BH người lao động 10,5%, quán 21,5%; thuế tự khấu trừ trước thực nhận. Lương được phân bổ theo giờ làm thực tế.',(310,520),960,21)
            self.button((330,740,440,65),'Đồng ý thuê / ký',('hire_confirm',),small=True)
        self.button((830,740 if self.modal!='fire_staff' else 650,440,65),'Quay lại',('dismiss',),small=True,color='#8a7352')
