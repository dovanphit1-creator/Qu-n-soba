"""Meters, immutable lease, dated invoices and annual assessment."""
from finance import PROVIDERS, STREETS, TAX_RATE
from model import vnd

class FinanceUI:
    def render_finance(self):
        w=self.world
        self.text('CHI PHÍ · Đồng hồ và hóa đơn',(60,397),24,'#26372e',True)
        for i,(kind,options) in enumerate(PROVIDERS.items()):
            m=w.meters[kind];name,rate,unit=options[m['provider']];y=438+i*62
            self.text(f'{name} · {vnd(rate)}/{unit} · Chốt ngày {m["close_day"]}',(60,y),20)
            self.text(f'Đồng hồ {m["reading"]:.3f} {unit} · Chưa chốt {vnd(round(m["cost"]-m["billed_cost"]))}',(60,y+24),17)
            self.button((765,y,150,35),'Đổi đơn vị',('provider_next',kind),not w.open,small=True)
        if w.lease:
            name,rent=STREETS[w.lease['street']]
            self.text(name+' · '+vnd(rent)+'/tháng',(955,442),20,'#26372e',True)
            self.wrap('Kỳ đầu tính theo ngày còn lại. Các tháng sau chốt ngày 1, hạn ngày 8. Hợp đồng giữ nguyên tuyến phố.',(955,479),530,19)
        else:
            self.text('Chọn mặt bằng trước khi mở quán:',(955,442),19)
            for i,(name,rent) in enumerate(STREETS):
                self.button((955,475+i*39,530,34),name+' · '+vnd(rent)+'/tháng',('lease',i),small=True)
        self.wrap('Giá mô phỏng. Thuế quán 10% lợi nhuận dương năm trước; 4 kỳ hạn 20/6, 20/8, 20/10, 20/12. Không có dữ liệu năm trước: 0 VND.',(955,602),530,18)
        assessment=w.tax_assessments.get(str(w.now.year),{})
        self.text('Thuế '+str(w.now.year)+': '+vnd(assessment.get('total',0))+' · Lãi năm trước '+vnd(assessment.get('profit',0)),(955,573),17)
        self.wrap('Chốt điện nước ga → báo số tiền ngay → hạn 7 ngày sau. Chi phí ghi nhận một lần; trả hóa đơn chỉ giảm tiền mặt.',(60,620),835,17)
        rows=sorted(w.bills,key=lambda b:(b['paid'],b['due'],b['id']))
        page=getattr(self,'finance_page',0);self.finance_page=min(page,max(0,(len(rows)-1)//3))
        for i,b in enumerate(rows[self.finance_page*3:self.finance_page*3+3]):
            y=677+i*53
            status='Không phải nộp' if b['amount']==0 else 'Đã trả' if b['paid'] else 'QUÁ HẠN' if b['due']<w.now.date().isoformat() else 'Chưa trả'
            self.text(b['label']+' · '+vnd(b['amount'])+' · '+status,(60,y),18)
            detail=f'Chốt {b["issued"]} · Hạn {b["due"]}'
            if 'quantity' in b:detail+=f' · {b["start"]:.3f} → {b["end"]:.3f} · {b["quantity"]:.3f} {b["unit"]} × {vnd(b["rate"])}'
            self.text(detail,(60,y+23),16)
            self.button((1340,y,155,36),'Thanh toán',('pay_bill',b['id']),not b['paid'] and w.cash>=b['amount'],small=True)
        self.button((1130,845,170,35),'Trước',('finance_page',-1),self.finance_page>0,small=True)
        self.button((1320,845,170,35),'Sau',('finance_page',1),(self.finance_page+1)*3<len(rows),small=True)

    def finance_action(self,kind,args):
        w=self.world
        if kind=='provider_next':
            k=args[0];w.change_provider(k,(w.meters[k]['provider']+1)%len(PROVIDERS[k]))
        elif kind=='lease':w.sign_lease(args[0])
        elif kind=='pay_bill':w.pay_bill(args[0])
        elif kind=='finance_page':self.finance_page=max(0,getattr(self,'finance_page',0)+args[0])
        else:return False
        self.persist();return True
