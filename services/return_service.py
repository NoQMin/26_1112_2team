"""누적 부분 반납 처리."""
from datetime import date
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
        write_rows("rentals.csv", RENTAL_FIELDS, rows)
        return remaining - quantity
