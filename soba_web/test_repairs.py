"""Real pointer regressions at phone, tablet and desktop viewport sizes."""
import os,sys
from pathlib import Path
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root/'game'))
import pygame as pg
from v2app import V2App
from v2world import Fixture

def tap(a,action):
 a.draw();r=next(r for r,act in a.buttons if act==action)
 point=(r.centerx*a.scale+a.offset[0],r.centery*a.scale+a.offset[1])
 for kind in (pg.MOUSEBUTTONDOWN,pg.MOUSEBUTTONUP):a.event(pg.event.Event(kind,pos=point,button=1))
for size in ((1600,1000),(1280,720),(844,390),(768,1024)):
 a=V2App(headless=True,persistent=False);a.modal=None
 a.event(pg.event.Event(pg.VIDEORESIZE,w=size[0],h=size[1]));assert a.display.get_size()==size
 tap(a,('phone',))
 for key in ('market','furniture','staff','shifts','menu','supplier','finance','history','settings'):
  tap(a,('app',key));assert a.modal=='phone_app' and a.active_app==key
  tap(a,('phone',));assert a.modal=='phone'
 tap(a,('app','staff'));tap(a,('staff_tab','hire'));tap(a,('post_recruitment',))
 assert a.world.candidates
 candidate=a.world.applicants()[0]
 tap(a,('hire_review',candidate['id']));assert a.modal=='hire_contract'
 tap(a,('dismiss',));assert a.modal=='phone_app' and a.active_app=='staff'
 tap(a,('phone',));tap(a,('app','menu'));tap(a,('field','name'))
 a.name_value='';a.event(pg.event.Event(pg.TEXTINPUT,text='Mì soba đặc biệt dành cho cả gia đình'))
 assert len(a.name_value)>24
 tap(a,('name_done',));assert a.menu_name=='Mì soba đặc biệt dành cho cả gia đình' and a.modal=='phone_app'
 tap(a,('dismiss',));assert a.modal is None
 a.placing={'kind':'sink'};a.place_point=(900,400);a.draw()
 a.event(pg.event.Event(pg.MOUSEMOTION,pos=(750*a.scale+a.offset[0],890*a.scale+a.offset[1])))
 assert a.place_point==(900,400),'Moving to confirm must not shift the furniture'
 a.action(('cancel_place',));a.owner.update(300,420);a.camera_origin=a.camera_goal()
 a.camera_keys.add(pg.K_d);a.step(.1);assert a.owner_moving and a.owner_stride>0
 a.camera_keys.clear();a.step(.1);assert not a.owner_moving
 for kind in ('stove','pass','fridge','round2'):
  f=Fixture(1,kind,900,400)
  assert f.visual_rect.bottom==f.rect.bottom and f.visual_rect.w<=f.rect.w
 pg.quit()
print('PASS: nine phone apps at four viewport sizes, recruitment/back, full menu names, stable placement, distance-based animation, aspect-preserving furniture')
