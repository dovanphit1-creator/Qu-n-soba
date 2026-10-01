"""Exercise expansion UI and scheduled deliveries in the packaged application."""
from datetime import datetime, timedelta
from pathlib import Path
import pygame as pg
from model import World, STOCK_COST, POT_POS, BOWL_POS
from vn_calendar import VIETNAM


def check_expansion_ui(app, output):
    clock=[datetime(2026,10,1,22,59,59,tzinfo=VIETNAM)]
    app.world=World(seed=17,clock=lambda:clock[0])
    app.init_management();app.modal=None
    w=app.world

    def button(action):
        app.draw()
        matches=[rect for rect,value in app.buttons if value==action]
        assert matches, ('Missing button',action)
        app.click(matches[0].center)

    def screenshot(name):
        app.draw();pg.image.save(app.canvas,str(Path(output).with_name(name+'.png')))

    assert len(w.tables)==1 and w.tables[0].capacity==4
    button(('tab','expansion'))
    button(('buy_table',0));button(('buy_chair',1));button(('buy_chair',1))
    button(('build_floor',));assert w.floors==2 and app.floor==1
    button(('buy_table',1));button(('buy_chair',2));button(('buy_chair',2))
    screenshot('expansion-preview')
    button(('tab','supplier'));button(('contract',))
    for i,name in enumerate(STOCK_COST):
        if i and i%6==0:button(('supplier_page',1))
        button(('order_qty',name,10))
    button(('order',));assert len(w.deliveries)==1
    screenshot('supplier-preview')
    clock[0]=datetime(2026,10,2,7,59,59,tzinfo=VIETNAM)
    app.step(0);assert w.stock['Mì tươi']==0
    clock[0]+=timedelta(seconds=1)
    app.step(0);assert w.stock['Mì tươi']==10
    app.step(0);assert w.stock['Mì tươi']==10

    button(('tab','menu'))
    button(('field','name'))
    app.event(pg.event.Event(pg.TEXTINPUT,text='Soba trứng đôi'))
    app.event(pg.event.Event(pg.KEYDOWN,key=pg.K_TAB))
    app.event(pg.event.Event(pg.TEXTINPUT,text='65000'))
    button(('recipe_page',1))
    button(('recipe_qty','Trứng',1));button(('recipe_qty','Trứng',1))
    button(('recipe_page',-1))
    button(('recipe_qty','Hành',1))
    screenshot('menu-preview')
    button(('save_menu',))
    assert w.menu['Soba trứng đôi']['toppings'].count('Trứng')==2
    for name in list(w.menu):
        if name!='Soba trứng đôi':w.delete_menu_item(name)
    w.restock('Bát/đĩa',10)
    button(('open',));w.spawn_left=100000
    app.floor=0
    for size in (2,2):
        p=w.add_party(size);w.respond(p.id,'accept');w.update(p.buy_seconds);w.collect(p.id)
        app.selected=p.id;app.drop(('party',p.id),w.table_position(0))
    first,second=w.parties[:2]
    assert not set(first.seats)&set(second.seats)
    assert w.free_seats(0)==[]
    app.draw();app.click(app.table_group_rect(0,1).center)
    assert app.selected==second.id
    for i in range(2):app.drop(('raw',0),POT_POS[i])
    app.step(210)
    for i in range(2):
        app.click(POT_POS[i]);b=w.bowls[-1]
        app.drop(('bowl',b.id),BOWL_POS[0])
        for name in second.recipes[i]:app.drop(('topping',name),BOWL_POS[0])
        app.drop(('bowl',b.id),w.table_position(0))
    assert len(first.meals)==0 and len(second.meals)==2
    screenshot('shared-preview')
    p=w.add_party(1);w.respond(p.id,'accept');w.update(p.buy_seconds);w.collect(p.id)
    app.drag=('party',p.id)
    app.event(pg.event.Event(pg.KEYDOWN,key=pg.K_2))
    assert app.floor==1 and app.drag==('party',p.id)
    app.drop(app.drag,w.table_position(2));app.drag=None
    assert w.tables[p.table].floor==1
    # Bundled persistence includes floor, menu, stock valuation and settled deliveries.
    path=Path(output).with_name('expanded-test-save.json')
    w.save(path);loaded=World.load(path)
    loaded._clock=lambda:clock[0]
    assert loaded.floors==2 and loaded.group(second.id).seats==second.seats
    assert loaded.menu==w.menu and not loaded.process_deliveries()
    app.world=loaded
    app.draw()
