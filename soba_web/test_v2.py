"""End-to-end physical economy and service, plus real touch/UI input."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'game'))
import pygame as pg
from v2app import V2App
from v2world import FURNITURE,storage_for
from model import COOK_SECONDS

a=V2App(headless=True,persistent=False);w=a.world;a.modal=None
assert not w.tables and not w.fixtures and not w.open and w.cash==10000000
layout={'square4':(420,460),'ticket':(420,300),'board':(660,300),'clock':(1250,300),'calendar':(1400,300),
 'stove':(1100,400),'pass':(1100,700),'fridge':(840,340),'spice':(840,500),'bowls':(800,640),'sink':(800,770),'drinks':(600,370),'rice':(1420,600)}
for kind in layout:assert w.buy_fixture(kind)
assert not w.fixtures and not w.parcels
w.delivery_tick(8);assert not w.parcels
w.delivery_tick(2);assert len(w.parcels)==len(layout)
for kind,(x,y) in layout.items():
 parcel=next(p for p in w.parcels if p['name']=='@'+kind)
 a.action(('take_parcel',parcel['id']));a.action(('open_parcel',));a.place_point=(x,y)
 a.action(('place_confirm',))
 if FURNITURE[kind][3]:
  assert a.modal=='name';a.name_value='Sakura';a.action(('name_done',))
 assert w.fixture(kind),('could not place',kind,w.logs[-1])
assert w.table_name(0)=='Sakura' and not a.hand
assert w.place('round1',425,460,name='Overlap') is None
assert w.place('round1',70,650,name='Sakura') is None
# Stock is paid immediately but cannot be used before delivery, opening and storage.
before=w.cash
for n in ('Bát/đĩa','Mì tươi','Nước dùng','Hành'):assert w.restock(n,10)
assert w.cash<before and w.stock['Mì tươi']==0 and w.clean==0
w.delivery_tick(20);w.delivery_tick(10)
for p in w.parcels[:]:
 a.action(('take_parcel',p['id']));f=w.fixture(storage_for(p['name']))
 assert not w.unpack(p,f)
 a.action(('open_parcel',));a.action(('open_store',f.id));assert not a.hand
assert w.clean==10 and w.stock['Mì tươi']==10
assert w.open_shop(),w.logs[-1]
assert not w.restock('Mì tươi',1)
p=w.add_party(1);p.orders=['Kake soba'];p.recipes=[['Nước dùng','Hành']];p.prices=[65000];p.drinks=[''];p.drinks_served=[False]
a.owner.update(p.x,p.y+60);a.interact(('guest',p.id));assert len(a.options)==3
a.action(('answer',p.id,'accept'));p.phase='ticket';p.paid=65000
w.ensure_receipt(p);a.action(('take_ticket',p.id));assert a.hand['kind']=='ticket'
a.action(('escort',p.id));table=w.table_fixture(0);a.owner.update(table.x-65,table.y+70);a.interact(('fixture',table.id));assert p.table==0 and w.receipts[p.id]['table']=='Sakura'
board=w.fixture('board');a.owner.update(board.x+20,board.y+80);a.interact(('fixture',board.id));a.action(('pin_ticket',));assert w.receipts[p.id]['location']=='board'
# Carry noodle -> pot -> bowl -> pass -> each ingredient -> ticket -> correct table.
a.action(('take_ingredient','Mì tươi'));assert w.stock['Mì tươi']==9
a.apply_ingredient('pot',0);assert w.stock['Mì tươi']==9 and not a.hand
w.pots[0]=COOK_SECONDS;a.action(('lift',0));bid=a.hand['id'];f=w.fixture('pass');a.owner.update(f.x-50,f.y+40);a.interact(('fixture',f.id));assert not a.hand
for n in ('Nước dùng','Hành'):
 a.action(('take_ingredient',n));a.apply_ingredient('bowl',bid);assert not a.hand
b=next(b for b in w.bowls if b.id==bid);a.action(('get_ticket',p.id));a.owner.update(*a.bowl_pos(b));a.interact(('bowl',bid));assert b.ticket_gid==p.id and not a.hand
a.action(('take_bowl',bid));a.serve_hand(0,p.id);assert p.meals and not a.hand
# Dirty dishes are carried physically and require held washing, never automatic storage wash.
p.phase='leaving';t=w.tables[0];t.dirty=1;t.needs_wipe=True
a.action(('take_dirty',0));assert a.hand['kind']=='dirty' and not w.sink
sink=w.fixture('sink');a.owner.update(sink.x-40,sink.y+35);a.interact(('fixture',sink.id));assert w.sink==1 and not w.washing and not a.hand
assert a.clean_target(('fixture',sink.id))==('wash',None)
# All phone apps draw, while neither physical clock nor shift viewer is exposed there.
for key in ('market','furniture','staff','shifts','menu','supplier','finance','history','settings'):
 a.action(('app',key));a.draw();assert not any(act==('staff_tab','clock') or act==('shifts_view',) for _,act in a.buttons)
a.modal=None;a.owner.update(1000,620);a.camera_origin=a.camera_goal();a.draw();pg.image.save(a.display,str(root/'v2-furnished-preview.png'))
a.action(('phone',));a.draw();pg.image.save(a.display,str(root/'v2-phone-preview.png'))
# A real finger tap on the phone icon does not become a movement gesture.
a.modal=None;a.draw();dw,dh=a.display.get_size();pos=(1500*a.scale+a.offset[0],150*a.scale+a.offset[1])
for typ in (pg.FINGERDOWN,pg.FINGERUP):a.event(pg.event.Event(typ,finger_id=1,x=pos[0]/dw,y=pos[1]/dh))
assert a.modal=='phone'
print('PASS: empty start, paid delivery, named nonoverlapping placement, physical stock, guest reception, receipt-table link, board, cooking/carry/tag/serve, dirty dishes, phone apps, native finger input')
# Archived receipts retain bought dishes after the guests leave.
a.modal=None
q=w.add_party(1);w.ensure_receipt(q)
before=w.day_orders[w.now.date().isoformat()]
assert w.ensure_receipt(q)['number']==before
w.parties.remove(p);a.action(('receipt',p.id));a.draw()
# Physical clock/calendar are read-only views.
for mode in ('physical_clock','physical_calendar'):
 a.modal=mode;a.target=('fixture',w.fixture('clock' if mode=='physical_clock' else 'calendar').id);a.draw()
 assert not any(act[0] in ('hire','shift_create','request_leave') for _,act in a.buttons)
a.modal=None;w.open=False
assert not w.buy_fixture('ticket')
# The phone does not pause deliveries.
a.action(('phone',));w.truck=None;w.shipments=[];w.queue_goods({'Mì tươi':2},{'Mì tươi':64000})
a.step(10);assert any(z['name']=='Mì tươi' for z in w.parcels)
print('PASS: receipt archival, read-only objects, duplicate equipment rejection, phone does not pause deliveries')
