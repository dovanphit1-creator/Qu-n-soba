#!/usr/bin/env python3
"""Quán Soba: giao diện desktop bằng Tkinter, không cần thư viện ngoài."""
import json
from pathlib import Path
import random
import sys
import tkinter as tk
from tkinter import messagebox, ttk

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SAVE = APP_DIR / "soba_gui_save.json"
COST = {"Mì": 45, "Nước dùng": 35, "Rau": 20, "Thịt": 60}
LIMIT = {"Mì": 120, "Nước dùng": 100, "Rau": 80, "Thịt": 60}
BASE = {"Truyền thống": 160, "Đặc biệt": 250}
UP = {
    "Bếp": (900, "Thêm 8 tô mỗi ngày"),
    "Biển hiệu": (700, "Thu hút thêm khách"),
    "Bàn ghế": (650, "Thêm 6 tô mỗi ngày"),
}
WEATHER = [("Trời mát", 1), ("Nắng đẹp", 1.15), ("Mưa", .8), ("Lễ hội", 1.45)]


def new_game():
    return {
        "day": 1, "cash": 1800, "rep": 50, "weather": 0,
        "stock": {"Mì": 12, "Nước dùng": 12, "Rau": 12, "Thịt": 5},
        "price": BASE.copy(), "upgrades": [], "ad": False,
        "last": "Chào mừng đến Quán Soba! Hãy chuẩn bị nguyên liệu và mở cửa.",
    }


def load():
    try:
        data = json.loads(SAVE.read_text(encoding="utf-8"))
        if (set(data["stock"]) != set(COST) or set(data["price"]) != set(BASE)
                or not 0 <= data["rep"] <= 100 or data["day"] < 1):
            raise ValueError("Dữ liệu lưu không hợp lệ")
        return data
    except FileNotFoundError:
        return new_game()
    except (OSError, ValueError, TypeError, KeyError):
        return new_game()


def fmt(n):
    return f"{n:,} xu"


class SobaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quán Soba — Game quản lý quán mì")
        self.geometry("1050x740")
        self.minsize(780, 620)
        self.configure(bg="#14232a")
        self.state_data = load()
        self.price_vars = {name: tk.StringVar() for name in BASE}
        self.setup_style()
        self.build_ui()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.quit_game)

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#14232a")
        style.configure("Card.TFrame", background="#20363e")
        style.configure("TLabel", background="#20363e", foreground="#f5f0e7",
                        font=("Segoe UI", 11))
        style.configure("Muted.TLabel", background="#20363e", foreground="#b6c9ca",
                        font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#14232a", foreground="#f5d28c",
                        font=("Segoe UI", 26, "bold"))
        style.configure("Head.TLabel", background="#20363e", foreground="#f2d18e",
                        font=("Segoe UI", 14, "bold"))
        style.configure("Stat.TLabel", background="#20363e", foreground="#ffffff",
                        font=("Segoe UI", 17, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8),
                        background="#d9ad62", foreground="#14232a")
        style.map("TButton", background=[("active", "#f2cb85")])
        style.configure("Open.TButton", font=("Segoe UI", 13, "bold"),
                        padding=(15, 12), background="#e5b35e")
        style.configure("TEntry", font=("Segoe UI", 11), padding=6)

    def card(self, parent, title):
        box = ttk.Frame(parent, style="Card.TFrame", padding=18)
        box.pack(fill="x", pady=(0, 14))
        ttk.Label(box, text=title, style="Head.TLabel").pack(anchor="w", pady=(0, 10))
        return box

    def build_ui(self):
        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="QUÁN SOBA", style="Title.TLabel").pack(anchor="w")
        tk.Label(outer, text="Mục tiêu: 10.000 xu và 80 danh tiếng",
                 bg="#14232a", fg="#b6c9ca", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 14))
        stats = ttk.Frame(outer)
        stats.pack(fill="x", pady=(0, 14))
        self.stats = {}
        for i, label in enumerate(("Ngày", "Tiền mặt", "Danh tiếng", "Thời tiết")):
            stats.columnconfigure(i, weight=1)
            box = ttk.Frame(stats, style="Card.TFrame", padding=12)
            box.grid(row=0, column=i, sticky="ew", padx=(0, 8))
            ttk.Label(box, text=label, style="Muted.TLabel").pack(anchor="w")
            val = ttk.Label(box, style="Stat.TLabel")
            val.pack(anchor="w")
            self.stats[label] = val
        columns = ttk.Frame(outer)
        columns.pack(fill="both", expand=True)
        left = ttk.Frame(columns)
        right = ttk.Frame(columns)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        stock_box = self.card(left, "Kho nguyên liệu")
        self.stock_labels = {}
        for name, cost in COST.items():
            line = ttk.Frame(stock_box, style="Card.TFrame")
            line.pack(fill="x", pady=5)
            label = ttk.Label(line, style="TLabel")
            label.pack(side="left")
            self.stock_labels[name] = label
            ttk.Button(line, text="Mua 5", command=lambda n=name: self.buy(n, 5)).pack(side="right")
            ttk.Button(line, text="Mua 1", command=lambda n=name: self.buy(n, 1)).pack(side="right", padx=5)
        ttk.Label(stock_box, text="Mỗi tô cần mì, nước dùng, rau. Tô đặc biệt cần thêm thịt.",
                  style="Muted.TLabel", wraplength=410).pack(anchor="w", pady=(10, 0))

        menu_box = self.card(left, "Thực đơn và giá bán")
        for name in BASE:
            line = ttk.Frame(menu_box, style="Card.TFrame")
            line.pack(fill="x", pady=6)
            ttk.Label(line, text=f"Soba {name.lower()} (gợi ý {fmt(BASE[name])})",
                      style="TLabel").pack(side="left")
            ttk.Entry(line, textvariable=self.price_vars[name], width=8).pack(side="right")
        ttk.Button(menu_box, text="Áp dụng giá", command=self.set_prices).pack(anchor="e", pady=(8, 0))

        upgrade_box = self.card(right, "Nâng cấp quán")
        self.upgrade_buttons = {}
        for name, (price, effect) in UP.items():
            line = ttk.Frame(upgrade_box, style="Card.TFrame")
            line.pack(fill="x", pady=5)
            ttk.Label(line, text=f"{name} · {fmt(price)}\n{effect}",
                      style="TLabel").pack(side="left")
            button = ttk.Button(line, text="Mua", command=lambda n=name: self.upgrade(n))
            button.pack(side="right")
            self.upgrade_buttons[name] = button
        action = self.card(right, "Kinh doanh")
        self.ad_button = ttk.Button(action, text="Quảng cáo · 150 xu", command=self.advertise)
        self.ad_button.pack(fill="x", pady=(0, 8))
        ttk.Button(action, text="MỞ CỬA ĐÓN KHÁCH", style="Open.TButton",
                   command=self.service).pack(fill="x")

        result = self.card(right, "Kết quả gần nhất")
        self.result_label = ttk.Label(result, style="TLabel", wraplength=420, justify="left")
        self.result_label.pack(anchor="w")
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(4, 0))
        ttk.Button(bottom, text="Chơi lại từ đầu", command=self.reset).pack(side="left")
        ttk.Button(bottom, text="Lưu và thoát", command=self.quit_game).pack(side="right")

    def save(self):
        try:
            SAVE.write_text(json.dumps(self.state_data, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Không lưu được", str(exc))

    def refresh(self):
        s = self.state_data
        for name, value in zip(self.stats, (str(s["day"]), fmt(s["cash"]),
                                           f'{s["rep"]}/100', WEATHER[s["weather"]][0])):
            self.stats[name].config(text=value)
        for name in COST:
            self.stock_labels[name].config(
                text=f'{name}: {s["stock"][name]}/{LIMIT[name]} · {fmt(COST[name])}/phần')
        for name in BASE:
            self.price_vars[name].set(str(s["price"][name]))
        for name, button in self.upgrade_buttons.items():
            owned = name in s["upgrades"]
            button.config(text="Đã có" if owned else "Mua",
                          state="disabled" if owned else "normal")
        self.ad_button.config(text="Đã quảng cáo hôm nay" if s["ad"] else "Quảng cáo · 150 xu",
                              state="disabled" if s["ad"] else "normal")
        self.result_label.config(text=s["last"])

    def buy(self, name, count):
        s = self.state_data
        count = min(count, LIMIT[name] - s["stock"][name])
        if count <= 0:
            messagebox.showinfo("Kho đầy", f"Kho {name.lower()} đã đầy.")
        elif s["cash"] < count * COST[name]:
            messagebox.showinfo("Thiếu tiền", "Bạn chưa đủ xu để mua số lượng này.")
        else:
            s["cash"] -= count * COST[name]
            s["stock"][name] += count
            self.save()
            self.refresh()

    def set_prices(self):
        values = {}
        try:
            for name, var in self.price_vars.items():
                values[name] = int(var.get())
                if not 80 <= values[name] <= 500:
                    raise ValueError
        except ValueError:
            messagebox.showwarning("Giá không hợp lệ", "Nhập giá nguyên từ 80 đến 500 xu.")
            return
        self.state_data["price"].update(values)
        self.save()
        self.refresh()
        messagebox.showinfo("Đã cập nhật", "Giá bán mới đã được áp dụng.")

    def upgrade(self, name):
        s = self.state_data
        price = UP[name][0]
        if s["cash"] < price:
            messagebox.showinfo("Thiếu tiền", "Bạn chưa đủ xu để nâng cấp.")
            return
        s["cash"] -= price
        s["upgrades"].append(name)
        self.save()
        self.refresh()

    def advertise(self):
        s = self.state_data
        if s["cash"] < 150:
            messagebox.showinfo("Thiếu tiền", "Bạn cần 150 xu để quảng cáo.")
            return
        s["cash"] -= 150
        s["ad"] = True
        self.save()
        self.refresh()

    def service(self):
        s = self.state_data
        capacity = 18 + (8 if "Bếp" in s["upgrades"] else 0)
        capacity += 6 if "Bàn ghế" in s["upgrades"] else 0
        potential = max(0, round(
            (random.randint(13, 20) + (s["rep"] - 50) / 10
             + (4 if "Biển hiệu" in s["upgrades"] else 0)
             + (6 if s["ad"] else 0)) * WEATHER[s["weather"]][1]))
        visitors = min(potential, capacity)
        sold = {"Truyền thống": 0, "Đặc biệt": 0}
        revenue = lost = 0
        for _ in range(visitors):
            order = (["Đặc biệt", "Truyền thống"] if random.random() < .38
                     else ["Truyền thống", "Đặc biệt"])
            served = False
            for name in order:
                chance = min(.98, max(.18, .92 - (s["price"][name] / BASE[name] - 1) * .75))
                if random.random() >= chance:
                    continue
                ingredients = ["Mì", "Nước dùng", "Rau"]
                if name == "Đặc biệt":
                    ingredients.append("Thịt")
                if all(s["stock"][item] > 0 for item in ingredients):
                    for item in ingredients:
                        s["stock"][item] -= 1
                    sold[name] += 1
                    revenue += s["price"][name]
                    served = True
                    break
            if not served:
                lost += 1
        expenses = 460 + (60 if "Bếp" in s["upgrades"] else 0)
        profit = revenue - expenses
        s["cash"] += profit
        total = sum(sold.values())
        change = (2 if total >= 12 else 0) - min(5, lost // 3)
        if total <= 5:
            change -= 2
        s["rep"] = min(100, max(0, s["rep"] + change))
        summary = (f'Ngày {s["day"]}: {visitors} khách ghé · {total} tô bán được.\n'
                   f'Truyền thống: {sold["Truyền thống"]} · Đặc biệt: {sold["Đặc biệt"]} · '
                   f'Khách bỏ đi: {lost}.\n'
                   f'Doanh thu: {fmt(revenue)} · Thuê và lương: {fmt(expenses)}.\n'
                   f'Lãi/lỗ vận hành: {fmt(profit)} · Danh tiếng: {s["rep"]}/100.')
        if s["cash"] >= 10000 and s["rep"] >= 80:
            summary += "\nChúc mừng! Quán soba của bạn đã nổi tiếng!"
        s["last"] = summary
        s["day"] += 1
        s["weather"] = random.randrange(len(WEATHER))
        s["ad"] = False
        self.save()
        self.refresh()

    def reset(self):
        if messagebox.askyesno("Chơi lại", "Xóa tiến trình hiện tại và chơi lại?"):
            self.state_data = new_game()
            self.save()
            self.refresh()

    def quit_game(self):
        self.save()
        self.destroy()


if __name__ == "__main__":
    SobaApp().mainloop()
