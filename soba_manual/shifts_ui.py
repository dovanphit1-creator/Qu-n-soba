import pygame as pg
from shifts import clock_label,shift_label

class ShiftsUI:
    def render_shifts(self):
        w=self.world
        self.button((1130,484,365,35),'Tạo ca' if self.shifts_view else 'Xem nguyện vọng theo ngày',('shifts_view',),small=True)
        if self.shifts_view:
            day=w.now.date()+__import__('datetime').timedelta(days=self.shift_day)
            self.text('NGUYỆN VỌNG / LỊCH CA · '+day.strftime('%d/%m/%Y'),(65,491),23,'#26372e',True)
            self.button((65,535,170,35),'Ngày trước',('shift_day',-1),self.shift_day>0,small=True)
            self.button((250,535,170,35),'Ngày sau',('shift_day',1),self.shift_day<31,small=True)
            for i,e in enumerate(w.employees[self.staff_page*3:self.staff_page*3+3]):
                p=w.day_plan(e,day);y=603+i*66
                self.text(e['name']+' · '+p.get('shift_name','Ca cũ')+' · '+clock_label(p['start'])+'–'+clock_label(p['end']),(65,y),21)
                intervals=p.get('breaks',[])
                breaks=', '.join(clock_label(a)+'–'+clock_label(b) for a,b in intervals) or 'Không nghỉ'
                hours=sum(b-a for a,b,mode in p['segments'])/60
                self.text(('Không làm hôm nay' if not p['segments'] else f'Dự kiến {hours:.2f}h làm')+' · Nghỉ: '+breaks,(65,y+27),16)
            self.staff_pager(len(w.employees),3)
            self.wrap('Lịch đã đăng ký được giữ ổn định khi mở lại trang và lưu game. Baito có thể đi muộn, về sớm hoặc nghỉ đột xuất theo tính cách; chỉ trả thời gian thực làm.',(65,810),1030,18)
            return
        self.text('CA TỰ TẠO · Ca trong ngày, dài 1–12 giờ',(65,491),23,'#26372e',True)
        self.button((65,535,435,40),self.shift_name or 'Bấm nhập tên ca',('shift_name',),small=True)
        self.text('Bắt đầu '+clock_label(self.shift_begin)+' · Kết thúc '+clock_label(self.shift_finish),(525,546),21)
        for x,label,field,delta in [(65,'Bắt đầu −15p','begin',-15),(280,'Bắt đầu +15p','begin',15),(525,'Kết thúc −15p','finish',-15),(740,'Kết thúc +15p','finish',15)]:
            self.button((x,588,205,38),label,('shift_time',field,delta),small=True)
        self.button((995,535,500,40),'Tạo ca mới',('shift_create',),small=True)
        for i,s in enumerate(w.shifts[self.staff_page*3:self.staff_page*3+3]):
            y=650+i*49
            self.text(shift_label(s)+' · '+('Đang mời đăng ký' if s['enabled'] else 'Ngừng mời'),(65,y),20)
            self.button((1170,y-5,325,35),'Ngừng mời' if s['enabled'] else 'Mời đăng ký',('shift_available',s['id']),small=True)
        self.staff_pager(len(w.shifts),3)
        self.wrap('Baito chọn lại mỗi ngày, nhiều lần nghỉ không tính công. Chính thức ghi ca trong CV; tuyển xong khóa ca, làm đủ 8h và nghỉ một lần. Ca chính thức phải dài ít nhất 8h15p.',(65,803),1020,17)

    def shifts_input(self,event):
        if self.input_focus!='shift_name' or self.modal:return False
        if event.type==pg.TEXTINPUT:
            self.shift_name=(self.shift_name+''.join(c for c in event.text if c.isprintable()))[:28];return True
        if event.type==pg.TEXTEDITING:return True
        if event.type==pg.KEYDOWN:
            if event.key==pg.K_BACKSPACE:self.shift_name=self.shift_name[:-1]
            elif event.key in (pg.K_RETURN,pg.K_ESCAPE):self.input_focus=None;pg.key.stop_text_input()
            return True
        return False

    def shifts_action(self,kind,args):
        w=self.world
        if kind=='shift_name':self.input_focus='shift_name';pg.key.start_text_input()
        elif kind=='shifts_view':self.shifts_view=not self.shifts_view;self.staff_page=0;self.input_focus=None;pg.key.stop_text_input()
        elif kind=='shift_day':self.shift_day=max(0,min(31,self.shift_day+args[0]));self.staff_page=0
        elif kind=='shift_time':
            field='shift_begin' if args[0]=='begin' else 'shift_finish'
            setattr(self,field,max(0,min(1440,getattr(self,field)+args[1])))
        elif kind=='shift_create':
            if w.create_shift(self.shift_name,self.shift_begin,self.shift_finish):self.shift_name='';self.staff_page=0;self.persist()
            else:w.note('Tên ca phải khác nhau; giờ trong 00–24h, dài 1–12h.')
        elif kind=='shift_available':
            s=next(s for s in w.shifts if s['id']==args[0]);s['enabled']=not s['enabled'];w.refresh_future_baito_shifts();self.persist()
        else:return False
        return True
