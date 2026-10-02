"""Web kitchen: clear work aisles, six burners, a clean pass and separate washing."""
import math
import pygame as pg

RAW=pg.Rect(810,300,170,88)
SINK=pg.Rect(810,738,180,90)
TRASH=pg.Rect(822,855,155,53)
RACK=pg.Rect(810,617,170,76)
POT_POS=[(1120+col*155,352+row*112) for row in range(2) for col in range(3)]
BOWL_POS=[(1120+col*155,787+row*83) for row in range(2) for col in range(3)]
TOPPINGS=['Nước dùng','Hành','Tôm','Bò','Trứng','Măng','Kaeshi','Vị cay','Bột ớt','Nori']
TOPPING_RECTS={name:pg.Rect(1080+(i%5)*94,567+(i//5)*49,87,44) for i,name in enumerate(TOPPINGS)}
DRINK_RECTS={name:pg.Rect(818,425+i*51,154,44) for i,name in enumerate(['Coca-Cola','Trà xanh','Bò húc'])}
COUNTERS=[RAW,SINK,TRASH,RACK,pg.Rect(1060,294,490,224),pg.Rect(802,411,186,168),pg.Rect(1065,550,480,122),pg.Rect(1060,749,495,166)]

class KitchenMixin:
    def counter(self,rect,color='#d7ded7'):
        r=pg.Rect(rect)
        self.box(r.move(4,6),'#68796f',9)
        self.box(r,color,8,border='#9aa89b')
        pg.draw.line(self.canvas,'#eef0e3',(r.left+9,r.top+5),(r.right-9,r.top+5),3)

    def render_kitchen(self):
        from model import COOK_SECONDS,LIFT_WINDOW
        from app import TOPPING_COLOR
        w=self.world
        # Quiet floor colors, dedicated work surfaces and an open north/south aisle.
        self.box((780,275,783,647),'#b7c4b5',4)
        for x in range(782,1560,48):pg.draw.line(self.canvas,'#a7b7a6',(x,278),(x,918))
        for y in range(280,922,48):pg.draw.line(self.canvas,'#a7b7a6',(784,y),(1560,y))
        self.box((994,297,56,607),'#c9d2c0',8)
        self.text('BẾP · LỐI ĐI GIỮA CÁC QUẦY',(1165,258),17,'#fff2d2',True,True)
        # Raw ingredient and drinks are beside the kitchen entry.
        self.counter(RAW,'#eadabb')
        self.text('01 / MÌ TƯƠI',(RAW.centerx,RAW.y+17),15,'#5b4b32',True,True)
        if w.stock['Mì tươi']>0:
            self.box((825,331,59,40),'#f6ebcd',5)
            for i in range(9):pg.draw.line(self.canvas,'#c4a36b',(831+i*5,336),(834+i*5,365),2)
            self.text(str(w.stock['Mì tươi'])+' phần',(930,347),15,'#5b4b32',True,True)
            self.text('Kéo vào nồi',(930,369),12,'#6b6b54',center=True)
        else:self.text('Khay đang trống',(RAW.centerx,350),15,'#797965',center=True)
        self.counter((802,411,186,168),'#66827a')
        self.text('ĐỒ UỐNG',(895,401),15,'#334d44',True,True)
        for name,r in DRINK_RECTS.items():
            if w.stock[name]<=0:continue
            self.box(r,'#e6e9d8',5)
            pg.draw.rect(self.canvas,TOPPING_COLOR[name],(r.x+9,r.y+8,18,27),border_radius=4)
            pg.draw.line(self.canvas,'#ebeddf',(r.x+11,r.y+8),(r.x+25,r.y+8),3)
            self.text(name,(r.x+35,r.y+7),13,'#314c43',True)
            self.text(str(w.stock[name])+' chai/lon',(r.x+35,r.y+25),11,'#617268')
        # Six clearly separated pots, with a continuous lower approach aisle.
        self.counter((1060,294,490,224),'#879a90')
        self.text('02 / BẾP LUỘC · 6 NỒI',(1305,283),15,'#40594a',True,True)
        for i,(x,y) in enumerate(POT_POS):
            state=w.pot_state(i)
            self.box((x-51,y-40,102,86),'#5e756b',7)
            pg.draw.circle(self.canvas,'#31473e',(x,y-4),35)
            pg.draw.circle(self.canvas,'#d5dfd7',(x,y-7),29)
            pg.draw.circle(self.canvas,'#7eaaa9' if state=='empty' else '#c5cda5',(x,y-7),23)
            for dx in (-40,31):self.box((x+dx,y-10,10,8),'#263e35',2)
            if state!='empty':
                for j in range(5):pg.draw.arc(self.canvas,'#f4df9c',(x-18+j*3,y-24+j*3,23,15),.3,5.3,2)
                for j in range(3):
                    sy=y-30-((self.animation*18+j*12)%23)
                    pg.draw.circle(self.canvas,'#eff2e5',(x-11+j*11,int(sy)),3)
            if state=='empty':label=f'{i+1} · Trống';col='#e7ead8'
            elif state=='cooking':
                left=max(0,math.ceil(COOK_SECONDS-w.pots[i]));label=f'{i+1} · {left//60}:{left%60:02}';col='#fff0c1'
            elif state=='ready':
                label=f'VỚT! {max(0,math.ceil(COOK_SECONDS+LIFT_WINDOW-w.pots[i]))}s';col='#b6f0ad'
                pg.draw.circle(self.canvas,'#98cf8a',(x,y-7),35,3)
            else:label='NHÃO';col='#ffc0a6'
            self.text(label,(x,y+31),15,col,True,True)
            b=next((b for b in w.bowls if b.stage=='lifted' and b.slot==i),None)
            if b and self.drag!=('bowl',b.id):
                self.box((x-48,y-37,96,81),'#d5c39c',6)
                self.bowl((x,y-8),mushy=b.mushy,size=27)
                self.text('Đưa ra quầy',(x,y+29),12,'#4b5e46',True,True)
        # Toppings directly above the finishing pass; no invisible stocked items.
        self.counter((1065,550,480,122),'#ccbb96')
        self.text('03 / TOPPING',(1305,540),15,'#40594a',True,True)
        for name,r in TOPPING_RECTS.items():
            if w.stock[name]<=0:continue
            self.box(r,'#f0e8cc',5,border='#998f6c')
            self.box((r.x+5,r.y+6,19,29),TOPPING_COLOR[name],4)
            short='Dùng' if name=='Nước dùng' else name
            self.text(short,(r.x+28,r.y+7),11,'#354b3b',True)
            self.text(str(w.stock[name]),(r.x+28,r.y+26),12,'#71735c')
        # Clean bowl rack is physically separate from the dirty return sink.
        self.counter(RACK,'#e6dac0')
        self.text('BÁT SẠCH',(RACK.centerx,RACK.y+15),15,'#51654d',True,True)
        for i in range(min(w.clean,4)):
            x=832+i*38
            pg.draw.ellipse(self.canvas,'#8c927d',(x-16,653,32,21))
            pg.draw.ellipse(self.canvas,'#faf7e8',(x-16,647,32,19))
            pg.draw.ellipse(self.canvas,'#c9d4c9',(x-11,650,22,11),2)
        self.text(str(w.clean),(RACK.right-18,RACK.bottom-10),14,'#52624b',True,True)
        self.counter(SINK,'#9daea5')
        self.text('RỬA / BÁT BẨN',(SINK.centerx,SINK.y-13),14,'#365346',True,True)
        self.box((820,748,97,57),'#455f58',8,border='#d5dfd8')
        for i in range(min(w.sink,3)):self.bowl((840+i*21,777),dirty=True,size=15)
        pg.draw.arc(self.canvas,'#e1e8e2',(866,738,29,34),0,math.pi,5)
        self.text(f'{w.sink} bát',(950,758),14,'#2b4b3e',True,True)
        self.text(str(max(0,math.ceil(w.wash_left)))+'s' if w.washing else 'GIỮ RỬA',(950,788),12,'#2b4b3e',True,True)
        self.counter(TRASH,'#67766a')
        self.text('RÁC / ĐỔ BỎ',TRASH.center,14,'#edf0dc',True,True)
        self.counter((1060,749,495,166),'#c8ae80')
        self.text('04 / HOÀN THIỆN & RA MÓN',(1305,730),15,'#40594a',True,True)
        for i,(x,y) in enumerate(BOWL_POS):
            self.box((x-49,y-30,98,76),'#e8d4a7',6,border='#b89b68')
            pg.draw.ellipse(self.canvas,'#c0aa7a',(x-27,y-18,54,34),2)
            self.text(str(i+1),(x-38,y+30),12,'#90794e',True)
            b=next((b for b in w.bowls if b.stage=='prep' and b.slot==i),None)
            if b and self.drag!=('bowl',b.id):
                self.bowl((x,y),b.toppings,b.mushy,size=28)
                self.text(f'Bát {b.id} · {len(b.toppings)} vị',(x,y+31),12,'#43573e',True,True)
