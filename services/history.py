"""대여 현황과 상태 계산."""
from datetime import date
from services.inventory import get_items
from services.storage import read_rows

def get_history():
    names = {r["item_id"]: r["name"] for r in get_items()}
    result = []
    for row in reversed(read_rows("rentals.csv")):
        remaining = int(row["quantity"]) - int(row["returned"])
        status = "반납 완료" if remaining == 0 else "연체" if row["end_date"] < date.today().isoformat() else "예약" if row["start_date"] > date.today().isoformat() else "대여 중"
        result.append({"대여번호": row["rental_id"], "물품": names.get(row["item_id"], row["item_id"]), "신청자": row["borrower"], "소속": row["department"], "시작일": row["start_date"], "종료일": row["end_date"], "대여 수량": int(row["quantity"]), "반납 수량": int(row["returned"]), "미반납 수량": remaining, "상태": status})
    return result
