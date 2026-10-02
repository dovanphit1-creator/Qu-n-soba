"""Code-native pixel sprites. No external art or font downloads at runtime."""
import math
import pygame as pg
from v2world import FURNITURE,storage_for
CREAM='#fff0ce';INK='#243f39';WOOD='#956743';MINT='#82aa90'
class PixelArt:
 def px(self,r,c):pg.draw.rect(self.canvas,c,pg.Rect(*(int(v//4*4) for v in r)))
 def disk(self,p,r,c):
  x,y=p
  for dy in range(-r,r+1,4):
   dx=int(math.sqrt(max(0,r*r-dy*dy)))//4*4
   if dx:self.px((x-dx,y+dy,dx*2,4),c)
 def person(self,x,y,color,step=0,scale=1):
  # Four walking poses, a separate moving shadow and a distinct apron.
  x=int(x//4*4);y=int(y//4*4);stride=[0,4,0,-4][int(step)%4]
  self.px((x-12,y+12,28,8),'#82785e')
  self.px((x-8,y+2,8,16+stride),'#334c50');self.px((x+4,y+2,8,16-stride),'#334c50')
  self.px((x-12,y-20,28,28),color);self.px((x-16,y-12+stride,4,20),'#e7b58b');self.px((x+16,y-12-stride,4,20),'#e7b58b')
  self.px((x-8,y-16,20,24),'#e8d9b2');self.px((x-4,y-12,12,4),color)
  self.px((x-8,y-40,20,24),'#e7b58b');self.px((x-12,y-40,24,8),'#463e38');self.px((x-12,y-36,4,12),'#463e38')
  self.px((x+4,y-28,4,4),'#343c36')
 def pixel_bowl(self,x,y,toppings=(),dirty=False):
  self.px((x-20,y-4,40,12),'#c0a783' if dirty else '#f9eac7');self.px((x-16,y+8,32,8),'#a9997c');self.px((x-8,y+16,16,4),'#574f42')
  self.px((x-16,y-8,32,8),'#897653' if dirty else '#c29752')
  if not dirty:
   for i in range(4):self.px((x-12+i*8,y-8+(i%2)*4,4,8),'#eed285')
   for i,n in enumerate(toppings[:4]):self.px((x-12+i*8,y-12,8,8),['#658658','#c88663','#edd89b','#456557'][i%4])
 def fixture_sprite(self,f):
  r=f.rect;x,y,w,h=r;kind=f.kind
  self.px((x+4,y+h-4,w,12),'#7f7054')
  if f.table>=0:
   count=FURNITURE[kind][3];cx,cy=r.center
   for i in range(count):
    ang=-math.pi/2+i*2*math.pi/count;xx=cx+math.cos(ang)*(w/2-14);yy=cy+math.sin(ang)*(h/2-14)
    self.px((xx-14,yy-14,28,28),'#684e3a');self.px((xx-10,yy-14,20,20),'#709479')
   if kind=='square4':self.px((x+24,y+24,w-48,h-48),'#ad7950');self.px((x+28,y+24,w-56,h-56),'#dfbe7d')
   else:self.disk((cx,cy),int(w/2-24),'#ad7950');self.disk((cx,cy-4),int(w/2-28),'#dfbe7d')
   return
  if kind in ('board','calendar','clock'):
   self.px(r,'#80583c');self.px(r.inflate(-8,-8),'#304e44' if kind=='board' else '#eee3c5')
   if kind=='board':
    for i in range(6):self.px((x+12+i*22,y+8,16,24),'#dbc892' if i%2 else '#ece0b6')
   elif kind=='clock':self.px((x+12,y+8,40,20),'#547f6c');self.px((x+16,y+12,24,4),'#cbe3b7')
   else:
    self.px((x+4,y+4,w-8,8),'#c37055')
    for dx in range(12,w-8,12):self.px((x+dx,y+20,4,8),'#738671')
   return
  colors={'fridge':'#a4b8ac','spice':'#9e7b52','bowls':'#c4b690','drinks':'#587c74','sink':'#8da7a0','pass':'#c19b62','stove':'#6b8278','rice':'#b9b6a0','ticket':'#41685c'}
  self.px(r,colors[kind]);self.px((x+4,y+4,w-8,8),'#d9d8b8');self.px((x+4,y+h-16,w-8,12),'#53665c')
  if kind=='ticket':
   self.px((x+12,y+20,w-24,28),'#bfce93')
   for dx in range(12,w-8,20):self.px((x+dx,y+56,12,12),'#e8bb77')
   self.px((x+24,y+h-24,w-48,8),'#203f36')
  elif kind=='sink':
   self.px((x+16,y+20,w-48,h-44),'#365950');self.px((x+28,y+24,w-72,h-56),'#628e8b');self.px((x+w-28,y+12,8,32),'#e2e7d0');self.px((x+w-48,y+12,24,8),'#e2e7d0')
  elif kind in ('fridge','spice','bowls','drinks'):
   self.px((x+12,y+20,w-24,h-40),'#334f43' if f.opened else '#bec6a9')
   if f.opened:
    names=[n for n,q in self.world.stock.items() if q>0 and storage_for(n)==kind]
    count=min(4,self.world.clean) if kind=='bowls' else min(4,len(names))
    for dx in [x+20+i*24 for i in range(count)]:
     self.px((dx,y+32,16,20),'#dbbc7f');self.px((dx,y+h-32,16,8),'#dbdbc2')
   else:self.px((x+w-24,y+32,4,20),'#4b6254')
  elif kind=='stove':
   for i in range(6):
    px,py=f.point(.17+(i%3)*.33,.28+(i//3)*.43)
    self.disk((px,py),23,'#304a42');self.disk((px,py-4),19,'#d2ddc8');self.disk((px,py-4),14,'#6c9997')
    age=self.world.pots[i]
    if age is not None:
     self.px((px-12,py-8,24,8),'#e0c88b')
     for j in range(3):
      sy=py-22-int((self.animation*14+j*11)%32)//4*4
      self.px((px-8+j*8,sy,8,8),'#e0e9d3')
  elif kind=='pass':
   for i in range(6):
    px,py=f.point(.17+(i%3)*.33,.28+(i//3)*.43);self.px((px-24,py-16,48,36),'#dfc58e')
  elif kind=='rice':
   self.disk(r.center,26,'#e4ded0');self.px((r.centerx-24,r.centery-8,48,8),'#85928b');self.px((r.centerx-8,r.centery+12,16,8),'#c17a54')
   job=self.world.rice_jobs.get(f.id)
   if job and job['left']>0:
    for j in range(3):self.px((r.centerx+j*8-8,r.y-8-int((self.animation*12+j*8)%24),4,8),'#ebecdb')
 def truck_sprite(self,x,y):
  self.px((x,y,196,60),'#d5bf87');self.px((x+4,y+4,120,44),'#ede1b5');self.px((x+128,y+4,64,52),'#59836f');self.px((x+144,y+8,40,24),'#a1c2b8')
  for dx in (28,148):self.px((x+dx,y+48,28,20),'#35453e');self.px((x+dx+8,y+52,12,12),'#95a79b')
 def parcel_sprite(self,p):
  x,y=p['x'],p['y'];self.px((x-20,y-20,40,36),'#a27244');self.px((x-20,y-20,40,12),'#d7ac67');self.px((x-4,y-20,8,36),'#e6c994');self.px((x+5,y-2,12,8),'#efe3c4')
  if p.get('opened'):self.px((x-28,y-24,24,8),'#ddbd88');self.px((x+8,y-24,24,8),'#ddbd88')
