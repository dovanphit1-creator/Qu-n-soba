"""Web 2.0: one persistent room, physical interactions, phone applications."""
import math,sys
import pygame as pg
from app import App
from camera import CameraMixin,VIEW,ZOOM,KEYS
from model import vnd,STOCK_COST,DISH_COST,DRINKS,DIRT_POS,COOK_SECONDS,Bowl
from v2world import V2World,Fixture,FURNITURE,storage_for,WALL
from v2art import PixelArt,CREAM,INK

class V2App(PixelArt,CameraMixin,App):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.world=V2World();self.init_camera();self.owner.update(300,420);self.camera_origin=self.camera_goal()
  self.hand=None;self.escort=None;self.target=None;self.page=0;self.shop_page=0;self.furniture_page=0
  self.placing=None;self.place_point=(440,400);self.place_rot=0;self.name_value='';self.name_purpose=None
  self.history_period='day';self.calendar_offset=0;self.return_view=None;self.active_app=None;self.opened_before=False;self.pixel_animation=0
  self.modal='v2welcome';self.staff_panel=False;self.last_warning='';self.pointer_down=None;self.touch_anchor=None
 def camera_active(self):return hasattr(self,'owner') and self.modal is None
 def camera_free(self,p):return self.world.walkable(p,self.floor)
 def sync_shop_screen(self):
  if self.opened_before and not self.world.open and self.world.last_report:self.modal='v2report'
  self.opened_before=self.world.open;self.screen_open=self.world.open
 def text(self,value,xy,size=22,color=INK,bold=False,center=False):
  surface=self.font(size,bold).render(str(value),False,color);r=surface.get_rect()
  if center:r.center=(round(xy[0]),round(xy[1]))
  else:r.topleft=(round(xy[0]),round(xy[1]))
  self.canvas.blit(surface,r);return r
 def button(self,rect,label,action,enabled=True,color='#426f57',small=False):
  # The phone does not duplicate the physical clock or calendar.
  if action[0]=='staff_tab' and action[1] in ('clock','shifts'):return
  if action[0]=='shifts_view':return
  r=pg.Rect(rect);self.box(r,color if enabled else '#929e8b',2)
  self.text(label,r.center,17 if small else 22,'#fff3d5',True,True)
  if enabled:self.buttons.append((r,action))
 def world_point(self,logical):return (self.camera_origin.x+(logical[0]-VIEW.x)/ZOOM,self.camera_origin.y+(logical[1]-VIEW.y)/ZOOM)
 def near(self,p,d=150):return self.owner.distance_to(p)<=d
 def fixture_near(self,f):return f.floor==self.floor and self.owner.distance_to(f.rect.center)<=max(f.rect.w,f.rect.h)/2+125
 def warn(self,msg):self.world.note(msg);self.last_warning=msg
 def release_clean(self):self.clean_hold=None;self.world.player_cleaning=None
 def event(self,e):
  if e.type==pg.QUIT:self.running=False;return
  if e.type in (pg.FINGERDOWN,pg.FINGERUP,pg.FINGERMOTION):
   self.finger_events=True
   if e.type==pg.FINGERDOWN:
    if self.primary_finger is not None:return
    self.primary_finger=e.finger_id
   if e.finger_id!=self.primary_finger:return
   dw,dh=self.display.get_size();kind={pg.FINGERDOWN:pg.MOUSEBUTTONDOWN,pg.FINGERUP:pg.MOUSEBUTTONUP,pg.FINGERMOTION:pg.MOUSEMOTION}[e.type]
   if e.type==pg.FINGERUP:self.primary_finger=None
   e=pg.event.Event(kind,pos=(e.x*dw,e.y*dh),button=1)
  elif getattr(e,'touch',False) and self.finger_events:return
  if e.type==pg.WINDOWFOCUSLOST:
   self.cancel_movement();self.release_clean();self.pointer_down=None;self.primary_finger=None;self.down=None;self.pressed_action=None;return
  if e.type==pg.VIDEORESIZE:
   self.display=pg.display.set_mode((max(800,e.w),max(500,e.h)),pg.RESIZABLE);self.update_size();return
  if self.modal=='name':
   if e.type==pg.TEXTINPUT:self.name_value=(self.name_value+e.text)[:24]
   elif e.type==pg.KEYDOWN:
    if e.key==pg.K_BACKSPACE:self.name_value=self.name_value[:-1]
    elif e.key==pg.K_RETURN:self.action(('name_done',))
  elif self.modal=='phone_app' and self.active_app in ('menu','staff','shifts'):
   if self.shifts_input(e) or self.management_input(e):return
  if e.type==pg.KEYDOWN:
   if e.key==pg.K_ESCAPE:
    if self.placing:self.placing=None
    self.close_view();return
   if e.key in KEYS and self.modal is None:self.camera_keys.add(e.key)
   if e.key==pg.K_r and self.placing:self.place_rot=1-self.place_rot
   return
  if e.type==pg.KEYUP:self.camera_keys.discard(e.key);return
  if e.type not in (pg.MOUSEBUTTONDOWN,pg.MOUSEBUTTONUP,pg.MOUSEMOTION):return
  logical=App.point(self,e.pos);self.mouse=self.world_point(logical);self.camera_pointer=e.pos
  if e.type==pg.MOUSEMOTION:
   if self.placing and VIEW.collidepoint(logical):self.place_point=(round(self.mouse[0]/20)*20,round(self.mouse[1]/20)*20)
   if self.touch_anchor is not None:
    delta=pg.Vector2(logical)-self.touch_anchor
    self.camera_touch=tuple(delta.normalize()*min(1,delta.length()/50)) if delta.length()>7 else (0,0)
   return
  if getattr(e,'button',1)!=1:return
  if e.type==pg.MOUSEBUTTONDOWN:
   self.no_input_seconds=0;self.pointer_down=logical
   for r,act in reversed(self.buttons):
    if r.collidepoint(logical):self.pressed_action=act;return
   self.pressed_action=None
   if self.modal:return
   if self.placing:
    self.place_point=(round(self.mouse[0]/20)*20,round(self.mouse[1]/20)*20);self.touch_anchor=pg.Vector2(logical);self.camera_touch=(0,0);return
   target=self.hit(self.mouse)
   clean=self.clean_target(target)
   if clean:
    if self.start_clean_hold(clean):self.down=self.mouse
    return
   if target is None:self.touch_anchor=pg.Vector2(logical);self.camera_touch=(0,0)
  else:
   moved=self.touch_anchor is not None and pg.Vector2(logical).distance_to(self.touch_anchor)>7
   self.touch_anchor=None;self.camera_touch=None;self.move_direction.update(0,0)
   if self.clean_hold:self.release_clean();self.down=None;return
   act=getattr(self,'pressed_action',None);self.pressed_action=None
   if act:
    if any(r.collidepoint(logical) and a==act for r,a in self.buttons):self.action(act)
   elif not self.modal and not self.placing and not moved and self.pointer_down:
    self.interact(self.hit(self.mouse))
   self.pointer_down=None
 def close_view(self):
  self.modal=None;self.active_app=None;self.input_focus=None;pg.key.stop_text_input();self.cancel_movement()
 def cleaning_target(self,point):return self.clean_target(self.hit(point))
 def clean_target(self,target):
  if self.modal or self.hand or not target:return None
  kind,value=target
  if kind=='dirt' and self.near(self.world.dirt_point(value),90):return ('sweep',value)
  if kind=='fixture':
   f=self.world.by_id(value)
   if not f or not self.fixture_near(f):return None
   if f.kind=='sink' and (self.world.sink or self.world.washing):return ('wash',None)
   if f.table>=0:
    t=self.world.tables[f.table]
    if t.needs_wipe and not t.dirty:return ('wipe',f.table)
  return None
 def hit(self,p):
  w=self.world
  for gid,r in w.receipts.items():
   if r['location']=='floor' and r['pos'][2]==self.floor and math.dist(p,r['pos'][:2])<25:return ('floor_ticket',gid)
  for q in reversed(w.parcels):
   if not q['held'] and q['floor']==self.floor and math.dist(p,(q['x'],q['y']))<30:return ('parcel',q['id'])
  for b in reversed(w.bowls):
   if b.id==w.carried_bowl:continue
   pos=self.bowl_pos(b)
   if pos and math.dist(p,pos)<30:return ('bowl',b.id)
  for g in reversed(w.parties):
   if g.phase in ('seated','eating'):continue
   if self.floor==0 and pg.Rect(g.x-max(45,g.size*12+15),g.y-65,max(90,g.size*24+30),95).collidepoint(p):return ('guest',g.id)
  for f in reversed(w.fixtures):
   if f.floor==self.floor and f.rect.collidepoint(p):
    if f.kind=='stove':return ('pot',min(range(6),key=lambda i:math.dist(p,f.slot_point(i))))
    return ('fixture',f.id)
  if self.floor==0 and pg.Rect(220,245,140,60).collidepoint(p):return ('door',0)
  for d in w.dirt:
   if d//len(DIRT_POS)==self.floor and math.dist(p,w.dirt_point(d))<30:return ('dirt',d)
  return None
 def bowl_pos(self,b):
  if b.id in self.world.free_bowls:return self.world.free_bowls[b.id][:2] if self.world.free_bowls[b.id][2]==self.floor else None
  f=self.world.fixture('pass' if b.stage=='prep' else 'stove',self.floor)
  return f.slot_point(b.slot) if f else None
 def interaction(self,title,options):
  self.dialog_title=title;self.options=options;self.modal='interact';self.cancel_movement();self.page=0
 def interact(self,target):
  if not target:return
  w=self.world;kind,ident=target;self.target=target
  if kind=='floor_ticket':
   r=w.receipts[ident]
   if self.near(r['pos'][:2]):self.action(('take_floor_ticket',ident))
   return
  if kind=='door':
   if not self.near((290,290)):self.warn('Đến gần cửa để đổi biển.');return
   self.interaction('BIỂN TREO CỬA',[('Xác nhận đóng quán' if w.closing else 'Ngừng đón khách · dọn và đóng' if w.open else 'Lật biển · Mở quán',('door_toggle',))]);return
  if kind=='guest':
   p=w.group(ident)
   if not p:self.warn('Nhóm khách đã rời đi.');return
   if not self.near((p.x,p.y)):self.warn('Đến gần nhóm khách để nói chuyện.');return
   self.selected=p.id
   if p.phase in ('door','waiting'):
    self.interaction(f'Nhóm {p.id:03} · {p.size} người',[('Còn chỗ, mời khách vào',('answer',p.id,'accept')),('Hết chỗ, bạn có thể đợi không?',('answer',p.id,'wait')),('Hết nguyên liệu, hôm nay không nhận khách',('answer',p.id,'decline'))])
   elif p.phase=='ticket':self.interaction('Khách đưa phiếu ăn',[('Nhận phiếu từ tay khách',('take_ticket',p.id))])
   elif p.phase=='ready':self.interaction('Nhóm đã nhận phiếu',[('Dẫn nhóm tới bàn',('escort',p.id)),('Xem phiếu',('receipt',p.id))])
   else:self.warn('Khách đang chọn món hoặc xếp hàng mua phiếu.')
   return
  if kind=='parcel':
   p=next(q for q in w.parcels if q['id']==ident)
   if not self.near((p['x'],p['y'])):self.warn('Hãy đến gần thùng hàng.');return
   self.interaction('THÙNG HÀNG · '+self.parcel_name(p),[('Nhấc thùng lên',('take_parcel',ident))]);return
  if kind=='pot':
   f=w.fixture('stove',self.floor)
   if not f or not self.fixture_near(f):self.warn('Đến gần bếp để thao tác.');return
   if self.hand and self.hand['kind']=='ingredient' and self.hand['name']=='Mì tươi':self.apply_ingredient('pot',ident);return
   options=[('Vớt mì vào bát sạch',('lift',ident)),('Đổ bỏ mì trong nồi',('discard_pot',ident))]
   self.add_move(f,options);self.interaction('NỒI '+str(ident+1)+' · '+w.pot_state(ident),options);return
  if kind=='bowl':
   b=next(b for b in w.bowls if b.id==ident);pos=self.bowl_pos(b)
   if not self.near(pos,180):self.warn('Đến gần bát để thao tác.');return
   if self.hand and self.hand['kind']=='ingredient':self.apply_ingredient('bowl',ident);return
   if self.hand and self.hand['kind']=='ticket':
    gid=self.hand['gid'];b.ticket_gid=gid;w.receipts[gid]['location']='bowl';self.hand=None;self.warn('Đã bỏ phiếu vào bát. Hãy tự kiểm tra đúng món và đúng bàn.');return
   r=w.receipts.get(getattr(b,'ticket_gid',None));label='BÁT '+str(ident)+' · '+(r['table'] if r else 'Chưa ghép phiếu')
   self.interaction(label,[('Trong bát: '+(' + '.join(b.toppings) or 'Mì chưa thêm topping'),('dismiss',)),('Cầm bát',('take_bowl',ident)),('Đổ bỏ bát mì',('discard_bowl',ident))]);return
  if kind=='dirt':self.warn('Đến gần rồi ấn giữ vết bẩn để lau.');return
  f=w.by_id(ident)
  if not f:return
  if not self.fixture_near(f):self.warn('Hãy đi đến gần đồ vật.');return
  if f.table>=0:
   t=w.tables[f.table]
   if self.escort:
    if w.seat(self.escort,f.table):self.escort=None
    return
   if self.hand and self.hand['kind']=='bowl':
    b=next((b for b in w.bowls if b.id==self.hand['id']),None)
    waiting=[p for p in w.at_table(f.table) if p.phase=='seated' and len(p.meals)<p.size]
    if len(waiting)>1:self.interaction(f.name,[('Phục vụ nhóm '+str(p.id),('serve',f.table,p.id)) for p in waiting])
    else:self.serve_hand(f.table,waiting[0].id if waiting else None)
    return
   if self.hand and self.hand['kind']=='ingredient' and self.hand['name'] in DRINKS:
    self.apply_ingredient('drink',f.table);return
   options=[]
   if t.dirty:options.append(('Bê chồng bát bẩn',('take_dirty',f.table)))
   for p in w.at_table(f.table):options.append(('Phiếu nhóm '+str(p.id),('receipt',p.id)))
   if not options:options=[('Bàn sạch · '+str(t.capacity)+' ghế',('dismiss',))]
   self.add_move(f,options);self.interaction(f.name,options);return
  if self.hand and self.hand['kind']=='parcel':
   parcel=next(q for q in w.parcels if q['id']==self.hand['id'])
   if not parcel['name'].startswith('@'):
    if storage_for(parcel['name'])==f.kind and not f.opened:
     self.interaction('CẤT HÀNG',[('Mở tủ và cất thùng hàng',('open_store',f.id))]);return
    if w.unpack(parcel,f):self.hand=None
    return
  if f.kind in ('fridge','spice','drinks','bowls'):
   if not f.opened:options=[('Mở cánh / ngăn tủ',('cabinet',f.id,True))]
   else:
    options=[('Đóng tủ',('cabinet',f.id,False))]
    for n,q in w.stock.items():
     if q>0 and storage_for(n)==f.kind:options.append((f'{n} · còn {q} · lấy 1',('take_ingredient',n)))
    if self.hand and self.hand['kind']=='ingredient':options.insert(0,('Cất món đang cầm vào tủ',('return_ingredient',f.id)))
   self.add_move(f,options);self.interaction(FURNITURE[f.kind][0],options)
  elif f.kind=='board':
   options=[]
   if self.hand and self.hand['kind']=='ticket':options.append(('Dán lên',('pin_ticket',)))
   options += [(f"Đơn {r['number']:03} · {r['table']}",('receipt',gid)) for gid,r in w.receipts.items() if r['location']=='board']
   self.add_move(f,options);self.interaction('BẢNG ĐEN · PHIẾU ĂN',options or [('Chưa có phiếu được dán',('dismiss',))])
  elif f.kind=='pass':
   if self.hand and self.hand['kind']=='bowl':
    free=next((i for i in range(6) if not any(b.stage=='prep' and b.slot==i and b.id!=self.hand['id'] for b in w.bowls)),None)
    if free is None:self.warn('Bàn ra món đã đầy.');return
    if w.move_prep(self.hand['id'],free):w.free_bowls.pop(self.hand['id'],None);self.hand=None;w.carried_bowl=None
   else:
    options=[('Đặt bát, thêm topping rồi cầm phiếu chạm vào bát để ghép đơn.',('dismiss',))];self.add_move(f,options);self.interaction('BÀN RA MÓN',options)
  elif f.kind=='sink':
   if self.hand and self.hand['kind']=='dirty':w.sink+=self.hand['count'];w.carried_dirty=0;self.hand=None;self.warn('Đã đặt bát vào bồn. Ấn giữ để rửa.')
   else:
    options=[('Ấn giữ bồn để rửa bát',('dismiss',))];self.add_move(f,options);self.interaction('BỒN RỬA',options)
  elif f.kind=='clock':self.modal='physical_clock'
  elif f.kind=='calendar':self.modal='physical_calendar'
  elif f.kind=='rice':
   j=w.rice_jobs.get(f.id)
   options=[('Nấu cơm · 1 phần gạo · 5 phút',('rice_start',f.id))] if not j else [('Cầm bát cơm' if j['left']<=0 else 'Cơm đang nấu · '+str(math.ceil(j['left']))+'s',('rice_take',f.id))]
   self.add_move(f,options);self.interaction('NỒI CƠM ĐIỆN',options)
  else:
   options=[('Khách tự mua phiếu tại máy',('dismiss',))];self.add_move(f,options);self.interaction(FURNITURE[f.kind][0],options)
 def add_move(self,f,opts):
  if not self.world.open:opts.append(('Nhấc và sắp xếp lại',('move_fixture',f.id)))
 def parcel_name(self,p):return (FURNITURE[p['name'][1:]][0] if p['name'].startswith('@') else p['name'])+' ×'+str(p['qty'])
 def empty_hand(self):
  if self.hand:self.warn('Hãy đặt đồ đang cầm xuống trước.');return False
  return True
 def apply_ingredient(self,kind,ident):
  w=self.world;h=self.hand;n=h['name'];w.stock[n]+=1;w.stock_value[n]+=h['cost']
  ok=w.start_pot(ident) if kind=='pot' else w.topping(ident,n) if kind=='bowl' else w.serve_drink(n,ident,self.selected or None)
  if ok:self.hand=None
  else:w.stock[n]-=1;w.stock_value[n]-=h['cost']
 def serve_hand(self,index,gid):
  w=self.world;bid=self.hand['id'];b=next((b for b in w.bowls if b.id==bid),None);tag=getattr(b,'ticket_gid',None)
  if w.serve(bid,index,gid):
   self.hand=None;w.carried_bowl=None;w.free_bowls.pop(bid,None)
   if tag in w.receipts:w.receipts[tag]['location']='board' if w.fixture('board') else 'table'
  self.modal=None
 def request_name(self,title,value,purpose):
  self.name_value=value;self.name_purpose=purpose;self.name_title=title;self.modal='name';pg.key.start_text_input()
  if sys.platform=='emscripten':
   import platform
   platform.window.sobaText.request(title,value)
 def action(self,action):
  kind,*args=action;w=self.world
  if kind in ('dismiss','begin'):
   self.close_view();return
  if kind=='phone':self.modal='phone';self.active_app=None;self.cancel_movement();return
  if kind=='app':
   self.active_app=args[0];self.modal='phone_app';self.page=0;self.staff_panel=False
   if self.active_app=='shifts':self.shifts_view=False
   if self.active_app=='staff' and self.staff_tab in ('clock','shifts'):self.staff_tab='team'
   return
  if kind=='history_period':self.history_period=args[0];self.page=0;return
  if kind=='calendar_day':self.calendar_offset+=args[0];self.page=0;return
  if kind=='page_v2':self.page=max(0,self.page+args[0]);return
  if kind=='buy_fixture':w.buy_fixture(args[0]);return
  if kind=='buy':w.restock(*args);return
  if kind=='help_v2':self.modal='help_v2';return
  if kind=='door_toggle':
   if w.open:w.close_shop()
   else:w.open_shop()
   self.modal=None;return
  if kind=='answer':w.respond(*args);self.modal=None;return
  if kind=='take_ticket':
   if not self.empty_hand():return
   w.manual_receipt=True;ok=w.collect(args[0]);w.manual_receipt=False
   if ok:self.hand={'kind':'ticket','gid':args[0]};self.selected=args[0];self.modal='receipt';self.receipt_gid=args[0]
   return
  if kind=='receipt':self.receipt_gid=args[0];self.modal='receipt';return
  if kind=='get_ticket':
   if args[0] not in w.receipts or w.receipts[args[0]]['location'] not in ('board','table'):return
   if self.empty_hand():w.receipts[args[0]]['location']='hand';self.hand={'kind':'ticket','gid':args[0]};self.modal=None
   return
  if kind=='pin_ticket':
   if self.hand and self.hand['kind']=='ticket':w.receipts[self.hand['gid']]['location']='board';self.hand=None
   self.modal=None;return
  if kind=='escort':self.escort=args[0];self.selected=args[0];self.modal=None;return
  if kind=='take_parcel':
   if not self.empty_hand():return
   p=next((q for q in w.parcels if q['id']==args[0]),None)
   if p:p['held']=True;self.hand={'kind':'parcel','id':p['id']};self.modal=None
   return
  if kind=='open_parcel':
   if not self.hand or self.hand['kind']!='parcel':return
   p=next(q for q in w.parcels if q['id']==self.hand['id']);p['opened']=True
   if p['name'].startswith('@'):
    self.placing={'kind':p['name'][1:],'parcel':p['id']};self.place_rot=0;self.place_point=(round((self.owner.x+120)/20)*20,round(self.owner.y/20)*20)
   else:self.warn('Đã mở thùng. Mang tới tủ phù hợp, mở tủ và cất hàng.')
   self.modal=None;return
  if kind=='put_down':
   if not self.hand:return
   h=self.hand;pos=self.owner+self.move_direction*40 if self.move_direction.length_squared() else self.owner+pg.Vector2(0,35)
   pos=pg.Vector2(w.safe_point(pos,self.floor))
   if h['kind']=='parcel':
    p=next(q for q in w.parcels if q['id']==h['id']);p.update(x=pos.x,y=pos.y,floor=self.floor,held=False)
   elif h['kind']=='bowl':w.free_bowls[h['id']]=(pos.x,pos.y,self.floor);w.carried_bowl=None
   elif h['kind']=='ticket':
    w.receipts[h['gid']]['location']='floor';w.receipts[h['gid']]['pos']=(pos.x,pos.y,self.floor)
   elif h['kind']=='ingredient':
    w.parcels.append({'id':w.next_parcel,'name':h['name'],'qty':1,'cost':h['cost'],'x':pos.x,'y':pos.y,'floor':self.floor,'opened':True,'held':False});w.next_parcel+=1
   elif h['kind']=='dirty':self.warn('Bát bẩn cần đặt vào bồn rửa.');return
   self.hand=None;self.placing=None;return
  if kind=='take_floor_ticket':
   if self.empty_hand():self.hand={'kind':'ticket','gid':args[0]};w.receipts[args[0]]['location']='hand'
   return
  if kind=='move_fixture':
   if not self.empty_hand() or w.open:return
   f=w.by_id(args[0]);self.placing={'kind':f.kind,'moving':f.id};self.place_point=f.rect.topleft;self.place_rot=f.rot;self.modal=None;return
  if kind=='rotate':self.place_rot=1-self.place_rot;return
  if kind=='cancel_place':self.placing=None;return
  if kind=='place_confirm':
   if not self.placing:return
   k=self.placing['kind']
   if FURNITURE[k][3]:
    old=w.by_id(self.placing.get('moving'));self.request_name('Đặt tên cho bàn',old.name if old else '',('place_table',));return
   self.finish_place('');return
  if kind=='name_done':
   purpose=self.name_purpose;value=self.name_value.strip()
   if not value:self.warn('Vui lòng nhập tên.');return
   pg.key.stop_text_input()
   if purpose[0]=='place_table':self.finish_place(value)
   elif purpose[0]=='menu_field':
    if purpose[1]=='name':self.menu_name=value[:48]
    else:self.menu_price=''.join(c for c in value if c.isdigit())[:10]
    self.modal='phone_app'
   elif purpose[0]=='shift':self.shift_name=value;self.modal='phone_app'
   self.input_focus=None;return
  if kind=='cabinet':w.by_id(args[0]).opened=args[1];self.modal=None;return
  if kind=='open_store':
   f=w.by_id(args[0])
   if not f or not self.hand or self.hand['kind']!='parcel':self.modal=None;return
   p=next((q for q in w.parcels if q['id']==self.hand['id']),None)
   if not p:self.hand=None;self.modal=None;return
   f.opened=True;p['opened']=True
   if w.unpack(p,f):self.hand=None
   self.modal=None;return
  if kind=='take_ingredient':
   if not self.empty_hand():return
   n=args[0]
   if w.stock[n]>0:
    cost=w.unit_cost(n);w.stock[n]-=1;w.stock_value[n]-=cost;self.hand={'kind':'ingredient','name':n,'cost':cost};self.modal=None
   return
  if kind=='return_ingredient':
   if self.hand and self.hand['kind']=='ingredient' and w.by_id(args[0]) and storage_for(self.hand['name'])==w.by_id(args[0]).kind:
    h=self.hand;w.stock[h['name']]+=1;w.stock_value[h['name']]+=h['cost'];self.hand=None;self.modal=None
   return
  if kind=='lift':
   if self.empty_hand() and w.lift(args[0]):
    b=w.bowls[-1];self.hand={'kind':'bowl','id':b.id};w.carried_bowl=b.id;self.modal=None
   return
  if kind=='take_bowl':
   if not any(b.id==args[0] for b in w.bowls):self.warn('Bát đã được phục vụ hoặc chuyển đi.');self.modal=None;return
   if self.empty_hand():self.hand={'kind':'bowl','id':args[0]};w.carried_bowl=args[0];self.modal=None
   return
  if kind=='discard_pot':w.discard_pot(args[0]);self.modal=None;return
  if kind=='discard_bowl':w.discard_bowl(args[0]);w.free_bowls.pop(args[0],None);self.modal=None;return
  if kind=='take_dirty':
   if not self.empty_hand():return
   t=w.tables[args[0]]
   if t.dirty:self.hand={'kind':'dirty','count':t.dirty};w.carried_dirty=t.dirty;t.dirty=0;t.needs_wipe=True;self.modal=None
   return
  if kind=='serve':
   if self.hand and self.hand['kind']=='bowl':self.serve_hand(*args)
   return
  if kind=='rice_start':
   if w.stock.get('Gạo',0)>0 and args[0] not in w.rice_jobs:
    w.consume('Gạo');w.rice_jobs[args[0]]={'left':300};self.modal=None
   else:self.warn('Cần mua gạo và cất vào tủ lạnh trước.')
   return
  if kind=='rice_take':
   if self.empty_hand() and w.rice_jobs.get(args[0],{}).get('left',1)<=0 and w.clean:
    b=Bowl(w.next_bowl,0,False,['Cơm'],'lifted');w.next_bowl+=1;w.bowls.append(b);w.clean-=1;del w.rice_jobs[args[0]];self.hand={'kind':'bowl','id':b.id};w.carried_bowl=b.id;self.modal=None
   return
  if kind=='field':self.request_name('Tên món' if args[0]=='name' else 'Giá bán VND',self.menu_name if args[0]=='name' else self.menu_price,('menu_field',args[0]));return
  if kind=='shift_name':self.request_name('Tên ca làm việc',self.shift_name,('shift',));return
  if kind=='floor':
   self.floor=args[0];self.camera_floor=self.floor;self.owner.update(w.safe_point((300,420),self.floor));self.camera_origin=self.camera_goal();self.cancel_movement();return
  if kind=='presentation':self.return_view='phone';self.modal='presentation';return
  if kind=='music_toggle':
   if sys.platform=='emscripten':
    import platform
    platform.window.sobaAudio.toggleMusic()
   return
  if kind=='fullscreen':return
  if kind=='new':self.__init__(headless=False,persistent=False);return
  # Existing finance, contract, menu and staff operations remain connected to the simulation.
  App.action(self,action)
  if kind=='staff_tab':self.modal='phone_app';self.active_app='staff'
 def finish_place(self,name):
  p=self.placing
  if not p:return
  ghost=Fixture(-1,p['kind'],*self.place_point,self.floor,self.place_rot)
  if ghost.kind not in WALL and ghost.rect.inflate(20,20).collidepoint(self.owner):self.warn('Không đặt đồ lên vị trí chủ quán đang đứng.');self.modal=None;return
  f=self.world.place(p['kind'],*self.place_point,self.floor,self.place_rot,name,p.get('moving'))
  if f:
   if p.get('parcel'):self.world.parcels=[q for q in self.world.parcels if q['id']!=p['parcel']];self.hand=None
   self.placing=None;self.modal=None
 def step(self,dt):
  self.world.escorting=self.escort
  super().step(dt)
  if not self.world.open:self.animation+=dt
  if self.escort:
   p=self.world.group(self.escort)
   if not p or p.phase!='ready':self.escort=None
   else:
    delta=self.owner-pg.Vector2(p.x,p.y)
    p.walking=delta.length()>55
    if delta.length()>55:delta=delta.normalize()*min(delta.length()-55,120*dt);p.x+=delta.x;p.y+=delta.y
  if self.modal=='name' and sys.platform=='emscripten':
   import platform,json
   result=platform.window.sobaText.result
   if result:
    platform.window.sobaText.result='';data=json.loads(str(result))
    if data.get('cancel'):self.modal=None
    else:self.name_value=data['value'];self.action(('name_done',))
 def render_scene(self):
  w=self.world;self.room_art()
  self.text('ĐANG MỞ' if w.open and not w.closing else 'NGỪNG ĐÓN' if w.closing else 'ĐÓNG CỬA',(290,266),14,'#fff1bc',True,True)
  for d in w.dirt:
   if d//len(DIRT_POS)==self.floor:
    x,y=w.dirt_point(d);self.px((x-14,y-4,32,12),'#92734e');self.px((x-4,y-12,12,28),'#92734e')
  for f in sorted(w.fixtures,key=lambda f:f.rect.bottom):
   if f.floor!=self.floor:continue
   self.fixture_sprite(f)
   label=f.name if f.table>=0 else FURNITURE[f.kind][0]
   if self.fixture_near(f):
    width=min(260,len(label)*8+16);self.box((f.rect.centerx-width/2,f.rect.y-45,width,20),'#29463c',0);self.text(label,(f.rect.centerx,f.rect.y-35),12,CREAM,True,True)
   if f.kind=='stove':
    for i in range(6):
     pos=f.slot_point(i);state=w.pot_state(i)
     label=str(i+1)+' · '+('Trống' if state=='empty' else 'VỚT!' if state=='ready' else 'NHÃO' if state=='mushy' else str(math.ceil(COOK_SECONDS-w.pots[i]))+'s')
     self.text(label,(pos[0],pos[1]+24),11,'#f9ebba',True,True)
   if f.table>=0:
    t=w.tables[f.table]
    if t.dirty:self.pixel_bowl(*f.rect.center,dirty=True)
    elif t.needs_wipe:self.px((f.rect.centerx-12,f.rect.centery,28,8),'#92734e')
    self.text(f'{len(w.free_seats(f.table))}/{t.capacity} chỗ',(f.rect.centerx,f.rect.centery+20),12,INK,True,True)
  for b in w.bowls:
   if b.id==w.carried_bowl:continue
   pos=self.bowl_pos(b)
   if pos:
    self.pixel_bowl(*pos,b.toppings)
    if getattr(b,'ticket_gid',None):
     self.px((pos[0]+12,pos[1]-22,16,20),'#fff3c9')
     r=w.receipts.get(b.ticket_gid)
     if r:self.text(f"{r['number']:03} · {r['table']}",(pos[0],pos[1]+27),11,INK,True,True)
  if self.floor==0:
   for p in w.parties:
    if p.phase in ('seated','eating'):continue
    for j in range(p.size):self.person(p.x+(j-(p.size-1)/2)*24,p.y+(j%2)*8,'#7e94af',self.animation*5 if getattr(p,'walking',False) else 0,variant=p.id+j)
    self.text(f'N{p.id:03} · {p.size} người',(p.x,p.y-65),14,INK,True,True)
    if p.phase=='ticket':self.px((p.x+14,p.y-28,16,24),'#fff1ba')
   for person in w.walkers:
    for j in range(person['size']):self.person(person['x']+j*28,person['y'],'#b48672',self.animation*6+j)
   if w.truck:
    age=w.truck['age'];x=-220+min(age/4,1)*520 if age<12 else 300+(age-12)*300
    self.truck_sprite(x,94)
    if 4<=age<=12:
     frac=min(1,(age-4)/4) if age<8 else max(0,(12-age)/4)
     self.person(440,154+frac*55,'#cfaa64',self.animation*5)
     if age<9:self.parcel_sprite({'x':452,'y':162+frac*55})
  for i,t in enumerate(w.tables):
   if t.floor!=self.floor:continue
   x,y=w.table_position(i)
   for p in w.at_table(i):
    for j,seat in enumerate(p.seats):
     angle=-math.pi/2+seat*math.tau/t.capacity;xx=x+math.cos(angle)*57;yy=y+math.sin(angle)*57
     self.person(xx,yy,'#9e85a0',variant=p.id+j)
     if j<len(p.meals):self.pixel_bowl(xx,yy+20,p.meals[j]['toppings'])
    self.text(f'N{p.id:03}',(x,y-4),13,INK,True,True)
  for e in w.employees:
   if e['present'] and e['floor']==self.floor:
    self.person(e['x'],e['y'],'#d3ac67' if e['role']=='baito' else '#b7cbbc',self.animation*5,action=e.get('job',{}).get('action',[''])[0] if e.get('job') else None);self.text(e['name'],(e['x'],e['y']-58),12,INK,center=True)
    if e.get('job') and e['job']['action'][0] in ('serve','prep','clear'):self.pixel_bowl(e['x'],e['y']-12,dirty=e['job']['action'][0]=='clear')
  for p in w.parcels:
   if not p['held'] and p['floor']==self.floor:self.parcel_sprite(p)
  for gid,r in w.receipts.items():
   if r['location']=='floor' and r['pos'][2]==self.floor:self.px((r['pos'][0]-8,r['pos'][1]-12,16,24),'#fff0ba')
  self.person(self.owner.x,self.owner.y,'#3f8e79',self.animation*7 if self.camera_keys or self.camera_touch else 0)
  if self.hand:
   if self.hand['kind']=='bowl':self.pixel_bowl(self.owner.x,self.owner.y-12)
   elif self.hand['kind']=='parcel':self.parcel_sprite({'x':self.owner.x,'y':self.owner.y-12})
   elif self.hand['kind']=='ticket':self.px((self.owner.x+12,self.owner.y-28,16,24),'#fff3ca')
   else:self.px((self.owner.x+12,self.owner.y-20,20,20),'#e9c37c')
  if self.placing:
   p=self.placing;f=Fixture(-1,p['kind'],*self.place_point,self.floor,self.place_rot)
   error=w.placement_error(f,p.get('moving'),paths=False);r=f.rect
   self.fixture_sprite(f);pg.draw.rect(self.canvas,'#cb7252' if error else '#61a986',r,4)
  crop=pg.Rect(round(self.camera_origin.x),round(self.camera_origin.y),round(VIEW.width/ZOOM),round(VIEW.height/ZOOM))
  self.canvas.blit(pg.transform.scale(self.canvas.subsurface(crop).copy(),VIEW.size),VIEW)
  if self.move_direction.length_squared():
   c=pg.Vector2(VIEW.x,VIEW.y)+(self.owner-self.camera_origin)*ZOOM;d=self.move_direction;s=pg.Vector2(-d.y,d.x)
   pg.draw.polygon(self.canvas,'#f8e7af',[c+d*65,c+d*42+s*10,c+d*42-s*10])
 def panel(self,title,phone=False):
  shade=pg.Surface((1600,1000),pg.SRCALPHA);shade.fill((14,31,26,170));self.canvas.blit(shade,(0,0));self.buttons=[]
  r=(28,105,1544,827) if phone else (280,145,1040,715)
  self.box(r,'#233f38',16);self.box(pg.Rect(r).inflate(-20,-20),'#f1e5c7',10)
  self.text(title,(800,165 if phone else 200),30,INK,True,True)
  self.button((1330,125,195,44) if phone else (635,787,330,48),'Đóng điện thoại' if phone else 'Trở lại quán',('dismiss',),small=True)
 def pager(self,total,size=7,y=830):
  self.button((70,y,150,40),'Trước',('page_v2',-1),self.page>0,small=True)
  self.button((230,y,150,40),'Sau',('page_v2',1),(self.page+1)*size<total,small=True)
 def render_phone(self):
  w=self.world
  if self.modal=='phone':
   shade=pg.Surface((1600,1000),pg.SRCALPHA);shade.fill((14,31,26,150));self.canvas.blit(shade,(0,0));self.buttons=[]
   self.box((460,110,680,790),'#263e36',24);self.box((480,130,640,750),'#b5cbb4',15)
   self.text(w.now.strftime('%H:%M'),(515,155),22,INK,True);self.text('QUÁN MÌ CỦA TÔI',(800,230),27,INK,True,True)
   apps=[('market','Chợ'),('furniture','Nội thất'),('staff','Nhân sự'),('shifts','Tạo ca'),('menu','Thực đơn'),('supplier','Nhà cung cấp'),('finance','Tài chính'),('history','Sổ kinh doanh'),('settings','Cài đặt')]
   colors=['#c58b58','#aa7855','#669085','#8d90ac','#b5a160','#669889','#7187a2','#aa8572','#789577']
   for i,(key,label) in enumerate(apps):
    x=510+i%3*200;y=290+i//3*165
    self.box((x+25,y,115,100),colors[i],9);self.draw_app_icon(key,x+80,y+48)
    self.text(label,(x+82,y+127),19,INK,True,True)
    self.buttons.append((pg.Rect(x,y,165,150),('app',key)))
   self.button((620,817,360,40),'Cất điện thoại',('dismiss',),small=True);return
  self.panel({'market':'CHỢ · ĐẶT HÀNG GIAO TẬN CỬA','furniture':'CỬA HÀNG NỘI THẤT','staff':'NHÂN SỰ','shifts':'TẠO CA LÀM VIỆC','menu':'THỰC ĐƠN','supplier':'NHÀ CUNG CẤP','finance':'TÀI CHÍNH','history':'SỔ KINH DOANH','settings':'CÀI ĐẶT'}.get(self.active_app,''),True)
  self.button((65,125,210,44),'Màn hình ứng dụng',('phone',),small=True)
  self.text('Ngân sách · '+vnd(w.cash),(65,225),26,INK,True)
  if self.active_app in ('market','furniture'):
   items=list(FURNITURE) if self.active_app=='furniture' else ['Bát/đĩa',*STOCK_COST]
   self.text('Xe giao tới cửa → cầm thùng → mở → tự sắp xếp. Chỉ đặt mua khi quán đã đóng.',(65,280),22)
   for i,n in enumerate(items[self.page*7:self.page*7+7]):
    y=340+i*65
    if self.active_app=='furniture':
     label,cost,_,_=FURNITURE[n];act=('buy_fixture',n)
    else:label=n;cost=DISH_COST if n=='Bát/đĩa' else STOCK_COST[n];act=('buy',n,1)
    self.text(label,(80,y+12),23,INK,True);self.text(vnd(cost),(710,y+15),21)
    self.button((1030,y,210,47),'Đặt 1',act,not w.open and w.cash>=cost and (self.active_app!='furniture' or not w.already_owned(n)),small=True)
    if self.active_app=='market':self.button((1260,y,235,47),'Đặt 10 · '+vnd(cost*10),('buy',n,10),not w.open and w.cash>=cost*10,small=True)
   self.pager(len(items))
   self.text(f'Đang chờ xe: {len(w.shipments)} đơn · Thùng chưa cất: {len(w.parcels)}',(500,840),19)
  elif self.active_app=='menu':self.render_menu()
  elif self.active_app=='supplier':self.render_supplier()
  elif self.active_app=='staff':self.render_staff()
  elif self.active_app=='shifts':self.shifts_view=False;self.render_shifts()
  elif self.active_app=='finance':self.render_finance()
  elif self.active_app=='history':
   for i,(k,label) in enumerate([('day','Ngày'),('month','Tháng'),('year','Năm')]):self.button((70+i*170,275,150,40),label,('history_period',k),small=True)
   for i,(key,row) in enumerate(list(reversed(sorted(w.totals(self.history_period).items())))[self.page*7:self.page*7+7]):
    self.text(key,(75,330+i*65),23,INK,True);self.text('Doanh thu '+vnd(row.get('revenue',0))+' · Lãi '+vnd(row.get('profit',0)),(370,330+i*65),23)
   self.pager(len(w.totals(self.history_period)))
  elif self.active_app=='settings':
   self.button((400,345,800,65),'Màn hình / nhạc',('presentation',))
   self.button((400,435,800,65),'Cách chơi 2.1',('help_v2',))
   if w.floors<3:self.button((400,525,800,65),'Xây thêm tầng · '+vnd({1:3000000,2:5000000}[w.floors]),('build_floor',),not w.open)
 def draw_app_icon(self,key,x,y):
  # Distinct small pixel symbols for each application.
  c='#fff0d0'
  if key=='market':
   self.px((x-32,y-12,64,32),c);self.px((x-20,y+24,12,12),c);self.px((x+16,y+24,12,12),c);self.px((x-40,y-28,12,20),c)
  elif key=='furniture':self.px((x-32,y-12,64,20),c);self.px((x-28,y+8,8,32),c);self.px((x+20,y+8,8,32),c)
  elif key=='staff':self.disk((x,y-16),16,c);self.px((x-24,y+4,48,28),c)
  elif key in ('menu','history'):
   self.px((x-28,y-32,56,68),c)
   for yy in range(-20,28,12):self.px((x-16,y+yy,32,4),'#687d60')
  elif key=='shifts':
   self.px((x-30,y-30,60,60),c);self.px((x-22,y-22,44,12),'#7f8b9c')
   for xx in range(-16,24,16):self.px((x+xx,y+4,8,12),'#7f8b9c')
  elif key=='supplier':self.px((x-32,y-20,48,44),c);self.px((x+16,y-8,20,32),c);self.disk((x-16,y+28),8,c);self.disk((x+24,y+28),8,c)
  elif key=='finance':self.px((x-32,y-24,64,52),c);self.disk((x,y),12,'#7187a2')
  else:
   for i in range(3):self.px((x-32,y-24+i*24,64,4),c);self.px((x-20+i*16,y-28+i*24,12,12),c)
 def render_ui(self):
  w=self.world;m=self.modal
  if m in ('phone','phone_app'):self.render_phone();return
  if m=='presentation':
   self.panel('MÀN HÌNH / ÂM THANH')
   self.wrap('Bấm toàn màn hình để thử mở ngang trên điện thoại. Nếu trình duyệt không cho phép, xoay máy ngang và thêm game vào Màn hình chính.',(345,295),910,24)
   self.button((380,535,390,60),'Bật / tắt nhạc nền',('music_toggle',))
   r=pg.Rect(830,535,390,60);self.button(r,'Toàn màn hình',('fullscreen',))
   if sys.platform=='emscripten':
    import platform,json
    platform.window.sobaFullscreenRect=json.dumps([self.offset[0]+r.x*self.scale,self.offset[1]+r.y*self.scale,r.w*self.scale,r.h*self.scale])
   return
  if m in ('v2welcome','help_v2'):
   self.panel('QUÁN MÌ CỦA TÔI · 2.1.0')
   lines=['Bạn có 10 triệu VND và một quán trống. Mở điện thoại để đặt mua đồ.',
    'Xe giao thùng trước cửa. Đến gần → nhận → mở thùng → đặt đồ hoặc cất vào tủ.',
    'Mua bộ bàn ghế, máy vé, bếp, bàn ra món, tủ lạnh, tủ gia vị, tủ bát và bồn rửa.',
    'Đặt bàn phải có tên. Chạm sàn, giữ và kéo để đi; đến gần đồ vật để dùng.',
    'Mở tủ lấy mì → thả vào nồi → vớt → đặt ở bàn ra món → thêm topping.',
    'Nhận phiếu từ khách, dẫn tới bàn; mang phiếu tới bảng đen để dán.',
    'Cầm phiếu chạm bát để ghép đơn, rồi bưng tới đúng bàn. Có thể ghép nhầm!',
    'Điện thoại quản lý quán. Cửa / biển đổi trạng thái. Game không tạm dừng.',
    'Web không lưu: tải lại trang sẽ bắt đầu ván mới.']
   for i,line in enumerate(lines):self.wrap(line,(325,275+i*51),950,20)
   return
  if m=='name':
   self.panel(self.name_title);self.box((355,340,890,70),'#fffaf0',2);self.text(self.name_value+'|',(375,362),27)
   self.text('Nhập tên rồi xác nhận. Tên bàn không được trùng.',(355,450),22)
   self.button((515,570,570,65),'Xác nhận',('name_done',));return
  if m=='interact':
   self.panel(self.dialog_title)
   for i,(label,act) in enumerate(self.options[self.page*6:self.page*6+6]):self.button((340,280+i*74,920,60),label,act,small=True)
   if len(self.options)>6:
    self.button((350,740,180,40),'Trước',('page_v2',-1),self.page>0,small=True);self.button((1060,740,180,40),'Sau',('page_v2',1),(self.page+1)*6<len(self.options),small=True)
   return
  if m=='receipt':
   self.panel('PHIẾU ĂN')
   r=w.receipts.get(self.receipt_gid);p=w.group(self.receipt_gid)
   if not r:self.text('Không tìm thấy phiếu.',(355,300),24);return
   if not p:
    from types import SimpleNamespace
    p=SimpleNamespace(id=r['gid'],orders=r['orders'],recipes=r['recipes'],drinks=r['drinks'],phase='done')
   self.text(f"ĐƠN {r['number']:03} · {r['day']} · Nhóm {p.id:03}",(345,270),24,INK,True)
   self.text('BÀN: '+r['table'],(345,310),25,'#577654',True)
   for i,n in enumerate(p.orders):
    self.text(f'{i+1}. {n}',(345,365+i*69),22,INK,True)
    self.text(' + '.join(p.recipes[i]),(365,395+i*69),17)
   self.text('Uống: '+', '.join(d for d in p.drinks if d),(345,657),19)
   if r['location'] in ('board','table'):self.button((345,708,370,50),'Cầm phiếu',('get_ticket',p.id),small=True)
   if p.phase=='ready':self.button((760,708,480,50),'Dẫn khách tới bàn',('escort',p.id),small=True)
   elif w.refund_amount(p.id):self.button((760,708,480,50),'Hết nguyên liệu · Hoàn tiền',('refund_review',p.id),small=True)
   return
  if m=='physical_clock':
   self.panel('MÁY CHẤM CÔNG · LƯỢT GHI NHẬN')
   for i,r in enumerate(list(reversed(w.clock_events))[self.page*8:self.page*8+8]):self.text(r['at'][:16]+' · '+r['name']+' · '+r['event'],(320,290+i*48),20)
   if not w.clock_events:self.text('Chưa có lượt chấm công.',(340,310),24)
   self.physical_footer();return
  if m=='physical_calendar':
   from datetime import timedelta
   day=w.now.date()+timedelta(days=self.calendar_offset)
   self.panel('LỊCH CA LÀM VIỆC · '+day.strftime('%d/%m/%Y'))
   self.button((340,235,200,38),'Ngày trước',('calendar_day',-1),small=True)
   self.button((1020,235,200,38),'Ngày sau',('calendar_day',1),small=True)
   for i,e in enumerate(w.employees[self.page*7:self.page*7+7]):
    p=w.day_plan(e,day);self.text(e['name']+' · '+p.get('shift_name','Chưa có ca'),(325,290+i*57),21,INK,True)
    self.text(('Nghỉ' if not p['segments'] else f"{p['start']//60:02}:{p['start']%60:02} – {p['end']//60:02}:{p['end']%60:02}"),(920,290+i*57),20)
   if not w.employees:self.text('Chưa tuyển nhân viên.',(340,310),24)
   self.physical_footer();return
  if m=='v2report':
   self.panel('TỔNG KẾT CA · QUÁN ĐÃ ĐÓNG')
   r=w.last_report or {}
   for i,(label,key) in enumerate([('Doanh thu','revenue'),('Nguyên liệu sử dụng','ingredients'),('Điện / nước / ga','utilities'),('Tiền lương','wages'),('Lợi nhuận','profit')]):self.text(label+': '+vnd(r.get(key,0)),(365,290+i*70),26)
   self.text(f"Khách hôm nay: {r.get('customers',0)} · Sao trung bình: {r.get('average_stars') or 0:.2f}/5",(365,675),23)
   return
  if m:App.render_modal(self)
 def physical_footer(self):
  self.button((340,710,160,45),'Trước',('page_v2',-1),self.page>0,small=True)
  total=len(self.world.clock_events) if self.modal=='physical_clock' else len(self.world.employees)
  self.button((515,710,160,45),'Sau',('page_v2',1),(self.page+1)*7<total,small=True)
  if not self.world.open and self.target and self.target[0]=='fixture':self.button((825,710,420,45),'Di chuyển đồ vật',('move_fixture',self.target[1]),small=True)
 def draw(self):
  self.buttons=[];self.render_scene()
  self.box((0,0,1600,96),'#29463c',0)
  self.text('Quán Mì Của Tôi',(24,15),29,CREAM,True)
  self.text(w:=self.world.now.strftime('%d/%m/%Y · %H:%M · VN'),(24,59),18,'#b8cbaa')
  self.text(vnd(self.world.cash),(640,22),25,'#f3cf89',True)
  self.text(f'Danh tiếng {self.world.reputation:.1f}% · Bát sạch {self.world.clean}',(640,60),18,'#c7d7b4')
  for floor in range(self.world.floors):self.button((1080+floor*68,22,60,48),f'T{floor+1}',('floor',floor),small=True)
  self.button((1430,118,142,80),'ĐIỆN THOẠI',('phone',),small=True)
  # Pixel handset icon rather than a permanent management sidebar.
  self.px((1488,208,30,48),'#203d35');self.px((1492,212,22,32),'#c9dcaf');self.px((1500,248,6,4),'#d9e8ba')
  self.box((15,949,1570,37),'#29463c',0)
  msg=self.world.logs[-1] if self.world.logs else 'Chạm sàn trống, giữ và kéo để di chuyển. Mở điện thoại để bắt đầu.'
  self.text(msg[:135],(27,958),17,CREAM)
  self.text('Phiên bản 2.1.0 · Nhà phát hành Đỗ Văn Phi',(800,994),12,'#596b56',center=True)
  if self.hand:
   h=self.hand;label={'parcel':'Thùng hàng','bowl':'Bát '+str(h.get('id','')),'ticket':'Phiếu nhóm '+str(h.get('gid','')),'ingredient':h.get('name',''),'dirty':'Chồng bát bẩn'}[h['kind']]
   if h['kind']=='bowl':
    b=next((b for b in self.world.bowls if b.id==h['id']),None);r=self.world.receipts.get(getattr(b,'ticket_gid',None))
    if r:label+=' → '+r['table']
   self.box((1130,775,450,162),'#29463c',2);self.text('ĐANG CẦM · '+label,(1150,790),19,CREAM,True)
   self.button((1145,831,190,44),'Đặt xuống',('put_down',),small=True)
   if h['kind']=='parcel':self.button((1350,831,215,44),'Mở thùng',('open_parcel',),small=True)
   if h['kind']=='ticket':self.button((1350,831,215,44),'Xem phiếu',('receipt',h['gid']),small=True)
  if self.placing:
   self.button((370,860,225,65),'Xoay 90°',('rotate',),small=True)
   self.button((610,860,280,65),'Đặt tại đây',('place_confirm',),small=True)
   self.button((905,860,180,65),'Hủy',('cancel_place',),small=True)
  if self.modal:self.render_ui()
  if sys.platform=='emscripten' and self.modal!='presentation':
   import platform
   platform.window.sobaFullscreenRect=''
  self.update_size();self.display.fill('#18291e');self.display.blit(pg.transform.scale(self.canvas,(int(1600*self.scale),int(1000*self.scale))),self.offset);pg.display.flip()
