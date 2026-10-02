"""Web-only close restaurant view; simulation coordinates remain unchanged."""
import math
import pygame as pg

VIEW = pg.Rect(0, 97, 1177, 850)
ZOOM = 1.75
CONTROLS = [(pg.Rect(82, 755, 64, 64), (0, -1), '↑'),
            (pg.Rect(16, 821, 64, 64), (-1, 0), '←'),
            (pg.Rect(82, 821, 64, 64), (0, 1), '↓'),
            (pg.Rect(148, 821, 64, 64), (1, 0), '→')]
KEYS = {pg.K_w:(0,-1), pg.K_UP:(0,-1), pg.K_s:(0,1), pg.K_DOWN:(0,1),
        pg.K_a:(-1,0), pg.K_LEFT:(-1,0), pg.K_d:(1,0), pg.K_RIGHT:(1,0)}

class CameraMixin:
    def init_camera(self):
        self.owner = pg.Vector2(370, 570)
        self.camera_keys = set()
        self.camera_touch = None
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

    def event(self, event):
        if event.type in (pg.MOUSEMOTION, pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP):
            self.camera_pointer=event.pos
        if event.type == pg.WINDOWFOCUSLOST:
            self.camera_keys.clear(); self.camera_touch=None
        if event.type == pg.KEYUP and event.key in KEYS:
            self.camera_keys.discard(event.key); return
        if self.camera_active():
            if event.type == pg.KEYDOWN and event.key in KEYS:
                self.camera_keys.add(event.key); self.no_input_seconds=0; return
            if event.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION):
                logical=super().point(event.pos)
                if event.type == pg.MOUSEBUTTONUP and event.button==1 and self.camera_touch is not None:
                    self.camera_touch=None; return
                if event.type==pg.MOUSEBUTTONDOWN and event.button==1:
                    for rect,direction,_ in CONTROLS:
                        if rect.collidepoint(logical):
                            self.camera_touch=direction; self.no_input_seconds=0; return
                if event.type==pg.MOUSEMOTION and self.camera_touch is not None:
                    self.camera_touch=next((d for r,d,_ in CONTROLS if r.collidepoint(logical)),(0,0)); return
        else:
            self.camera_keys.clear(); self.camera_touch=None
        return super().event(event)

    def step(self, dt):
        super().step(dt)
        if not self.camera_active():
            self.camera_keys.clear(); self.camera_touch=None; return
        if self.camera_floor != self.floor:
            self.camera_floor=self.floor; self.owner.update(370,570)
            self.camera_origin=self.camera_goal()
        # Cleaning holds stay fixed. A carried bowl can travel with the camera.
        if self.clean_hold or (self.down and not self.drag): return
        direction=pg.Vector2(self.camera_touch or (0,0))
        for key in self.camera_keys: direction += KEYS[key]
        if self.drag and hasattr(self,'camera_pointer'):
            px,py=super().point(self.camera_pointer)
            if VIEW.collidepoint((px,py)):
                direction += (int(px>VIEW.right-45)-int(px<VIEW.left+45),
                              int(py>VIEW.bottom-45)-int(py<VIEW.top+45))
        if direction.length_squared():
            direction=direction.normalize()*190*min(dt,.1)
            # Small steps prevent tunnelling through a counter after a slow frame.
            steps=max(1,math.ceil(direction.length()/4)); delta=direction/steps
            for _ in range(steps):
                for axis in (0,1):
                    trial=self.owner.copy(); trial[axis]+=delta[axis]
                    if self.camera_free(trial): self.owner=trial
            self.no_input_seconds=0
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
            for rect,direction,label in CONTROLS:
                self.box(rect,'#426f57' if self.camera_touch==direction else '#233d32',10,border='#fff2d2')
                self.text(label,rect.center,32,'#fff2d2',True,True)
            self.box((16,895,330,42),'#233d32',8)
            self.text('WASD / mũi tên · Góc nhìn 175%',(30,905),16,'#fff2d2')
            if self.drag:
                self.box((354,895,617,42),'#233d32',8)
                self.text('Kéo sát mép để đi tiếp · Thả đúng bàn/nồi', (368,905),16,'#fff2d2')
            # Mini-map gives context even when the door or cooking area is offscreen.
            mini=pg.Rect(990,112,171,124)
            self.box(mini,'#233d32',8,border='#bcd0b1')
            self.text('BẢN ĐỒ QUÁN',(mini.centerx,mini.y+15),12,'#fff2d2',True,True)
            def map_point(x,y):return (int(mini.x+9+x/1177*153),int(mini.y+29+(y-97)/850*84))
            pg.draw.rect(self.canvas,'#d6b980',(*map_point(35,270),147,65),border_radius=3)
            pg.draw.rect(self.canvas,'#a8b4a5',(*map_point(775,270),46,65),border_radius=2)
            for i,t in enumerate(self.world.tables):
                if t.floor==self.floor:pg.draw.circle(self.canvas,'#755235',map_point(*self.world.table_position(i)),5)
            pg.draw.circle(self.canvas,'#46b7aa',map_point(*self.owner),4)
        super().render_modal()
