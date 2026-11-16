"""CSV 파일 저장 및 쓰기 잠금."""
import csv
import json
import os
import tempfile
from datetime import date, datetime
from contextlib import contextmanager
from pathlib import Path
import msvcrt

DATA_DIR = Path(os.environ.get("RENTAL_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
ITEM_FIELDS = ["item_id", "name", "category", "total"]
RENTAL_FIELDS = ["rental_id", "item_id", "borrower", "department", "quantity", "start_date", "end_date", "returned", "created_at", "return_events"]


class DataError(ValueError):
    """화면에서 안내할 수 있는 CSV 검증 오류."""


def _invalid(name, line, column, detail):
    return DataError(f"{name} {line}행 '{column}' 값을 확인해 주세요. {detail}")


def _integer(name, line, column, value, minimum=0):
    try:
        # bool, 소수 및 공백 값은 정수 수량으로 인정하지 않는다.
        if isinstance(value, bool):
            raise ValueError
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise _invalid(name, line, column, "정수를 입력해야 합니다.") from exc
    if number < minimum:
        raise _invalid(name, line, column, f"{minimum} 이상의 정수를 입력해야 합니다.")
    return number


def _validate(name, fields, rows):
    schema = ITEM_FIELDS if name == "items.csv" else RENTAL_FIELDS if name == "rentals.csv" else None
    if schema is None:
        return rows
    required = set(schema) - {"return_events"}
    missing = required - set(fields or [])
    if missing:
        raise DataError(f"{name} 필수 컬럼이 없습니다: {', '.join(sorted(missing))}")
    if len(fields) != len(set(fields)):
        raise DataError(f"{name}에 중복된 컬럼이 있습니다.")
    seen = set()
    for line, row in enumerate(rows, start=2):
        if None in row or any(row.get(key) is None for key in required):
            raise DataError(f"{name} {line}행의 컬럼 수가 헤더와 다릅니다.")
        id_field = "item_id" if name == "items.csv" else "rental_id"
        identifier = str(row[id_field]).strip()
        if not identifier or identifier in seen:
            raise _invalid(name, line, id_field, "ID는 비어 있지 않아야 하며 중복될 수 없습니다.")
        seen.add(identifier)
        if name == "items.csv":
            for key in ("name", "category"):
                if not str(row[key]).strip():
                    raise _invalid(name, line, key, "빈 값을 입력할 수 없습니다.")
            _integer(name, line, "total", row["total"])
        else:
            quantity = _integer(name, line, "quantity", row["quantity"], 1)
            returned = _integer(name, line, "returned", row["returned"])
            if returned > quantity:
                raise _invalid(name, line, "returned", "대여 수량을 초과할 수 없습니다.")
            for key in ("start_date", "end_date"):
                try:
                    date.fromisoformat(row[key])
                except (ValueError, TypeError) as exc:
                    raise _invalid(name, line, key, "YYYY-MM-DD 형식의 날짜를 입력해야 합니다.") from exc
            if row["start_date"] > row["end_date"]:
                raise _invalid(name, line, "end_date", "시작일보다 빠를 수 없습니다.")
            # 기존 10개 컬럼 CSV도 읽는다. 다음 성공한 쓰기 때 새 컬럼을 추가한다.
            raw_events = row.get("return_events") or "[]"
            try:
                events = json.loads(raw_events)
                if not isinstance(events, list):
                    raise ValueError
                event_ids = set()
                event_total = 0
                for event in events:
                    if not isinstance(event, dict) or not isinstance(event.get("return_id"), str) or not event["return_id"] or event["return_id"] in event_ids:
                        raise ValueError
                    event_ids.add(event["return_id"])
                    if type(event.get("quantity")) is not int or event["quantity"] <= 0:
                        raise ValueError
                    timestamp = datetime.fromisoformat(event["returned_at"])
                    if timestamp.tzinfo is None:
                        raise ValueError
                    event_total += event["quantity"]
                if event_total > returned:
                    raise ValueError
            except (ValueError, TypeError, KeyError) as exc:
                raise _invalid(name, line, "return_events", "반납 이력 형식과 누적 반납 수량을 확인해 주세요.") from exc
            row["return_events"] = raw_events
    return rows

@contextmanager
def transaction():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / ".write.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

def read_rows(name):
    path = DATA_DIR / name
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            return _validate(name, reader.fieldnames, rows)
    except (UnicodeError, csv.Error) as exc:
        raise DataError(f"{name}을 읽을 수 없습니다. CSV 형식과 UTF-8 인코딩을 확인해 주세요.") from exc

def write_rows(name, fields, rows):
    rows = _validate(name, fields, [dict(row) for row in rows])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, DATA_DIR / name)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
