"""CSV 파일 저장 및 쓰기 잠금."""
import csv
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
import msvcrt

DATA_DIR = Path(os.environ.get("RENTAL_DATA_DIR", Path(__file__).resolve().parents[1] / "data"))
ITEM_FIELDS = ["item_id", "name", "category", "total"]
RENTAL_FIELDS = ["rental_id", "item_id", "borrower", "department", "quantity", "start_date", "end_date", "returned", "created_at"]

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
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def write_rows(name, fields, rows):
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
