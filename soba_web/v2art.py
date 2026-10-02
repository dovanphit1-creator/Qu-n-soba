"""Raster sprite renderer: one logical art pixel = two world pixels.
Atlases are generated artwork, cropped per cell and cached with nearest sampling.
Collision footprints remain independent of decorative sprite overhangs.
"""
import math
from pathlib import Path
import pygame as pg
from v2world import FURNITURE
CREAM='#fff0ce';INK='#243f39';WOOD='#956743';MINT='#82aa90'
class PixelArt:
 def px(self,r,c):pg.draw.rect(self.canvas,c,pg.Rect(*(int(v//2*2) for v in r)))
 def disk(self,p,r,c):
  x,y=p
  for dy in range(-r,r+1,2):
   dx=int(math.sqrt(max(0,r*r-dy*dy)))//2*2
   if dx:self.px((x-dx,y+dy,dx*2,2),c)
 def art(self,sheet,index,size):
  if not hasattr(self,'_art_cache'):self._art_cache={};self._atlases={}
  size=tuple(max(2,int(v)//2*2) for v in size);key=(sheet,index,size)
  if key not in self._art_cache:
   if sheet not in self._atlases:self._atlases[sheet]=pg.image.load(str(Path(__file__).parent/'assets'/'pixel'/f'{sheet}.png')).convert_alpha()
   atlas=self._atlases[sheet];cw,ch=atlas.get_width()//4,atlas.get_height()//4
   region=pg.Rect(index%4*cw,index//4*ch,cw,ch)
   if sheet=='skins' and index==8:region=pg.Rect(0,int(atlas.get_height()*.474),cw,int(atlas.get_height()*.27))
   cell=atlas.subsurface(region).copy()
   parts=pg.mask.from_surface(cell,128).get_bounding_rects()
   bounds=max(parts,key=lambda r:r.w*r.h) if parts else cell.get_rect()
   if sheet=='icons' and index==2 and parts:bounds=bounds.unionall([p for p in parts if p.w*p.h>=bounds.w*bounds.h*.25])
   if bounds.w and bounds.h:cell=cell.subsurface(bounds).copy()
   if sheet=='environment' and index<4:
    inset=max(3,cell.get_width()//24);cell=cell.subsurface(cell.get_rect().inflate(-inset*2,-inset*2)).copy()
   # Downsample once to the shared logical pixel grid; never smoothscale.
   cell=pg.transform.scale(cell,(size[0]//2,size[1]//2))
   self._art_cache[key]=pg.transform.scale(cell,size)
  return self._art_cache[key]
 def sprite(self,sheet,index,rect):
  r=pg.Rect(rect);self.canvas.blit(self.art(sheet,index,r.size),r)
 def skin(self,index,rect):
  r=pg.Rect(rect)
  if r.w<=0 or r.h<=0:return
  if not hasattr(self,'_skin_cache'):self._skin_cache={}
  key=(index,r.size)
  if key not in self._skin_cache:
   src=self.art('skins',index,(128,128));dst=pg.Surface(r.size,pg.SRCALPHA)
   edge=min(18,r.w//3,r.h//3);cuts=(0,24,104,128)
   xs=(0,edge,r.w-edge,r.w);ys=(0,edge,r.h-edge,r.h)
   for y in range(3):
    for x in range(3):
     piece=src.subsurface((cuts[x],cuts[y],cuts[x+1]-cuts[x],cuts[y+1]-cuts[y]))
     dst.blit(pg.transform.scale(piece,(xs[x+1]-xs[x],ys[y+1]-ys[y])),(xs[x],ys[y]))
   self._skin_cache[key]=dst
  self.canvas.blit(self._skin_cache[key],r)
 def box(self,rect,color,radius=10,border=None,width=2):
  c=pg.Color(color);index=0 if (c.r+c.g+c.b)>480 else 1
  if max(pg.Rect(rect).size)<32:pg.draw.rect(self.canvas,c,rect);return
  self.skin(index,rect)
 def ingredient_sprite(self,name,x,y,size=32):
  names=['Mì tươi','Nước dùng','Hành','Tôm','Bò','Trứng','Măng','Kaeshi','Vị cay','Bột ớt','Nori','Coca-Cola','Trà xanh','Bò húc','Gạo']
  if name in names:self.sprite('ingredients',names.index(name),(x-size/2,y-size/2,size,size))
 def ticket_sprite(self,x,y,size=24):self.sprite('icons',10,(x-size*.35,y-size*.5,size*.7,size))
 def dirt_sprite(self,x,y):
  surf=pg.Surface((44,30),pg.SRCALPHA)
  pg.draw.polygon(surf,(116,71,38,165),[(2,16),(8,10),(14,12),(20,4),(28,8),(30,16),(40,16),(42,24),(30,28),(22,24),(14,28),(6,22)])
  pg.draw.lines(surf,(216,181,115,205),False,[(10,18),(16,14),(20,20),(28,16)],2)
  for dx,dy in ((4,4),(34,6),(38,26)):pg.draw.rect(surf,(91,64,38,135),(dx,dy,2,2))
  self.canvas.blit(surf,(int(x)-22,int(y)-15))
 def shadow(self,x,y,w,h):
  surf=pg.Surface((max(2,w//2),max(2,h//2)),pg.SRCALPHA)
  pg.draw.ellipse(surf,(54,43,32,38),surf.get_rect())
  pg.draw.ellipse(surf,(54,43,32,35),surf.get_rect().inflate(-4,-2))
  self.canvas.blit(pg.transform.scale(surf,(w,h)),(x-w//2,y-h//2))
 def person(self,x,y,color,step=0,scale=1,action=None,variant=None):
  owner=color=='#3f8e79';row=0;sheet='owner'
  if owner:
   d=self.move_direction
   if d.length_squared():self._facing=3 if abs(d.y)>abs(d.x) and d.y<0 else 0 if abs(d.y)>abs(d.x) else 1 if d.x<0 else 2
   row=getattr(self,'_facing',0)
  elif color in ('#7e94af','#b48672','#9e85a0','#cfaa64'):
   sheet='guests';row={'#7e94af':1,'#b48672':0,'#9e85a0':2,'#cfaa64':3}[color]
  if sheet=='guests' and row!=3 and variant is not None:row=variant%3
  if owner and self.clean_hold:sheet='actions';row=3;step=self.animation*5
  elif owner and self.hand:sheet='actions';row=1
  elif owner and not step:sheet='actions';row=0;step=self.animation*2
  elif action in ('prep','top','start','lift'):sheet='actions';row=2;step=self.animation*5
  elif action in ('wash','clean_wait','wipe','sweep'):sheet='actions';row=3;step=self.animation*5
  elif action in ('serve','clear'):sheet='actions';row=1
  frame=int(step)%4 if step else 1
  self.shadow(x+3,y+10,36,14)
  bob=2 if not step and int(self.animation*1.5)%3==1 else 0
  self.sprite(sheet,row*4+frame,(round(x/2)*2-22,round(y/2)*2-62+bob,44,76))
 def pixel_bowl(self,x,y,toppings=(),dirty=False):
  self.sprite('environment' if dirty or toppings else 'icons',11 if dirty else 10 if toppings else 15,(x-22,y-20,44,40))
 def fixture_sprite(self,f):
  r=f.rect;kind=f.kind;idx=list(FURNITURE).index(kind)
  self.shadow(r.centerx+4,r.bottom-4,r.w,22)
  rise=24 if kind not in ('clock','calendar','board') else 8
  self.sprite('furniture',idx,(r.x,r.y-rise,r.w,r.h+rise))
  if kind in ('bowls','drinks','spice','fridge'):
   self.text('MỞ' if f.opened else 'ĐÓNG',(r.centerx,r.bottom-10),10,'#fff1cf',True,True)
  if kind=='board':
   for i,receipt in enumerate([r for r in self.world.receipts.values() if r['location']=='board'][-6:]):
    x=r.x+12+i*22;self.ticket_sprite(x+8,r.y+14)
  if kind=='stove':
   for i,age in enumerate(self.world.pots):
    if age is not None:
     x,y=f.slot_point(i)
     for j in range(3):
      t=(self.animation*15+j*11)%34;self.px((x-8+j*8+int(math.sin(t/8)*2)*2,y-16-t,4,8),'#ece5cf')
  if kind=='rice' and self.world.rice_jobs.get(f.id,{}).get('left',0)>0:
   t=self.animation*12%24;self.px((r.centerx,r.y-t,4,10),'#eee9d8')
 def truck_sprite(self,x,y):self.sprite('environment',14,(x,y-24,196,100))
 def parcel_sprite(self,p):self.sprite('environment',13 if p.get('opened') else 12,(p['x']-24,p['y']-32,48,48))
 def room_art(self):
  if not hasattr(self,'_room_art'):
   dest=self.canvas;self.canvas=pg.Surface((1600,1000));self.canvas.fill('#677367')
   for area,index,tile in [(pg.Rect(0,98,1600,58),3,96),(pg.Rect(0,156,1600,90),2,80),(pg.Rect(40,282,1520,638),0,128),(pg.Rect(780,282,780,638),1,128)]:
    self.canvas.set_clip(area)
    for y in range(area.y,area.bottom,tile):
     for x in range(area.x,area.right,tile):self.sprite('environment',index,(x,y,tile,tile))
   self.canvas.set_clip(None)
   self.px((24,282,16,654),'#694d36');self.px((1560,282,16,654),'#694d36');self.px((24,920,1552,16),'#694d36')
   for x in range(360,1560,150):self.sprite('environment',4,(x,222,150,64))
   self.sprite('environment',4,(24,222,196,64))
   for x in (510,960,1410):self.sprite('environment',5,(x,221,78,64))
   for x in (110,740,1250):self.sprite('environment',9,(x,218,32,64))
   for x in (55,1470):self.sprite('environment',8,(x,184,40,58))
   self._room_art=self.canvas;self.canvas=dest
  self.canvas.blit(self._room_art,(0,0))
  self.sprite('environment',7 if self.world.open else 6,(220,224,140,62))
