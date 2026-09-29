#!/usr/bin/env python3
"""Quán Soba - game quản lý quán ăn chạy bằng thư viện chuẩn Python."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import random
import sys

APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SAVE_FILE = APP_DIR / "soba_save.json"
INGREDIENTS = {
    "mì": (120, 45),
    "nước dùng": (100, 35),
    "rau": (80, 20),
    "thịt": (60, 60),
}
RECIPES = {
    "Soba truyền thống": {"mì": 1, "nước dùng": 1, "rau": 1},
    "Soba đặc biệt": {"mì": 1, "nước dùng": 1, "rau": 1, "thịt": 1},
}
BASE_PRICES = {"Soba truyền thống": 160, "Soba đặc biệt": 250}
WEATHERS = {
    "nắng đẹp": (1.15, "Khách muốn ăn món nhẹ và mát."),
    "mưa": (0.80, "Khách ra đường ít hơn."),
    "trời mát": (1.00, "Một ngày thuận lợi cho quán soba."),
    "lễ hội": (1.45, "Phố đông khách hơn thường lệ!"),
}
UPGRADES = {
    "bếp": (900, "Tăng số tô có thể phục vụ mỗi ngày thêm 8."),
    "biển hiệu": (700, "Thu hút thêm khoảng 4 khách mỗi ngày."),
    "bàn ghế": (650, "Tăng số tô có thể phục vụ mỗi ngày thêm 6."),
}


def ask_int(prompt, minimum, maximum):
    """Đọc số nguyên trong khoảng; người chơi có thể nhập lại nếu sai."""
    while True:
        try:
            number = int(input(prompt).strip())
            if minimum <= number <= maximum:
                return number
        except ValueError:
            pass
        print(f"Vui lòng nhập số từ {minimum} đến {maximum}.")


def money(amount):
    return f"{amount:,} xu"


@dataclass
class Game:
    day: int = 1
    cash: int = 1800
    reputation: int = 50
    inventory: dict = field(default_factory=lambda: {
        "mì": 12, "nước dùng": 12, "rau": 12, "thịt": 5
    })
    prices: dict = field(default_factory=lambda: BASE_PRICES.copy())
    upgrades: list = field(default_factory=list)
    history: list = field(default_factory=list)
    weather: str = "trời mát"
    advertised: bool = False

    @classmethod
    def load(cls):
        if not SAVE_FILE.exists():
            return cls()
        try:
            data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            game = cls(**data)
            if (set(game.inventory) != set(INGREDIENTS)
                    or set(game.prices) != set(RECIPES)
                    or not 0 <= game.reputation <= 100
                    or game.day < 1):
                raise ValueError("Dữ liệu không hợp lệ")
            return game
        except (OSError, ValueError, TypeError) as exc:
            print(f"Không đọc được bản lưu: {exc}. Bắt đầu ván mới.")
            return cls()

    def save(self):
        try:
            SAVE_FILE.write_text(
                json.dumps(self.__dict__, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print("Đã lưu tiến trình.")
        except OSError as exc:
            print(f"Không thể lưu: {exc}")

    def status(self):
        print(f"\n=== NGÀY {self.day} | {self.weather.upper()} ===")
        print(f"Tiền: {money(self.cash)} | Danh tiếng: {self.reputation}/100")
        print("Kho:", ", ".join(f"{name} {count}" for name, count in self.inventory.items()))
        print("Giá:", " | ".join(f"{name}: {money(price)}"
                                 for name, price in self.prices.items()))
        print("Nâng cấp:", ", ".join(self.upgrades) or "chưa có")
        print(f"Quảng cáo hôm nay: {'đã chạy' if self.advertised else 'chưa chạy'}")

    def shop(self):
        names = list(INGREDIENTS)
        while True:
            print(f"\nTiền hiện có: {money(self.cash)}")
            for i, name in enumerate(names, 1):
                cost, price = INGREDIENTS[name]
                print(f"{i}. {name}: {money(price)}/phần (kho {self.inventory[name]}/{cost})")
            print("0. Quay lại")
            choice = ask_int("Chọn nguyên liệu: ", 0, len(names))
            if choice == 0:
                return
            name = names[choice - 1]
            capacity, price = INGREDIENTS[name]
            maximum = min((self.cash // price), capacity - self.inventory[name])
            if maximum == 0:
                print("Không đủ tiền hoặc kho đã đầy.")
                continue
            quantity = ask_int(f"Mua bao nhiêu (0-{maximum})? ", 0, maximum)
            self.cash -= quantity * price
            self.inventory[name] += quantity
            print(f"Đã mua {quantity} phần {name}, tốn {money(quantity * price)}.")

    def set_prices(self):
        for name in RECIPES:
            print(f"{name} đang bán {money(self.prices[name])}.")
            self.prices[name] = ask_int("Giá mới (80-500 xu): ", 80, 500)
        print("Đã cập nhật thực đơn.")

    def improve(self):
        available = [name for name in UPGRADES if name not in self.upgrades]
        if not available:
            print("Quán đã có đủ mọi nâng cấp.")
            return
        for i, name in enumerate(available, 1):
            price, effect = UPGRADES[name]
            print(f"{i}. {name}: {money(price)} — {effect}")
        print("0. Quay lại")
        choice = ask_int("Chọn nâng cấp: ", 0, len(available))
        if choice:
            name = available[choice - 1]
            price = UPGRADES[name][0]
            if self.cash >= price:
                self.cash -= price
                self.upgrades.append(name)
                print(f"Đã nâng cấp {name}!")
            else:
                print("Bạn chưa đủ tiền.")

    def advertise(self):
        if self.advertised:
            print("Hôm nay bạn đã quảng cáo rồi.")
        elif self.cash < 150:
            print("Cần 150 xu để quảng cáo.")
        else:
            self.cash -= 150
            self.advertised = True
            print("Đã chi 150 xu quảng cáo; ngày này sẽ có thêm khách.")

    def service(self, rng):
        """Mô phỏng một ngày: nhu cầu, số chỗ, tồn kho, doanh thu và chi phí."""
        weather_factor, _ = WEATHERS[self.weather]
        capacity = 18 + (8 if "bếp" in self.upgrades else 0)
        capacity += 6 if "bàn ghế" in self.upgrades else 0
        potential = max(0, round(
            (rng.randint(13, 20) + (self.reputation - 50) / 10
             + (4 if "biển hiệu" in self.upgrades else 0)
             + (6 if self.advertised else 0)) * weather_factor
        ))
        visitors = min(potential, capacity)
        sold = {name: 0 for name in RECIPES}
        revenue = 0
        lost = 0
        expensive = 0
        for _ in range(visitors):
            special = rng.random() < 0.38
            choices = (["Soba đặc biệt", "Soba truyền thống"] if special
                       else ["Soba truyền thống", "Soba đặc biệt"])
            served = False
            for name in choices:
                # Giá cao làm khách ngần ngại; giá thấp tăng cơ hội bán.
                ratio = self.prices[name] / BASE_PRICES[name]
                willingness = min(0.98, max(0.18, 0.92 - (ratio - 1) * 0.75))
                if rng.random() >= willingness:
                    expensive += 1
                    continue
                if all(self.inventory[item] >= amount
                       for item, amount in RECIPES[name].items()):
                    for item, amount in RECIPES[name].items():
                        self.inventory[item] -= amount
                    sold[name] += 1
                    revenue += self.prices[name]
                    served = True
                    break
            if not served:
                lost += 1

        rent = 320
        wages = 140 + (60 if "bếp" in self.upgrades else 0)
        expenses = rent + wages
        profit = revenue - expenses
        self.cash += profit
        total = sum(sold.values())
        change = (2 if total >= 12 else 0) - min(5, lost // 3)
        if total <= 5:
            change -= 2
        self.reputation = min(100, max(0, self.reputation + change))
        result = {
            "day": self.day, "weather": self.weather, "visitors": visitors,
            "sold": sold, "lost": lost, "revenue": revenue,
            "expenses": expenses, "profit": profit,
        }
        self.history.append(result)
        print(f"\n--- KẾT QUẢ NGÀY {self.day} ---")
        print(f"Khách ghé: {visitors} | Bán: {total} tô | Bỏ đi: {lost}")
        for name, count in sold.items():
            print(f"  {name}: {count} tô")
        print(f"Doanh thu: {money(revenue)} | Thuê mặt bằng + lương: {money(expenses)}")
        print(f"Lãi/lỗ vận hành: {money(profit)} | Tiền còn: {money(self.cash)}")
        print(f"Danh tiếng: {self.reputation}/100 ({change:+d})")
        if expensive:
            print("Một số khách thấy giá chưa phù hợp.")
        self.day += 1
        self.advertised = False
        self.weather = rng.choice(list(WEATHERS))
        self.save()
        if self.cash < 0:
            print("Quán đang nợ. Hãy điều chỉnh giá và mua nguyên liệu cẩn thận!")
        elif self.cash >= 10000 and self.reputation >= 80:
            print("🏆 Bạn đã xây dựng quán soba nổi tiếng! Có thể tiếp tục chơi.")

    def reports(self):
        if not self.history:
            print("Chưa có ngày kinh doanh nào.")
            return
        print("\nNGÀY | KHÁCH | BÁN | DOANH THU | LÃI/LỖ")
        for row in self.history[-10:]:
            print(f"{row['day']:>4} | {row['visitors']:>5} | "
                  f"{sum(row['sold'].values()):>3} | "
                  f"{row['revenue']:>9,} | {row['profit']:>+8,}")
        print(f"Tổng lãi/lỗ vận hành: "
              f"{money(sum(row['profit'] for row in self.history))}")


def main():
    rng = random.Random()
    game = Game.load()
    print("🍜 QUÁN SOBA — xây quán đạt 10.000 xu và 80 danh tiếng!")
    print("Mỗi ngày hãy chuẩn bị kho và giá bán, rồi mở cửa đón khách.")
    while True:
        game.status()
        print("\n1. Mua nguyên liệu  2. Đặt giá  3. Nâng cấp")
        print("4. Quảng cáo (150 xu)  5. Mở cửa  6. Báo cáo")
        print("7. Lưu game  8. Chơi lại từ đầu  0. Thoát")
        choice = ask_int("Bạn chọn: ", 0, 8)
        if choice == 0:
            game.save()
            print("Hẹn gặp lại!")
            return
        if choice == 1:
            game.shop()
        elif choice == 2:
            game.set_prices()
        elif choice == 3:
            game.improve()
        elif choice == 4:
            game.advertise()
        elif choice == 5:
            game.service(rng)
        elif choice == 6:
            game.reports()
        elif choice == 7:
            game.save()
        elif ask_int("Xóa tiến trình và chơi lại? 1=Có, 0=Không: ", 0, 1):
            game = Game()
            game.save()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nĐã thoát trò chơi.")
