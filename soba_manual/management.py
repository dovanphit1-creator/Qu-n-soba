"""Closed-shop management controls, including Unicode menu text input."""
import pygame as pg
from model import STOCK_COST, TABLE_COST, CHAIR_COST, FLOOR_COST, vnd, supplier_price, DRINKS, STOCK_UNITS

INK='#26372e'
GREEN='#426f57'
RED='#ba4d3c'

class ManagementUI:
    def init_management(self):
        self.init_staff_ui()
        self.stock_page=0
        self.supplier_page=0
        self.recipe_page=0
        self.floor = 0
        self.order_quantities = {name: 0 for name in STOCK_COST}
        self.menu_page = 0
        self.reset_menu_form()

    def reset_menu_form(self):
        self.menu_original = None
        self.menu_name = ''
        self.menu_price = ''
        self.menu_quantities = {name: 0 for name in STOCK_COST if name != 'Mì tươi' and name not in DRINKS}
        self.input_focus = None
        self.composition = ''

    def render_expansion(self):
        w=self.world
        self.text('BÀN GHẾ & TẦNG · Tối đa 3 tầng, 6 bàn/tầng, 4 ghế/bàn',(60,398),24,INK,True)
        for floor in range(w.floors):
            self.button((65+floor*180,441,165,40),f'Tầng {floor+1}',('floor',floor),color=GREEN if floor==self.floor else '#8a7352',small=True)
        if w.floors<3:
            self.button((830,441,685,40),f'Xây tầng {w.floors+1} · {vnd(FLOOR_COST[w.floors+1])}',('build_floor',),w.cash>=FLOOR_COST[w.floors+1],small=True)
        else:self.text('Đã xây đủ 3 tầng',(1030,450),23,GREEN,True)
        rows=[(i,t) for i,t in enumerate(w.tables) if t.floor==self.floor]
        for row,(i,t) in enumerate(rows):
            y=500+row*49
            self.text(f'Bàn {i+1} · {t.capacity}/4 ghế',(70,y+6),23,INK,True)
            self.text(f'Vị trí {t.slot+1}',(435,y+8),20)
            self.button((830,y,685,40),f'Thêm 1 ghế · {vnd(CHAIR_COST)}',('buy_chair',i),t.capacity<4 and w.cash>=CHAIR_COST,small=True)
        if not rows:self.text('Tầng này chưa có bàn. Mua bàn rồi thêm ghế bên dưới.',(70,535),24)
        self.button((65,836,660,43),f'Mua bàn trống tầng {self.floor+1} · {vnd(TABLE_COST)}',('buy_table',self.floor),len(rows)<6 and w.cash>=TABLE_COST,small=True)
        self.text('Bàn mới chưa có ghế. Mua từng ghế để mở chỗ ngồi.',(765,849),20)

    def render_supplier(self):
        w=self.world
        self.text('NHÀ CUNG CẤP · Giao tự động 08:00 giờ Việt Nam',(60,398),24,INK,True)
        status='Có hiệu lực đến trước '+w.contract_until if w.contract_active else 'Chưa có hợp đồng còn hiệu lực'
        self.text(status,(65,445),20,GREEN)
        self.button((930,435,587,43),'Ký hợp đồng 1 tháng · đơn hàng giá lẻ giảm 3%',('contract',),not w.contract_active,small=True)
        for i,name in enumerate(list(STOCK_COST)[self.supplier_page*6:self.supplier_page*6+6]):
            y=495+i*48
            self.text(name,(65,y+7),21,INK,True)
            self.text(vnd(supplier_price(name))+'/phần',(230,y+9),17)
            for x,label,delta in [(450,'−10',-10),(514,'−1',-1),(697,'+1',1),(761,'+10',10)]:
                self.button((x,y,60,36),label,('order_qty',name,delta),small=True)
            self.text(str(self.order_quantities[name]),(633,y+18),22,INK,True,True)
        self.button((450,789,160,35),'Trước',('supplier_page',-1),self.supplier_page>0,small=True)
        self.button((655,789,160,35),'Sau',('supplier_page',1),(self.supplier_page+1)*6<len(STOCK_COST),small=True)
        cost=sum(supplier_price(k)*v for k,v in self.order_quantities.items())
        self.text('Tổng đơn: '+vnd(cost),(66,801),26,GREEN,True)
        self.button((65,847,758,40),'Đặt & thanh toán · giao sáng mai',('order',),w.contract_active and cost>0 and w.cash>=cost and w.now.hour<23,small=True)
        self.wrap('Mỗi ngày đặt 1 đơn trước 23:00. Chọn số lượng nhập thêm; hàng tồn được giữ nguyên. Hợp đồng không có phí cố định, mỗi đơn giảm 3% so với mua lẻ.',(925,493),585,21)
        self.text('ĐƠN GẦN NHẤT',(929,615),21,INK,True)
        for i,order in enumerate(reversed(w.deliveries[-3:])):
            y=654+i*69
            self.text(order['due'][:10]+' · 08:00 · '+('Đã giao' if order['delivered'] else 'Đang chờ'),(929,y),20,GREEN)
            self.text(vnd(order['cost'])+' · '+str(sum(order['quantities'].values()))+' phần',(929,y+27),18)
        if not w.deliveries:self.text('Chưa đặt đơn nào.',(929,660),21)
        self.text('Nếu tắt game: nhận hàng quá hạn ngay khi mở lại.',(929,865),18)

    def render_menu(self):
        w=self.world
        self.text('MENU TỰ TẠO · Mỗi món gồm 1 phần mì + topping bạn chọn',(60,398),23,INK,True)
        rows=list(w.menu.items())
        for i,(name,item) in enumerate(rows[self.menu_page*6:self.menu_page*6+6]):
            y=450+i*60
            self.text(name,(65,y),21,INK,True)
            self.text(vnd(item['price'])+' · Vốn '+vnd(w.recipe_cost(item['toppings'])),(65,y+28),17)
            self.button((550,y+3,80,39),'Sửa',('edit_menu',name),small=True)
            self.button((641,y+3,80,39),'Xóa',('delete_menu',name),len(rows)>1,small=True,color=RED)
        self.button((65,837,200,42),'Thêm món mới',('reset_menu',),small=True)
        self.button((310,837,180,42),'Trước',('menu_page',-1),self.menu_page>0,small=True)
        self.button((520,837,200,42),'Sau',('menu_page',1),(self.menu_page+1)*6<len(rows),small=True)
        self.text('Tên món',(810,447),21,INK,True)
        self.text('Giá bán VND',(810,495),21,INK,True)
        for key,y in [('name',437),('price',485)]:
            rect=pg.Rect(965,y,553,40)
            self.box(rect,'#ffffff',6,GREEN if self.input_focus==key else '#baac8b')
            value=self.menu_name if key=='name' else self.menu_price
            self.text(value+('|' if self.input_focus==key else ''),(978,y+9),20)
            self.buttons.append((rect,('field',key)))
        self.text('Nguyên liệu: 1 mì tươi (cố định) +',(810,534),20,INK,True)
        for i,(name,qty) in enumerate(list(self.menu_quantities.items())[self.recipe_page*4:self.recipe_page*4+4]):
            y=562+i*39
            self.text(name,(815,y+5),20)
            self.button((1180,y,70,33),'−',('recipe_qty',name,-1),small=True)
            self.text(str(qty),(1310,y+16),21,INK,True,True)
            self.button((1372,y,70,33),'+',('recipe_qty',name,1),small=True)
        self.button((815,725,250,30),'Topping trước',('recipe_page',-1),self.recipe_page>0,small=True)
        self.button((1090,725,350,30),'Topping tiếp',('recipe_page',1),(self.recipe_page+1)*4<len(self.menu_quantities),small=True)
        toppings=[k for k,v in self.menu_quantities.items() for _ in range(v)]
        cost=w.recipe_cost(toppings)
        price=int(self.menu_price or 0)
        self.text('Giá vốn nguyên liệu: '+vnd(cost),(815,765),22,GREEN,True)
        self.text('Lãi trước điện/nước/ga: '+vnd(price-cost),(815,798),21,GREEN if price>=cost else RED)
        self.button((815,844,700,42),'Lưu món · cập nhật máy bán vé',('save_menu',),small=True)
        if self.composition:self.text(self.composition,(980,414),17,GREEN)

    def extra_action(self, kind, args):
        w=self.world
        if self.staff_action(kind,args):return True
        if kind in ('stock_page','supplier_page','recipe_page'):
            setattr(self,kind,max(0,getattr(self,kind)+args[0]))
        elif kind=='floor':
            self.floor=args[0]
        elif kind=='buy_table':w.buy_table(args[0]);self.persist()
        elif kind=='buy_chair':w.buy_chair(args[0]);self.persist()
        elif kind=='build_floor':
            if w.build_floor():self.floor=w.floors-1
            self.persist()
        elif kind=='contract':w.sign_contract();self.persist()
        elif kind=='order_qty':
            key,delta=args;self.order_quantities[key]=min(9999,max(0,self.order_quantities[key]+delta))
        elif kind=='order':
            if w.place_order(self.order_quantities):self.order_quantities={k:0 for k in STOCK_COST}
            self.persist()
        elif kind=='recipe_qty':
            key,delta=args
            if delta<0 or sum(self.menu_quantities.values())<12:
                self.menu_quantities[key]=min(6,max(0,self.menu_quantities[key]+delta))
        elif kind=='field':
            self.input_focus=args[0];pg.key.start_text_input()
        elif kind=='reset_menu':self.reset_menu_form()
        elif kind=='edit_menu':
            self.reset_menu_form();self.menu_original=self.menu_name=args[0]
            item=w.menu[args[0]];self.menu_price=str(item['price'])
            self.menu_quantities={k:item['toppings'].count(k) for k in self.menu_quantities}
        elif kind=='delete_menu':
            if w.delete_menu_item(args[0]):
                self.menu_page=min(self.menu_page,(len(w.menu)-1)//6)
                if self.menu_original==args[0]:self.reset_menu_form()
                self.persist()
        elif kind=='save_menu':
            if w.save_menu_item(self.menu_name,int(self.menu_price or 0),self.menu_quantities,self.menu_original):
                self.reset_menu_form();self.persist()
        elif kind=='menu_page':self.menu_page=max(0,self.menu_page+args[0])
        else:return False
        return True

    def management_input(self, event):
        if self.world.open or self.modal or self.manager_tab!='menu' or not self.input_focus:
            return False
        if event.type==pg.TEXTEDITING:
            self.composition=event.text
            return True
        if event.type==pg.TEXTINPUT:
            value=event.text
            if self.input_focus=='name':self.menu_name=(self.menu_name+''.join(c for c in value if c.isprintable()))[:28]
            elif value.isascii() and value.isdigit():self.menu_price=(self.menu_price+value)[:9]
            self.composition=''
            return True
        if event.type==pg.KEYDOWN:
            if event.key==pg.K_BACKSPACE:
                if self.input_focus=='name':self.menu_name=self.menu_name[:-1]
                else:self.menu_price=self.menu_price[:-1]
            elif event.key==pg.K_TAB:self.input_focus='price' if self.input_focus=='name' else 'name'
            elif event.key==pg.K_RETURN:self.action(('save_menu',))
            elif event.key==pg.K_ESCAPE:self.input_focus=None;pg.key.stop_text_input()
            return True
        return False
