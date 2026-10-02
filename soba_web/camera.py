"""Web-only close restaurant view; simulation coordinates remain unchanged."""
import math
import pygame as pg

VIEW = pg.Rect(0, 97, 1177, 850)
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
        return pg.Vector2(max(VIEW.left, min(self.owner.x-width/2, VIEW.right-width)),
                          max(VIEW.top, min(self.owner.y-height/2, VIEW.bottom-height)))

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
        if not VIEW.collidepoint(logical) or pg.Rect(990,112,171,124).collidepoint(logical):return False
        point=(self.camera_origin.x+(logical[0]-VIEW.x)/ZOOM,
               self.camera_origin.y+(logical[1]-VIEW.y)/ZOOM)
        if any(rect.collidepoint(point) for rect,_ in self.buttons):return False
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

    def render_modal(self):
        if self.camera_active():
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
            mini=pg.Rect(990,112,171,124)
            self.box(mini,'#233d32',8,border='#bcd0b1')
            self.text(f'T{self.floor+1} · Sàn bẩn: {len(self.world.dirt)}',(mini.centerx,mini.y+15),12,'#fff2d2',True,True)
            def map_point(x,y):return (int(mini.x+9+x/1177*153),int(mini.y+29+(y-97)/850*84))
            pg.draw.rect(self.canvas,'#d6b980',(*map_point(35,270),147,65),border_radius=3)
            pg.draw.rect(self.canvas,'#a8b4a5',(*map_point(775,270),46,65),border_radius=2)
            for i,t in enumerate(self.world.tables):
                if t.floor==self.floor:pg.draw.circle(self.canvas,'#755235',map_point(*self.world.table_position(i)),5)
            pg.draw.circle(self.canvas,'#46b7aa',map_point(*self.owner),4)
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
            if self.world.open:self.button((1207,825,169,45),'Màn hình / nhạc',('presentation',),small=True)
            else:self.button((680,80,275,38),'Màn hình / nhạc',('presentation',),small=True)
        super().render_modal()
