"""Physical inventory, deliveries and receipts for the disposable web edition."""
import math
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import pygame as pg
from model import World,Table,STOCK_COST,DISH_COST,DRINKS

# name, price, footprint, capacity (tables only)
FURNITURE={
 'round1':('Bàn tròn · 1 ghế',180000,(112,112),1),
 'round2':('Bàn tròn · 2 ghế',260000,(128,128),2),
 'round3':('Bàn tròn · 3 ghế',340000,(144,144),3),
 'square4':('Bàn vuông · 4 ghế',420000,(152,152),4),
 'ticket':('Máy bán phiếu ăn',850000,(80,96),0),
 'clock':('Máy chấm công',90000,(64,40),0),
 'calendar':('Lịch ca làm việc',30000,(64,40),0),
 'board':('Bảng đen phiếu ăn',150000,(160,40),0),
 'sink':('Bồn rửa bát',350000,(152,88),0),
 'bowls':('Tủ bát sạch',180000,(112,80),0),
 'drinks':('Tủ đồ uống',280000,(96,96),0),
 'stove':('Bếp luộc mì · 6 ô',950000,(240,128),0),
 'rice':('Nồi cơm điện bàn',180000,(80,80),0),
 'pass':('Bàn hoàn thiện / ra món',420000,(240,112),0),
 'fridge':('Bàn có tủ lạnh',650000,(160,96),0),
 'spice':('Tủ ngăn gia vị',220000,(144,80),0),
}
SPICES={'Hành','Kaeshi','Vị cay','Bột ớt','Nori'}
WALL={'board','calendar','clock'}
def storage_for(name):
 if name=='Bát/đĩa':return 'bowls'
 if name in DRINKS:return 'drinks'
 return 'spice' if name in SPICES else 'fridge'

@dataclass
class Fixture:
 id:int;kind:str;x:int;y:int;floor:int=0;rot:int=0;name:str='';opened:bool=False;table:int=-1
 @property
 def rect(self):
  w,h=FURNITURE[self.kind][2]
  return pg.Rect(self.x,self.y,h if self.rot else w,w if self.rot else h)
 def slot_point(self,index):
  r=self.rect;u=.17+(index%3)*.33
  v=(.26+(index//3)*.24) if self.kind=='stove' else (.10+(index//3)*.14)
  return (r.x+u*r.w,r.y-24+(r.h+24)*v)
 def point(self,u=.5,v=.5):
  r=self.rect
  return (r.x+(1-v if self.rot else u)*r.w,r.y+(u if self.rot else v)*r.h)

class V2World(World):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.tables=[];self.fixtures=[];self.next_fixture=1
  self.shipments=[];self.parcels=[];self.next_parcel=1;self.truck=None
  self.receipts={};self.day_orders={};self.carried_bowl=None;self.carried_dirty=0
  self.manual_receipt=False;self.rice_jobs={};self.free_bowls={};self.dirt_locations={}
 def fixture(self,kind,floor=None):return next((f for f in self.fixtures if f.kind==kind and (floor is None or f.floor==floor)),None)
 def by_id(self,fid):return next((f for f in self.fixtures if f.id==fid),None)
 def table_fixture(self,index):return next((f for f in self.fixtures if f.table==index),None)
 def table_position(self,index):
  f=self.table_fixture(index)
  return f.rect.center if f else super().table_position(index)
 def table_name(self,index):
  f=self.table_fixture(index);return f.name if f else 'Chưa xếp bàn'
 def machine_target(self,phase,index=0):
  f=self.fixture('ticket',0)
  return (f.rect.centerx,f.rect.bottom+50+index*36) if f else (650,374)
 def walkable(self,p,floor=0,fixtures=None):
  x,y=p
  if not(40<=x<=1560 and 170<=y<=930):return False
  if 244<=y<=282 and not 220<=x<=360:return False
  return not any(f.floor==floor and f.kind not in WALL and f.rect.inflate(20,20).collidepoint(p) for f in (fixtures if fixtures is not None else self.fixtures))
 def safe_point(self,p,floor=0):
  if self.walkable(p,floor):return tuple(p)
  if not hasattr(self,'_safe_cache'):self._safe_cache={}
  key=(round(p[0]),round(p[1]),floor)
  if key not in self._safe_cache:
   candidates=[(x,y) for x in range(60,1541,20) for y in range(180,921,20) if self.walkable((x,y),floor)]
   self._safe_cache[key]=min(candidates,key=lambda q:math.dist(p,q)) if candidates else (300,300)
  return self._safe_cache[key]
 def parcel_position(self):
  occupied=[(p['x'],p['y']) for p in self.parcels if not p['held'] and p['floor']==0]
  for y in (205,175):
   for x in range(420,1510,55):
    if all(math.dist((x,y),q)>=32 for q in occupied):return x,y
  # Extra loads remain on the truck until a delivery space is free.
  return None
 def navigate(self,key,position,target,dt,floor=0):
  import heapq
  start=self.safe_point(position,floor);goal=self.safe_point(target,floor)
  if not hasattr(self,'_routes'):self._routes={}
  cache=self._routes.get(key)
  signature=(round(goal[0]/20),round(goal[1]/20),floor,len(self.fixtures))
  if not cache or cache[0]!=signature:
   def cell(p):return (round(p[0]/20)*20,round(p[1]/20)*20)
   a=cell(self.safe_point(start,floor));b=cell(goal)
   frontier=[(0,a)];cost={a:0};parent={a:None};end=None
   while frontier:
    _,cur=heapq.heappop(frontier)
    if math.dist(cur,b)<=28:end=cur;break
    for q in ((cur[0]+20,cur[1]),(cur[0]-20,cur[1]),(cur[0],cur[1]+20),(cur[0],cur[1]-20)):
     if not self.walkable(q,floor):continue
     c=cost[cur]+20
     if c<cost.get(q,float('inf')):cost[q]=c;parent[q]=cur;heapq.heappush(frontier,(c+math.dist(q,b),q))
   if end is None:return start
   route=[]
   while end is not None:route.append(end);end=parent[end]
   route.reverse();route.append(goal)
   self._routes[key]=(signature,route);cache=self._routes[key]
  route=cache[1];pos=pg.Vector2(start);budget=max(0,dt)*130
  while route and budget>0:
   delta=pg.Vector2(route[0])-pos;dist=delta.length()
   if dist<=budget:pos.update(route.pop(0));budget-=dist
   else:pos+=delta/dist*budget;budget=0
  return pos.x,pos.y
 def move_guest(self,p,target,dt):
  if getattr(self,'escorting',None)==p.id:return
  before=(p.x,p.y)
  if p.phase in ('door','waiting') or (p.phase=='leaving' and p.y<243):
   delta=pg.Vector2(target)-pg.Vector2(p.x,p.y)
   if delta.length():delta.scale_to_length(min(delta.length(),dt*145));p.x+=delta.x;p.y+=delta.y
  else:p.x,p.y=self.navigate(('guest',p.id),(p.x,p.y),target,dt,self.tables[p.table].floor if p.table>=0 and p.phase in ('seated','eating') else 0)
  p.walking=math.dist(before,(p.x,p.y))>.1
 def move_employee(self,e,job,dt):
  tx,ty,floor=job['target']
  if e['floor']!=floor:e['floor']=floor;e['x'],e['y']=self.safe_point((300,320),floor)
  e['x'],e['y']=self.navigate(('staff',e['id']),(e['x'],e['y']),(tx,ty),dt,floor)
  if math.dist((e['x'],e['y']),self.safe_point((tx,ty),floor))>8:job['left']=max(job['left'],.1)
 def placement_error(self,f,ignore=None,paths=True):
  r=f.rect
  if not pg.Rect(40,292,1520,628).contains(r):return 'Đặt đồ bên trong quán.'
  if f.kind in WALL and not(r.top<=312 or r.left<=60 or r.right>=1540):return 'Đồ treo tường phải sát một bức tường.'
  if r.colliderect(pg.Rect(215,280,170,90)):return 'Chừa lối ra vào trước cửa.'
  others=[o for o in self.fixtures if o.id!=ignore]
  if any(o.floor==f.floor and r.inflate(12,12).colliderect(o.rect) for o in others):return 'Vị trí này đè lên đồ khác.'
  if not paths:return ''
  layout=others+[f];seen={(300,300)};queue=deque(seen)
  while queue:
   x,y=queue.popleft()
   for p in ((x+20,y),(x-20,y),(x,y+20),(x,y-20)):
    if p not in seen and self.walkable(p,f.floor,layout):seen.add(p);queue.append(p)
  for o in layout:
   if o.floor!=f.floor:continue
   if not any(o.rect.inflate(105,105).collidepoint(p) for p in seen):return 'Đồ này làm mất lối đi tới một khu thao tác.'
  return ''
 def place(self,kind,x,y,floor=0,rot=0,name='',moving=None):
  if self.open:self.note('Chỉ sắp xếp nội thất sau khi đóng quán.');return None
  if kind not in FURNITURE:return None
  if FURNITURE[kind][3] and (not name.strip() or any(f.name.casefold()==name.strip().casefold() and f.id!=moving for f in self.fixtures if f.table>=0)):
   self.note('Tên bàn không được trống hoặc trùng.');return None
  f=Fixture(moving or self.next_fixture,kind,int(x),int(y),floor,rot,name.strip()[:24])
  error=self.placement_error(f,moving)
  if error:self.note(error);return None
  if moving:
   old=self.by_id(moving);f.table=old.table;self.fixtures.remove(old)
   if f.table>=0:self.tables[f.table].floor=floor
  else:
   self.next_fixture+=1
   if FURNITURE[kind][3]:
    f.table=len(self.tables);self.tables.append(Table(FURNITURE[kind][3],floor=floor,slot=f.table%6))
  self._routes={};self._safe_cache={};self.fixtures.append(f);self.note('Đã đặt '+(f.name or FURNITURE[kind][0]));return f
 def queue_goods(self,items,costs=None,label='Đơn mua lẻ'):
  self.shipments.append({'items':dict(items),'costs':costs or {},'label':label})
 def already_owned(self,kind):
  if FURNITURE[kind][3]:return False
  return bool(self.fixture(kind) or any(p['name']=='@'+kind for p in self.parcels) or any('@'+kind in o['items'] for o in self.shipments) or (self.truck and any('@'+kind in o['items'] for o in self.truck['orders'])))
 def buy_fixture(self,kind):
  if self.open or kind not in FURNITURE:self.note('Đóng quán trước khi đặt nội thất.');return False
  if self.already_owned(kind):self.note('Bạn đã mua thiết bị này. Hãy kiểm tra hàng giao hoặc nội thất đã đặt.');return False
  cost=FURNITURE[kind][1]
  if self.cash<cost:self.note('Không đủ ngân sách.');return False
  self.cash-=cost;self.record('equipment',cost);self.queue_goods({'@'+kind:1},label=FURNITURE[kind][0]);self.note('Đã đặt hàng. Xe sẽ giao trước cửa.');return True
 def restock(self,name,count=10):
  if self.open:self.note('Đóng quán trước khi đặt hàng mua lẻ.');return False
  if name not in (*STOCK_COST,'Bát/đĩa') or not isinstance(count,int) or count<=0:return False
  cost=(DISH_COST if name=='Bát/đĩa' else STOCK_COST[name])*count
  if self.cash<cost:self.note('Không đủ ngân sách.');return False
  self.cash-=cost;self.record('equipment' if name=='Bát/đĩa' else 'purchases',cost)
  self.queue_goods({name:count},{name:cost});self.note('Đã đặt '+str(count)+' '+name+'. Chờ xe giao hàng.');return True
 def process_deliveries(self):
  changed=False
  for o in self.deliveries:
   if not o['delivered'] and self.now>=datetime.fromisoformat(o['due']):
    self.queue_goods(o['quantities'],{n:q*o.get('unit_prices',{}).get(n,STOCK_COST[n]*.97) for n,q in o['quantities'].items()},'Nhà cung cấp')
    o['delivered']=True;changed=True
  return changed
 def delivery_tick(self,dt):
  if not self.truck and self.shipments:
   self.truck={'age':0.,'orders':self.shipments[:], 'unloaded':False};self.shipments.clear()
  if not self.truck:return
  t=self.truck;t['age']+=dt
  if t['age']>=9 and not t['unloaded']:
   for order in t['orders']:
    for n,q in order['items'].items():
     while q:
      take=1 if n.startswith('@') else q;q-=take
      pos=self.parcel_position()
      if pos is None:
       self.queue_goods({n:take+q},order['costs'],order['label']);break
      i=self.next_parcel;self.next_parcel+=1
      self.parcels.append({'id':i,'name':n,'qty':take,'cost':order['costs'].get(n,0),'x':pos[0],'y':pos[1],'floor':0,'opened':False,'held':False})
   t['unloaded']=True;self.note('Hàng đã ở trước cửa. Đến nhận thùng, mở và cất đồ.')
  if t['age']>=16:self.truck=None
 def unpack(self,parcel,fixture):
  if parcel not in self.parcels:return False
  n=parcel['name']
  if not parcel['opened']:self.note('Mở thùng trước khi cất hàng.');return False
  if n.startswith('@') or storage_for(n)!=fixture.kind:self.note('Hãy cất vào đúng loại tủ.');return False
  if not fixture.opened:self.note('Mở tủ trước khi cất hàng.');return False
  q=parcel['qty']
  if n=='Bát/đĩa':self.clean+=q;self.dishes_owned+=q
  else:self.stock[n]+=q;self.stock_value[n]+=parcel['cost']
  self.parcels.remove(parcel);self.note(f'Đã cất {q} {n}.');return True
 def opening_blocker(self,automatic=False):
  if not self.tables:return 'Cần mua và đặt ít nhất một bộ bàn ghế.'
  for kind in ('ticket','stove','pass','fridge','bowls','sink','spice'):
   if not self.fixture(kind,0):return 'Cần đặt '+FURNITURE[kind][0]+' ở tầng 1.'
  return super().opening_blocker(automatic)
 def ensure_receipt(self,p):
  if p.id not in self.receipts:
   day=self.now.date().isoformat();self.day_orders[day]=self.day_orders.get(day,0)+1
   self.receipts[p.id]={'gid':p.id,'number':self.day_orders[day],'day':day,'location':'customer','table':'Chưa xếp bàn','attached':{},'orders':list(p.orders),'recipes':[list(x) for x in p.recipes],'drinks':list(p.drinks),'size':p.size}
  return self.receipts[p.id]
 def collect(self,gid):
  if not super().collect(gid):return False
  r=self.ensure_receipt(self.group(gid));r['location']='hand' if self.manual_receipt else 'board'
  self.note('Đã nhận phiếu đơn '+str(r['number'])+'. Mang tới bảng đen để dán.');return True
 def seat(self,gid,index):
  if not super().seat(gid,index):return False
  self.ensure_receipt(self.group(gid))['table']=self.table_name(index);return True
 def reserved_action(self,action):
  if action[0] in ('prep','top','serve','discard') and len(action)>1 and (action[1]==self.carried_bowl or action[1] in self.free_bowls):return True
  return super().reserved_action(action)
 def choose_staff_job(self,e,active):
  result=super().choose_staff_job(e,active)
  if not result:
   for b in self.bowls:
    p=self.group(getattr(b,'ticket_gid',None))
    if b.stage=='prep' and b.id!=self.carried_bowl and b.id not in self.free_bowls and p and p.phase=='seated' and len(p.meals)<p.size:
     action=('serve',b.id,p.table,p.id)
     if not self.reserved_action(action):return (action,(*self.table_position(p.table),self.tables[p.table].floor),2)
   return None
  action,target,seconds=result;kind=action[0]
  f=self.fixture('stove' if kind in ('start','lift','discard_pot') else 'pass' if kind in ('prep','top','discard') else 'sink' if kind in ('wash','clean_wait') and (kind=='wash' or action[1]=='wash') else 'ticket' if kind=='collect' else '')
  if f:target=(f.rect.centerx,f.rect.bottom+32,f.floor)
  if kind=='serve':
   b=next((b for b in self.bowls if b.id==action[1]),None)
   tag=getattr(b,'ticket_gid',None)
   if tag:
    p=self.group(tag)
    if p and p.table>=0:action=('serve',b.id,p.table,p.id);target=(*self.table_position(p.table),self.tables[p.table].floor)
  if kind=='sweep':target=(*self.dirt_point(action[1]),action[1]//4)
  target=(*self.safe_point(target[:2],target[2]),target[2])
  return action,target,seconds
 def finish_staff_job(self,e,job):
  super().finish_staff_job(e,job)
  if job['action'][0]=='prep':
   b=next((b for b in self.bowls if b.id==job['action'][1]),None)
   order=next((o for o in self.staff_cooking.values() if o.get('bid')==getattr(b,'id',None)),None)
   if b and order:
    gid=order.get('gid');candidates=[p.id for p in self.parties if p.phase=='seated']
    if 'Hậu đậu' in e['traits'] and candidates and self.rng.random()<.12:gid=self.rng.choice(candidates)
    b.ticket_gid=gid
 def move_prep(self,bid,slot):
  b=next((b for b in self.bowls if b.id==bid),None)
  if b and b.stage=='prep' and b.slot==slot:return True
  return super().move_prep(bid,slot)
 def dirt_point(self,spot):
  from model import DIRT_POS
  return self.dirt_locations.get(spot,DIRT_POS[spot%len(DIRT_POS)])
 def mark_dirty(self,floor=0,reason='Vết bẩn',preferred=0):
  before=set(self.dirt);result=super().mark_dirty(floor,reason,preferred)
  for spot in set(self.dirt)-before:
   p=self.dirt_point(spot)
   if not self.walkable(p,floor):
    candidates=[(x,y) for x in range(60,1540,40) for y in range(320,900,40) if self.walkable((x,y),floor)]
    if candidates:self.dirt_locations[spot]=min(candidates,key=lambda q:math.dist(p,q))
  return result
 def close_shop(self,automatic=False):
  if self.carried_dirty:self.note('Còn bát bẩn đang cầm, hãy mang về bồn.');return False
  return super().close_shop(automatic)
 def update(self,dt):
  self.delivery_tick(dt)
  super().update(dt)
  for p in self.parties:
   if p.paid and not p.refunded:self.ensure_receipt(p)
  for fid,job in self.rice_jobs.items():
   if job['left']>0:job['left']=max(0,job['left']-dt)
