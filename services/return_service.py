"""누적 부분 반납 처리."""
import json
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
from services.storage import transaction, read_rows, write_rows, RENTAL_FIELDS

def register_return(rental_id, quantity):
    if type(quantity) is not int or quantity <= 0:
        raise ValueError('반납 수량은 1 이상의 정수여야 합니다.')
    with transaction():
        rows = read_rows("rentals.csv")
        row = next((r for r in rows if r["rental_id"] == rental_id), None)
        if row is None:
            raise ValueError('대여 내역을 찾을 수 없습니다.')
        if date.fromisoformat(row["start_date"]) > date.today():
            raise ValueError('대여 시작일 이전에는 반납할 수 없습니다.')
        remaining = int(row["quantity"]) - int(row["returned"])
        if quantity > remaining:
            raise ValueError('미반납 수량을 초과했습니다.')
        row["returned"] = int(row["returned"]) + quantity
        events = json.loads(row.get("return_events") or "[]")
        events.append({
            "return_id": uuid4().hex,
            "quantity": quantity,
            "returned_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
        })
        row["return_events"] = json.dumps(events, ensure_ascii=False)
        # 누적 수량과 이력을 같은 CSV의 원자적 교체로 함께 확정한다.
        write_rows("rentals.csv", RENTAL_FIELDS, rows)
        return remaining - quantity


def get_return_history(rental_id):
    """기록을 시작한 이후의 반납 건을 시간순으로 반환한다."""
    row = next((r for r in read_rows("rentals.csv") if r["rental_id"] == rental_id), None)
    if row is None:
        raise ValueError("대여 내역을 찾을 수 없습니다.")
    events = json.loads(row.get("return_events") or "[]")
    return [
        {"반납번호": event["return_id"], "반납 수량": event["quantity"], "반납 일시": event["returned_at"]}
        for event in events
    ]
