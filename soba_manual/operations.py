"""Staff stock emergencies and auditable advances, separate from wages."""
from collections import Counter
from datetime import date
from staff import cycle_key
from model import STOCK_COST


def adopt_unassigned_noodles(w):
    planned={(o['gid'],o['index']) for o in w.staff_cooking.values()}
    for p in sorted(w.parties,key=lambda p:p.id):
        if p.phase!='seated':continue
        for i in range(len(p.meals),p.size):
            if (p.id,i) in planned:continue
            pot=next((j for j,v in enumerate(w.pots) if v is not None and str(j) not in w.staff_cooking),None)
            if pot is not None:w.staff_cooking[str(pot)]={'gid':p.id,'index':i};planned.add((p.id,i));continue
            b=next((b for b in w.bowls if not any(o.get('bid')==b.id for o in w.staff_cooking.values()) and (not b.toppings or Counter(b.toppings)==Counter(p.recipes[i]))),None)
            key=next((str(j) for j in range(6) if str(j) not in w.staff_cooking and w.pots[j] is None),None)
            if b and key is not None:w.staff_cooking[key]={'gid':p.id,'index':i,'bid':b.id,'done':b.stage=='prep' and Counter(b.toppings)==Counter(p.recipes[i])};planned.add((p.id,i))


def required_stock(w):
    needed=Counter();planned={(o['gid'],o['index']):o for o in w.staff_cooking.values()}
    for p in w.parties:
        if p.phase not in ('queue','buying','ticket','ready','seated','eating'):continue
        for i in range(len(p.meals),p.size):
            order=planned.get((p.id,i));b=next((b for b in w.bowls if order and b.id==order.get('bid')),None)
            if not order:needed['Mì tươi']+=1
            needed+=Counter(p.recipes[i])-Counter(b.toppings if b else [])
        for i,name in enumerate(p.drinks):
            if name and p.drinks_served[i]!=name:needed[name]+=1
    manual=sum(v is not None and str(i) not in w.staff_cooking for i,v in enumerate(w.pots))
    manual+=sum(not any(o.get('bid')==b.id for o in w.staff_cooking.values()) for b in w.bowls)
    needed['Mì tươi']=max(0,needed['Mì tươi']-manual)
    return needed


def missing_stock(w):
    needed=required_stock(w)
    missing=Counter({n:max(0,q-w.stock[n]) for n,q in needed.items()})
    viable=any(all(w.stock[n]-needed[n]>=q for n,q in Counter(['Mì tươi',*item['toppings']]).items()) for item in w.menu.values())
    if not viable and not missing:
        if +needed:return Counter()  # Finish prepaid orders before shopping for future guests.
        recipe=min((Counter(['Mì tươi',*m['toppings']]) for m in w.menu.values()),key=lambda c:sum(STOCK_COST[n]*q for n,q in c.items()))
        missing=Counter({n:max(0,q+needed[n]-w.stock[n]) for n,q in recipe.items()})
    return +missing


def refund_unservable(w):
    available=Counter(w.stock)
    for p in sorted(w.parties,key=lambda p:p.id):
        if not w.refund_amount(p.id):continue
        needs=Counter()
        for i in range(len(p.meals),p.size):
            o=next((o for o in w.staff_cooking.values() if o['gid']==p.id and o['index']==i),None)
            b=next((b for b in w.bowls if o and b.id==o.get('bid')),None)
            if not o:needs['Mì tươi']+=1
            needs+=Counter(p.recipes[i])-Counter(b.toppings if b else [])
        for i,n in enumerate(p.drinks):
            if n and p.drinks_served[i]!=n:needs[n]+=1
        if any(available[n]<q for n,q in needs.items()):w.refund_party(p.id)
        else:available.subtract(needs)


def manage_shortage(w,active):
    if not w.open or w.closing or not active:return
    if any(e['job'] and e['job']['action'][0]=='shop' for e in w.employees):return
    adopt_unassigned_noodles(w)
    missing=missing_stock(w)
    if not missing:return
    for p in list(w.parties):
        if p.phase in ('door','waiting'):w.respond(p.id,'decline')
    helpers=[e for e in active if not e['job']]
    if not helpers:return
    e=helpers[0];key=w.now.date().isoformat()
    budget=500000-sum(x['cost'] for x in w.staff_purchases if x['employee']==e['id'] and x['date']==key)
    cost=sum(STOCK_COST[n]*q for n,q in missing.items())
    if e['shortage_policy']=='restock' and cost<=budget:
        e['job']={'action':['shop',dict(missing)],'target':[850,160,0],'left':w.rng.uniform(120,240)}
        e['status']='Ứng tiền đi mua lẻ';w.note(f'{e["name"]}: Hết nguyên liệu, tôi ứng {cost:,.0f} VND đi mua lẻ. Tạm ngừng nhận khách.')
        w.staff_reports.append({'date':key,'text':f'{e["name"]} đang đi mua: '+', '.join(f'{n} × {q}' for n,q in missing.items())})
    else:
        w.closing=True;w.staff_opened_shop=True;w.staff_shutdown_date=key
        refund_unservable(w)
        w.staff_reports.append({'date':key,'text':f'{e["name"]}: hết nguyên liệu; ngừng đón khách, hoàn phiếu không thể làm, dọn sạch và đóng quán.'})
        w.note(w.staff_reports[-1]['text'])


def complete_purchase(w,e,items):
    items={n:q for n,q in items.items() if n in STOCK_COST and type(q)==int and q>0}
    if not items:return False
    cost=sum(STOCK_COST[n]*q for n,q in items.items());key=w.now.date().isoformat()
    for n,q in items.items():w.stock[n]+=q;w.stock_value[n]+=STOCK_COST[n]*q
    w.record('purchases',cost)
    w.staff_purchases.append({'employee':e['id'],'name':e['name'],'date':key,'items':items,'cost':cost,'reimbursed':False})
    w.staff_reports.append({'date':key,'text':f'{e["name"]} đã ứng {cost:,.0f} VND mua: '+', '.join(f'{n} × {q}' for n,q in items.items())})
    w.note(w.staff_reports[-1]['text']);return True


def reimburse(w,e,period,force=False):
    purchases=[r for r in w.staff_purchases if r['employee']==e['id'] and not r['reimbursed'] and (force or (r['date']==period if e['role']=='baito' else cycle_key(date.fromisoformat(r['date']))==period))]
    total=sum(r['cost'] for r in purchases)
    for r in purchases:r['reimbursed']=True;r['paid_date']=w.now.date().isoformat()
    w.cash-=total
    if total:w.record("reimbursement_paid",total)
    if total:w.note(f'Hoàn tiền ứng mua nguyên liệu cho {e["name"]}: {total:,.0f} VND, tách riêng tiền công.')
    return total
