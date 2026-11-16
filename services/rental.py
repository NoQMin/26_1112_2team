"""대여 신청 검증 및 저장."""
from datetime import date, datetime
from uuid import uuid4
from services.inventory import available_quantity, validate_period
from services.storage import transaction, read_rows, write_rows, RENTAL_FIELDS

def create_rental(item_id, borrower, department, quantity, start, end):
    validate_period(start, end)
    if start < date.today():
        raise ValueError('대여 시작일은 오늘 이후로 선택해 주세요.')
    if not borrower.strip() or not department.strip():
        raise ValueError('신청자 이름과 소속을 모두 입력해 주세요.')
    if len(borrower.strip()) > 50 or len(department.strip()) > 100:
        raise ValueError('이름은 50자, 소속은 100자 이하로 입력해 주세요.')
    if type(quantity) is not int or quantity <= 0:
        raise ValueError('대여 수량은 1 이상의 정수여야 합니다.')
    with transaction():
        rows = read_rows("rentals.csv")
        available = available_quantity(item_id, start, end, rows)
        if quantity > available:
            raise ValueError(f"선택 기간 대여 가능 수량: {available}개")
        row = dict(rental_id=uuid4().hex[:12], item_id=item_id, borrower=borrower.strip(), department=department.strip(), quantity=quantity, start_date=start.isoformat(), end_date=end.isoformat(), returned=0, created_at=datetime.now().isoformat(timespec="seconds"), return_events="[]")
        rows.append(row)
        write_rows("rentals.csv", RENTAL_FIELDS, rows)
    return row["rental_id"]
