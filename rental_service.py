import csv
import os
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4


# ==========================================
# 1. 기본 설정
# ==========================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

ITEM_FIELDS = [
    "item_id",
    "name",
    "total_quantity",
]

RENTAL_FIELDS = [
    "rental_id",
    "item_id",
    "start_date",
    "end_date",
    "quantity",
    "returned_quantity",
]

RETURN_FIELDS = [
    "return_id",
    "rental_id",
    "returned_at",
    "quantity",
]

DEFAULT_ITEMS = [
    {
        "item_id": "CH-001",
        "name": "의자",
        "total_quantity": 100,
    },
    {
        "item_id": "TB-001",
        "name": "테이블",
        "total_quantity": 30,
    },
    {
        "item_id": "TN-001",
        "name": "천막",
        "total_quantity": 10,
    },
    {
        "item_id": "AU-001",
        "name": "음향장비",
        "total_quantity": 8,
    },
]


class RentalError(Exception):
    """대여 서비스에서 발생하는 오류"""
    pass


# ==========================================
# 2. 날짜 처리
# ==========================================

def to_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise RentalError(
            "날짜는 YYYY-MM-DD 형식으로 입력하세요."
        )


# ==========================================
# 3. CSV 파일 읽기 및 저장
# ==========================================

def file_path(filename):
    return DATA_DIR / filename


def read_csv(filename, fields):
    path = file_path(filename)

    if not path.exists():
        raise RentalError(
            f"{filename} 파일이 존재하지 않습니다."
        )

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            reader = csv.DictReader(f)

            if reader.fieldnames is None:
                raise RentalError(
                    f"{filename} 파일이 비어 있습니다."
                )

            missing = set(fields) - set(reader.fieldnames)

            if missing:
                raise RentalError(
                    f"{filename}에 필요한 컬럼이 없습니다: "
                    f"{', '.join(sorted(missing))}"
                )

            return list(reader)

    except UnicodeError as exc:
        raise RentalError(
            f"{filename}의 인코딩을 확인하세요."
        ) from exc


def write_csv(filename, fields, rows):
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = file_path(filename)

    temp = file_path(
        f".{filename}.{uuid4().hex}.tmp"
    )

    try:
        with temp.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fields,
                extrasaction="ignore",
            )

            writer.writeheader()
            writer.writerows(rows)

        os.replace(temp, target)

    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def data_lock():
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_path = file_path(".write.lock")
    start_time = time.monotonic()

    while True:
        try:
            fd = os.open(
                lock_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            os.close(fd)
            break

        except FileExistsError:
            if time.monotonic() - start_time > 10:
                raise RentalError(
                    "다른 작업이 데이터를 수정 중입니다. "
                    "잠시 후 다시 시도하세요."
                )

            time.sleep(0.05)

    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


# ==========================================
# 4. 초기 데이터 생성
# ==========================================

def init_data():
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    initial_files = [
        (
            "items.csv",
            ITEM_FIELDS,
            DEFAULT_ITEMS,
        ),
        (
            "rentals.csv",
            RENTAL_FIELDS,
            [],
        ),
        (
            "returns.csv",
            RETURN_FIELDS,
            [],
        ),
    ]

    for filename, fields, rows in initial_files:
        if not file_path(filename).exists():
            write_csv(
                filename,
                fields,
                rows,
            )


# ==========================================
# 5. 물품 및 대여 데이터 불러오기
# ==========================================

def items():
    init_data()

    rows = read_csv(
        "items.csv",
        ITEM_FIELDS,
    )

    for row in rows:
        row["total_quantity"] = int(
            row["total_quantity"]
        )

        if row["total_quantity"] < 0:
            raise RentalError(
                "보유 수량은 음수일 수 없습니다."
            )

    return rows


def rentals():
    init_data()

    rows = read_csv(
        "rentals.csv",
        RENTAL_FIELDS,
    )

    for row in rows:
        row["quantity"] = int(
            row["quantity"]
        )

        row["returned_quantity"] = int(
            row["returned_quantity"]
        )

        if (
            row["quantity"] < 1
            or row["returned_quantity"] < 0
            or row["returned_quantity"] > row["quantity"]
        ):
            raise RentalError(
                "대여 데이터의 수량이 올바르지 않습니다."
            )

    return rows


def returns():
    init_data()

    rows = read_csv(
        "returns.csv",
        RETURN_FIELDS,
    )

    for row in rows:
        row["quantity"] = int(
            row["quantity"]
        )

    return rows


# ==========================================
# 6. 날짜별 미반납 수량 계산
# ==========================================

def outstanding_on(
    rental,
    selected_date,
    return_events,
):
    selected_date = to_date(selected_date)

    start = to_date(
        rental["start_date"]
    )

    # 대여 시작일 이전에는 점유하지 않음
    if selected_date < start:
        return 0

    returned = 0

    for event in return_events:
        if event["rental_id"] != rental["rental_id"]:
            continue

        returned_date = to_date(
            event["returned_at"]
        )

        if returned_date <= selected_date:
            returned += int(
                event["quantity"]
            )

    remaining = (
        int(rental["quantity"]) - returned
    )

    return max(0, remaining)


# ==========================================
# 7. F-01 대여 가능 수량 조회
# ==========================================

def stock_on(selected_date):
    selected_date = to_date(selected_date)

    item_list = items()
    rental_list = rentals()
    return_list = returns()

    result = []

    for item in item_list:
        item_id = item["item_id"]
        total = item["total_quantity"]

        occupied = 0

        for rental in rental_list:
            if rental["item_id"] != item_id:
                continue

            occupied += outstanding_on(
                rental,
                selected_date,
                return_list,
            )

        available = max(
            0,
            total - occupied,
        )

        result.append({
            "물품 ID": item_id,
            "물품명": item["name"],
            "보유 수량": total,
            "대여 중 수량": occupied,
            "대여 가능 수량": available,
            "상태": (
                "대여 가능"
                if available > 0
                else "대여 불가"
            ),
        })

    return result


# ==========================================
# 8. 기간 전체의 최소 재고 조회
# ==========================================

def min_available(
    item_id,
    start_date,
    end_date,
):
    start_date = to_date(start_date)
    end_date = to_date(end_date)

    if end_date < start_date:
        raise RentalError(
            "반납 예정일이 대여 시작일보다 빠릅니다."
        )

    # 실제 점유 수량이 변하는 날짜만 확인
    check_dates = {start_date}

    rental_list = rentals()
    return_list = returns()

    for rental in rental_list:
        if rental["item_id"] != item_id:
            continue

        start = to_date(
            rental["start_date"]
        )

        if start_date <= start <= end_date:
            check_dates.add(start)

    related_ids = {
        rental["rental_id"]
        for rental in rental_list
        if rental["item_id"] == item_id
    }

    for event in return_list:
        if event["rental_id"] not in related_ids:
            continue

        returned_date = to_date(
            event["returned_at"]
        )

        if start_date <= returned_date <= end_date:
            check_dates.add(returned_date)

    minimum = None
    minimum_day = start_date

    for day in sorted(check_dates):
        row = next(
            (
                row
                for row in stock_on(day)
                if row["물품 ID"] == item_id
            ),
            None,
        )

        if row is None:
            raise RentalError(
                "물품 정보를 찾을 수 없습니다."
            )

        available = row["대여 가능 수량"]

        if minimum is None or available < minimum:
            minimum = available
            minimum_day = day

    return minimum, minimum_day


# ==========================================
# 9. F-02 대여 신청
# ==========================================

def create_rental(
    item_id,
    start_date,
    end_date,
    quantity,
):
    start_date = to_date(start_date)
    end_date = to_date(end_date)

    if start_date < date.today():
        raise RentalError(
            "과거 날짜로는 대여를 신청할 수 없습니다."
        )

    if end_date < start_date:
        raise RentalError(
            "반납 예정일은 대여 시작일보다 "
            "빠를 수 없습니다."
        )

    if type(quantity) is not int or quantity < 1:
        raise RentalError(
            "신청 수량은 1 이상의 정수여야 합니다."
        )

    with data_lock():

        item_ids = {
            item["item_id"]
            for item in items()
        }

        if item_id not in item_ids:
            raise RentalError(
                "등록되지 않은 물품입니다."
            )

        available, shortage_day = min_available(
            item_id,
            start_date,
            end_date,
        )

        if quantity > available:
            raise RentalError(
                f"{shortage_day}에 대여 가능한 "
                f"수량은 {available}개입니다. "
                f"신청 수량 {quantity}개가 부족합니다."
            )

        records = rentals()

        used_numbers = []

        for record in records:
            rental_id = record["rental_id"]

            if (
                rental_id.startswith("R-")
                and rental_id[2:].isdigit()
            ):
                used_numbers.append(
                    int(rental_id[2:])
                )

        next_number = (
            max(used_numbers, default=0) + 1
        )

        new_id = f"R-{next_number:04d}"

        records.append({
            "rental_id": new_id,
            "item_id": item_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "quantity": quantity,
            "returned_quantity": 0,
        })

        write_csv(
            "rentals.csv",
            RENTAL_FIELDS,
            records,
        )

    return new_id


# ==========================================
# 10. F-03 반납 수량 등록
# ==========================================

def register_return(
    rental_id,
    quantity,
):
    if type(quantity) is not int or quantity < 1:
        raise RentalError(
            "반납 수량은 1 이상의 정수여야 합니다."
        )

    with data_lock():

        records = rentals()

        target = next(
            (
                rental
                for rental in records
                if rental["rental_id"] == rental_id
            ),
            None,
        )

        if target is None:
            raise RentalError(
                "해당 신청번호를 찾을 수 없습니다."
            )

        if to_date(target["start_date"]) > date.today():
            raise RentalError(
                "대여 시작일 이전에는 반납할 수 없습니다."
            )

        remaining = (
            target["quantity"]
            - target["returned_quantity"]
        )

        if remaining <= 0:
            raise RentalError(
                "이미 반납 완료된 신청입니다."
            )

        if quantity > remaining:
            raise RentalError(
                f"미반납 수량은 {remaining}개입니다. "
                "이를 초과하여 반납할 수 없습니다."
            )

        # 기존 누적 반납 수량 업데이트
        target["returned_quantity"] += quantity

        # 반납 이력 추가
        return_records = returns()

        return_records.append({
            "return_id": uuid4().hex[:12],
            "rental_id": rental_id,
            "returned_at": date.today().isoformat(),
            "quantity": quantity,
        })

        write_csv(
            "returns.csv",
            RETURN_FIELDS,
            return_records,
        )

        write_csv(
            "rentals.csv",
            RENTAL_FIELDS,
            records,
        )

        remaining = (
            target["quantity"]
            - target["returned_quantity"]
        )

        status = (
            "반납완료"
            if remaining == 0
            else "일부반납"
        )

        result = {
            "누적 반납 수량": target["returned_quantity"],
            "미반납 수량": remaining,
            "상태": status,
        }

    return result


# ==========================================
# 11. F-04 대여 현황 조회
# ==========================================

def rental_status_rows():
    item_names = {
        item["item_id"]: item["name"]
        for item in items()
    }

    today = date.today()
    result = []

    for rental in rentals():
        quantity = rental["quantity"]
        returned = rental["returned_quantity"]

        remaining = quantity - returned

        if remaining == 0:
            status = "반납완료"

        elif returned > 0:
            status = "일부반납"

        else:
            status = "대여중"

        end_date = to_date(
            rental["end_date"]
        )

        overdue = (
            end_date < today
            and remaining > 0
        )

        result.append({
            "신청번호": rental["rental_id"],
            "물품 ID": rental["item_id"],
            "물품명": item_names.get(
                rental["item_id"],
                rental["item_id"],
            ),
            "대여일": rental["start_date"],
            "반납 예정일": rental["end_date"],
            "신청 수량": quantity,
            "누적 반납 수량": returned,
            "미반납 수량": remaining,
            "상태": status,
            "기한": (
                "기한 초과"
                if overdue
                else "정상"
            ),
        })

    return result


# ==========================================
# 12. 직접 실행 테스트
# ==========================================

if __name__ == "__main__":
    init_data()

    print("바로대여 서비스 초기화 완료")
    print()

    print("등록된 물품")
    for item in items():
        print(item)

    print()
    print("오늘의 대여 가능 수량")

    for row in stock_on(date.today()):
        print(row)

    print()
    print("대여 서비스 정상 실행")