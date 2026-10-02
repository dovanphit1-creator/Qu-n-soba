"""Real input regression: reskinned phone still invokes the original game actions."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'game'))
import pygame as pg
from v2app import V2App
app=V2App(headless=True,persistent=False);app.modal=None

def tap(action):
 app.draw();rect=next(r for r,a in app.buttons if a==action)
 dw,dh=app.display.get_size();x=(rect.centerx*app.scale+app.offset[0])/dw;y=(rect.centery*app.scale+app.offset[1])/dh
 for typ in (pg.FINGERDOWN,pg.FINGERUP):app.event(pg.event.Event(typ,finger_id=11,x=x,y=y))

tap(('phone',));assert app.modal=='phone'
tap(('app','market'));assert app.active_app=='market'
stock=app.world.stock['Mì tươi'];cash=app.world.cash
tap(('buy','Mì tươi',1));assert app.world.cash<cash and app.world.stock['Mì tươi']==stock and app.world.shipments
# Receipt skin retains its real archived order and table, with its pickup button.
p=app.world.add_party(1);r=app.world.ensure_receipt(p);r['location']='board';r['table']='Sakura'
app.action(('receipt',p.id));app.draw();tap(('get_ticket',p.id));assert app.hand['kind']=='ticket'
app.action(('put_down',));app.draw()
# Every held ingredient is rendered without touching stock or its cost.
for name in app.world.stock:
 app.hand={'kind':'ingredient','name':name,'cost':100};app.modal=None;app.draw()
assert app.world.stock['Mì tươi']==stock
print('PASS: finger input on reskinned phone, paid delivery purchase, receipt pickup/drop, all held ingredients')
