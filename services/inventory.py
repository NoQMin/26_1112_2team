"""기간별 최대 동시 대여 수량 계산."""
from datetime import date, timedelta
from services.storage import read_rows

def get_items():
    return read_rows("items.csv")

def validate_period(start, end):
    if start > end:
        raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")

def available_quantity(item_id, start, end, rentals=None):
    validate_period(start, end)
    item = next((row for row in get_items() if row["item_id"] == item_id), None)
    if item is None:
        raise ValueError("존재하지 않는 물품입니다.")
    events = {}
    for row in read_rows("rentals.csv") if rentals is None else rentals:
        remaining = int(row["quantity"]) - int(row["returned"])
        if row["item_id"] != item_id or remaining <= 0:
            continue
        first = date.fromisoformat(row["start_date"])
        last = date.fromisoformat(row["end_date"])
        if last < date.today():
            last = date.max
        left, right = max(start, first), min(end, last)
        if left <= right:
            events[left] = events.get(left, 0) + remaining
            if right < date.max:
                after = right + timedelta(days=1)
                events[after] = events.get(after, 0) - remaining
    current = peak = 0
    for day in sorted(events):
        current += events[day]
        peak = max(peak, current)
    return max(0, int(item["total"]) - peak)
