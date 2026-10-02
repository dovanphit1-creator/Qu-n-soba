"""Web-only close restaurant view; simulation coordinates remain unchanged."""
import math
import pygame as pg

WORLD = pg.Rect(0, 97, 1177, 850)
VIEW = pg.Rect(0, 97, 1600, 850)
MINI = pg.Rect(1413,112,171,124)
DOOR = pg.Rect(222,245,131,42)
DESK = pg.Rect(392,244,185,40)
REACH = 145
ZOOM = 1.75
KEYS = {pg.K_w:(0,-1), pg.K_UP:(0,-1), pg.K_s:(0,1), pg.K_DOWN:(0,1),
        pg.K_a:(-1,0), pg.K_LEFT:(-1,0), pg.K_d:(1,0), pg.K_RIGHT:(1,0)}

class CameraMixin:
    def init_camera(self):
        self.owner = pg.Vector2(370, 570)
        self.camera_keys = set()
        self.camera_touch = None
        self.touch_anchor = None
        self.move_direction = pg.Vector2()
        self.primary_finger = None
        self.finger_events = False
        self.camera_origin = self.camera_goal()
        self.camera_floor = self.floor

    def camera_active(self):
        return hasattr(self, 'owner') and self.world.open and not self.staff_panel and not self.modal

    def camera_goal(self):
        width, height = VIEW.width / ZOOM, VIEW.height / ZOOM
        return pg.Vector2(max(WORLD.left, min(self.owner.x-width/2, WORLD.right-width)),
                          max(WORLD.top, min(self.owner.y-height/2, WORLD.bottom-height)))

    def point(self, point):
        logical = super().point(point)
        if self.camera_active() and VIEW.collidepoint(logical):
            return (self.camera_origin.x+(logical[0]-VIEW.x)/ZOOM,
                    self.camera_origin.y+(logical[1]-VIEW.y)/ZOOM)
        return logical

    def camera_free(self, point):
        x,y = point
        if not (48 <= x <= 1150 and 165 <= y <= 924): return False
        # The front wall has one doorway; kitchen counters and tables are solid.
        if 239 <= y <= 286 and not 236 <= x <= 338: return False
        from app import MACHINE, SINK, RAW, TRASH
        from model import POT_POS, BOWL_POS
        obstacles = [MACHINE, SINK, RAW, TRASH]
        obstacles += [pg.Rect(px-51,py-40,102,86) for px,py in POT_POS]
        obstacles += [pg.Rect(px-49,py-30,98,76) for px,py in BOWL_POS]
        for i,table in enumerate(self.world.tables):
            if table.floor == self.floor:
                tx,ty=self.world.table_position(i)
                obstacles.append(pg.Rect(tx-92,ty-50,184,96))
        return not any(r.inflate(20,20).collidepoint(point) for r in obstacles)

    def movement_floor(self, logical):
        if not VIEW.collidepoint(logical) or MINI.collidepoint(logical):return False
        point=(self.camera_origin.x+(logical[0]-VIEW.x)/ZOOM,
               self.camera_origin.y+(logical[1]-VIEW.y)/ZOOM)
        if any(rect.collidepoint(point) for rect,_ in self.buttons):return False
        if DOOR.collidepoint(point) or DESK.collidepoint(point):return False
        if self.hit_party(point) or self.hit_table(point) is not None or self.cleaning_target(point):return False
        from app import MACHINE,TICKET,SINK,RAW,TRASH,TOPPING_RECTS,DRINK_RECTS
        from model import POT_POS,BOWL_POS
        if any(r.collidepoint(point) for r in [MACHINE,TICKET,SINK,RAW,TRASH,*TOPPING_RECTS.values(),*DRINK_RECTS.values()]):return False
        if any(math.dist(point,pos)<55 for pos in [*POT_POS,*BOWL_POS]):return False
        return self.camera_free(point)

    def cancel_movement(self):
        self.camera_keys.clear();self.camera_touch=None;self.touch_anchor=None
        self.move_direction.update(0,0)

    def event(self, event):
        # Some browsers send SDL finger events plus emulated mouse events. Handle one stream.
        if event.type in (pg.FINGERDOWN,pg.FINGERMOTION,pg.FINGERUP):
            self.finger_events=True
            if event.type==pg.FINGERDOWN:
                if self.primary_finger is not None:return
                self.primary_finger=event.finger_id
            if event.finger_id!=self.primary_finger:return
            dw,dh=self.display.get_size();pos=(event.x*dw,event.y*dh)
            kind={pg.FINGERDOWN:pg.MOUSEBUTTONDOWN,pg.FINGERMOTION:pg.MOUSEMOTION,pg.FINGERUP:pg.MOUSEBUTTONUP}[event.type]
            if event.type==pg.FINGERUP:self.primary_finger=None
            event=pg.event.Event(kind,pos=pos,button=1,rel=(0,0),buttons=(1,0,0))
        elif getattr(event,'touch',False) and self.finger_events:return
        if event.type in (pg.MOUSEMOTION,pg.MOUSEBUTTONDOWN,pg.MOUSEBUTTONUP):self.camera_pointer=event.pos
        if event.type==pg.WINDOWFOCUSLOST:self.cancel_movement();self.primary_finger=None
        if event.type==pg.KEYUP and event.key in KEYS:self.camera_keys.discard(event.key);return
        if self.camera_active():
            if event.type==pg.KEYDOWN and event.key in KEYS:
                self.camera_keys.add(event.key);self.no_input_seconds=0;return
            if event.type in (pg.MOUSEBUTTONDOWN,pg.MOUSEBUTTONUP,pg.MOUSEMOTION):
                logical=super().point(event.pos)
                if event.type==pg.MOUSEBUTTONUP and event.button==1 and self.touch_anchor is not None:
                    self.touch_anchor=None;self.camera_touch=None;self.move_direction.update(0,0);return
                if event.type==pg.MOUSEBUTTONDOWN and event.button==1 and self.movement_floor(logical):
                    self.touch_anchor=pg.Vector2(logical);self.camera_touch=(0,0);self.no_input_seconds=0;return
                if event.type==pg.MOUSEMOTION and self.touch_anchor is not None:
                    delta=pg.Vector2(logical)-self.touch_anchor
                    self.camera_touch=tuple(delta.normalize()*min(1,delta.length()/60)) if delta.length()>8 else (0,0)
                    return
        else:self.cancel_movement()
        return super().event(event)

    def action(self, action):
        kind=action[0]
        if kind=='staff_panel' and self.modal=='desk':self.modal=None
        if kind=='answer' and self.modal=='guest':
            p=self.world.group(action[1])
            if not p or p.phase not in ('door','waiting') or not self.near_party(p):
                self.modal=None;return
            result=super().action(action);self.modal=None;return result
        if kind=='close' and self.modal=='entrance':
            self.modal=None
            return super().action(action)
        if kind=='context':
            self.modal=action[1];self.cancel_movement();return
        if kind=='presentation':self.cancel_movement();self.modal='presentation';return
        if kind=='music_toggle':
            import sys
            if sys.platform=='emscripten':
                import platform
                platform.window.sobaAudio.toggleMusic()
            return
        if kind=='fullscreen':return # The DOM requests it synchronously on the actual pointer gesture.
        return super().action(action)

    def step(self, dt):
        super().step(dt)
        if not self.camera_active():
            self.cancel_movement(); return
        if self.camera_floor != self.floor:
            self.camera_floor=self.floor; self.owner.update(370,570)
            self.camera_origin=self.camera_goal()
        # Cleaning holds stay fixed. A carried bowl can travel with the camera.
        if self.clean_hold or (self.down and not self.drag):
            self.move_direction.update(0,0);return
        direction=pg.Vector2(self.camera_touch or (0,0))
        for key in self.camera_keys: direction += KEYS[key]
        if self.drag and hasattr(self,'camera_pointer'):
            px,py=super().point(self.camera_pointer)
            if VIEW.collidepoint((px,py)):
                direction += (int(px>VIEW.right-45)-int(px<VIEW.left+45),
                              int(py>VIEW.bottom-45)-int(py<VIEW.top+45))
        if direction.length_squared():
            self.move_direction=direction.normalize()
            direction=self.move_direction*min(1,direction.length())*190*min(dt,.1)
            # Small steps prevent tunnelling through a counter after a slow frame.
            steps=max(1,math.ceil(direction.length()/4)); delta=direction/steps
            for _ in range(steps):
                for axis in (0,1):
                    trial=self.owner.copy(); trial[axis]+=delta[axis]
                    if self.camera_free(trial): self.owner=trial
            self.no_input_seconds=0
        else:self.move_direction.update(0,0)
        self.camera_origin += (self.camera_goal()-self.camera_origin)*min(1,dt*12)
        # Re-map a stationary pointer after the camera pans, before hit testing.
        if hasattr(self,'camera_pointer'): self.mouse=self.point(self.camera_pointer)


    def button(self, rect, label, action, *args, **kwargs):
        if self.world.open and action[0]=='close' and rect[1]<97:
            label='Cách chơi';action=('modal','help')
        return super().button(rect,label,action,*args,**kwargs)

    def render_side(self):
        # No sidebar or invisible sidebar hitboxes. These signs live in world coordinates.
        self.box(DOOR,'#426f57',5)
        self.text('CỬA QUÁN',DOOR.center,14,'#fff2d2',True,True)
        self.box(DESK,'#755235',5)
        self.text('BẢNG QUẢN LÝ',DESK.center,14,'#fff2d2',True,True)
        nearby=[p for p in self.world.parties if p.phase in ('door','waiting') and self.near_party(p)]
        if nearby:
            p=nearby[0]
            self.text('Chạm nhóm để tiếp đón',(p.x,p.y-86),15,'#234c43',True,True)

    def near_party(self,p):
        if p.table>=0:
            if self.world.tables[p.table].floor!=self.floor:return False
            target=self.world.table_position(p.table)
        else:
            if self.floor!=0:return False
            target=(p.x,p.y)
        return self.owner.distance_to(target)<=REACH

    def source(self,point):
        p=self.hit_party(point)
        if p and not self.near_party(p):return None
        return super().source(point)

    def click(self,point,right=False):
        if self.camera_active() and not right:
            # Header and floor navigation still use their regular buttons.
            if any(rect.collidepoint(point) for rect,_ in self.buttons):
                return super().click(point,right)
            for rect,kind in ((DOOR,'entrance'),(DESK,'desk')):
                if rect.collidepoint(point):
                    if self.owner.distance_to(rect.center)>REACH:
                        self.last_warning='Hãy đến gần để tương tác.';return
                    if kind=='entrance' and self.floor!=0:
                        self.last_warning='Hãy xuống tầng 1 để đóng quán.';return
                    self.last_warning='';self.modal=kind;self.cancel_movement();return
            from app import TICKET
            if TICKET.collidepoint(point):
                if self.floor!=0 or self.owner.distance_to(TICKET.center)>REACH:
                    self.last_warning='Hãy đến gần máy bán vé để nhận phiếu.';return
                result=super().click(point,right)
                p=self.world.group(self.selected)
                if p and p.ticket_read:self.modal='guest';self.cancel_movement()
                return result
            p=self.hit_party(point)
            if p:
                if not self.near_party(p):
                    self.last_warning='Hãy đi đến gần nhóm khách rồi chạm vào họ.';return
                self.selected=p.id;self.last_warning='';self.modal='guest';self.cancel_movement();return
        return super().click(point,right)

    def render_context(self):
        # Context dialogs are screen-space; simulation continues as with existing dialogs.
        self.buttons=[]
        shade=pg.Surface((1600,1000),pg.SRCALPHA);shade.fill((12,28,22,145));self.canvas.blit(shade,(0,0))
        self.box((270,140,1060,720),'#fff2d2',18,border='#b7b793')
        if self.modal=='guest':
            p=self.world.group(self.selected)
            if not p or p.phase=='leaving':
                self.text('Nhóm khách đã rời đi',(800,235),30,center=True)
            elif p.phase in ('door','waiting'):
                self.text(f'Nhóm {p.id:03} · {p.size} người',(800,205),32,bold=True,center=True)
                self.text(f'“Chúng tôi có {p.size} người. Quán còn chỗ không?”',(800,290),26,center=True)
                self.button((365,385,870,70),'Còn chỗ, mời khách vào',('answer',p.id,'accept'))
                self.button((365,480,870,70),'Hết chỗ, bạn có thể đợi không?',('answer',p.id,'wait'),color='#97713b')
                self.button((365,575,870,70),'Hết nguyên liệu, hôm nay không nhận khách nữa',('answer',p.id,'decline'),color='#ba4d3c')
            else:
                self.text(f'PHIẾU NHÓM {p.id:03} · {p.size} người',(800,198),30,bold=True,center=True)
                if p.ticket_read:
                    self.text('Kéo nhóm vào bàn sau khi đóng phiếu.' if p.table<0 else f'Tầng {self.world.tables[p.table].floor+1} · Bàn {p.table+1}',(800,246),22,center=True)
                    y=286
                    for i,order in enumerate(p.orders):
                        self.text(f'{i+1}. {order}'+(' ✓' if i<len(p.meals) else ''),(325,y),22,bold=True)
                        self.wrap(' · '.join(f'{name} ×{p.recipes[i].count(name)}' for name in dict.fromkeys(p.recipes[i])),(345,y+28),910,17)
                        y+=75
                    if p.drinks:self.text('Đồ uống: '+', '.join(d or '—' for d in p.drinks),(325,610),19)
                else:
                    self.wrap('Khách đang chọn món hoặc chờ mua phiếu. Đến máy và chạm phiếu màu vàng để nhận khi khách mua xong.',(335,320),930,26)
                if self.world.refund_amount(p.id):
                    self.button((400,660,800,55),'Hết nguyên liệu · Hoàn tiền và mời khách về',('refund_review',p.id),small=True,color='#ba4d3c')
        elif self.modal=='entrance':
            self.text('CỬA QUÁN',(800,215),34,bold=True,center=True)
            self.wrap('Ngừng nhận khách mới, phục vụ những khách còn lại và dọn sạch quán trước khi xác nhận kết thúc ca.',(355,320),900,27)
            self.button((395,525,810,75),'Dọn xong · xác nhận đóng' if self.world.closing else 'Ngừng nhận khách · chuẩn bị đóng quán',('close',))
        else:
            self.text('BẢNG QUẢN LÝ',(800,200),34,bold=True,center=True)
            for i,(label,action) in enumerate([('Nhân viên / lịch làm việc',('staff_panel',)),('Chi phí / hóa đơn',('modal','finance')),('Đánh giá của khách',('modal','reviews')),('Màn hình / nhạc',('presentation',)),('Cách chơi',('modal','help'))]):
                self.button((410,280+i*85,780,65),label,action)
        self.button((560,770,480,60),'Trở lại quán',('dismiss',))

    def render_modal(self):
        if self.world.open and not self.staff_panel and self.modal in (None,'guest','entrance','desk'):
            self.person(self.owner.x,self.owner.y,'#46b7aa',self.animation*8 if self.camera_keys or self.camera_touch else 0)
            pg.draw.circle(self.canvas,'#fff2d2',(round(self.owner.x),round(self.owner.y+8)),19,2)
            self.text('CHỦ QUÁN',(self.owner.x,self.owner.y-44),13,'#234c43',True,True)
            # Crop only the world: header, ticket panel, log and dialogs stay fixed.
            crop=pg.Rect(round(self.camera_origin.x),round(self.camera_origin.y),
                         round(VIEW.width/ZOOM),round(VIEW.height/ZOOM))
            scene=self.canvas.subsurface(crop).copy()
            self.canvas.blit(pg.transform.smoothscale(scene,VIEW.size),VIEW)
            if self.move_direction.length_squared():
                center=pg.Vector2(VIEW.x,VIEW.y)+(self.owner-self.camera_origin)*ZOOM
                forward=self.move_direction;side=pg.Vector2(-forward.y,forward.x)
                tip=center+forward*75
                base=center+forward*43
                points=[tip,base+side*14,base-side*14]
                pg.draw.polygon(self.canvas,'#fff2d2',points)
                pg.draw.polygon(self.canvas,'#217f74',points,3)
            self.box((16,895,330,42),'#233d32',8)
            self.text('Chạm sàn trống, giữ và kéo để đi',(30,905),16,'#fff2d2')
            if self.drag:
                self.box((354,895,617,42),'#233d32',8)
                self.text('Kéo sát mép để đi tiếp · Thả đúng bàn/nồi', (368,905),16,'#fff2d2')
            # Mini-map gives context even when the door or cooking area is offscreen.
            mini=MINI
            self.box(mini,'#233d32',8,border='#bcd0b1')
            self.text(f'T{self.floor+1} · Sàn bẩn: {len(self.world.dirt)}',(mini.centerx,mini.y+15),12,'#fff2d2',True,True)
            def map_point(x,y):return (int(mini.x+9+x/1177*153),int(mini.y+29+(y-97)/850*84))
            pg.draw.rect(self.canvas,'#d6b980',(*map_point(35,270),147,65),border_radius=3)
            pg.draw.rect(self.canvas,'#a8b4a5',(*map_point(775,270),46,65),border_radius=2)
            for i,t in enumerate(self.world.tables):
                if t.floor==self.floor:pg.draw.circle(self.canvas,'#755235',map_point(*self.world.table_position(i)),5)
            pg.draw.circle(self.canvas,'#46b7aa',map_point(*self.owner),4)
        if self.modal in ('guest','entrance','desk'):
            self.render_context();return
        if self.modal=='presentation':
            self.box((280,130,1040,750),'#fff2d2',16,border='#b7b793')
            self.text('MÀN HÌNH & ÂM THANH',(800,185),32,'#26372e',True,True)
            self.wrap('Điện thoại: game thử mở toàn màn hình và khóa ngang khi bạn bấm Vào quán. Nếu máy không cho phép, hãy xoay ngang. iPhone: thêm game vào màn hình chính để mở riêng, ít thanh trình duyệt hơn.',(340,255),920,23)
            self.wrap('Di chuyển: chạm sàn trống, giữ và kéo theo hướng muốn đi. Thả tay để dừng. Mũi tên trước chủ quán chỉ hướng đang đi. Chạm nồi, bàn, nguyên liệu vẫn thao tác như cũ.',(340,415),920,23)
            enabled=True
            import sys
            if sys.platform=='emscripten':
                import platform,json
                enabled=bool(platform.window.sobaAudio.musicEnabled)
                r=pg.Rect(830,635,390,60)
                platform.window.sobaFullscreenRect=json.dumps([self.offset[0]+r.x*self.scale,self.offset[1]+r.y*self.scale,r.width*self.scale,r.height*self.scale])
            self.button((380,635,390,60),'Nhạc nền: '+('Bật' if enabled else 'Tắt'),('music_toggle',),small=True)
            self.button((830,635,390,60),'Toàn màn hình',('fullscreen',),small=True)
            self.button((550,760,500,60),'Trở lại game',('dismiss',))
            return
        import sys
        if sys.platform=='emscripten':
            import platform
            platform.window.sobaFullscreenRect=''
        if not self.modal and not self.staff_panel:
            if self.world.open:pass # Settings are reached through the in-world management board.
            else:self.button((680,80,275,38),'Màn hình / nhạc',('presentation',),small=True)
        super().render_modal()
