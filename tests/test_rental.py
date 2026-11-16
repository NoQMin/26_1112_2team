import unittest
import tempfile
from pathlib import Path
from datetime import date, timedelta
from unittest.mock import patch
from services import storage
from services.inventory import available_quantity
from services.rental import create_rental
from services.return_service import register_return

class RentalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch = patch.object(storage, "DATA_DIR", Path(self.temp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        storage.write_rows("items.csv", storage.ITEM_FIELDS, [dict(item_id="A", name="Test", category="Test", total=10)])
        self.today = date.today()

    def test_overlap_and_nonoverlap(self):
        d = self.today
        create_rental("A", "User", "Team", 6, d, d)
        create_rental("A", "User", "Team", 6, d+timedelta(days=1), d+timedelta(days=2))
        self.assertEqual(available_quantity("A", d, d+timedelta(days=2)), 4)
        with self.assertRaises(ValueError):
            create_rental("A", "User", "Team", 5, d, d)

    def test_partial_return(self):
        d = self.today
        key = create_rental("A", "User", "Team", 6, d, d)
        self.assertEqual(register_return(key, 2), 4)
        self.assertEqual(available_quantity("A", d, d), 6)
        with self.assertRaises(ValueError): register_return(key, 5)
        self.assertEqual(register_return(key, 4), 0)
        with self.assertRaises(ValueError): register_return(key, 1)

    def test_validation_and_future_return(self):
        d = self.today
        for args in [("A", "", "Team", 1, d, d), ("A", "User", "Team", 0, d, d), ("A", "User", "Team", 1, d, d-timedelta(days=1)), ("missing", "User", "Team", 1, d, d)]:
            with self.assertRaises(ValueError): create_rental(*args)
        key = create_rental("A", "User", "Team", 1, d+timedelta(days=1), d+timedelta(days=2))
        with self.assertRaises(ValueError): register_return(key, 1)

    def test_overdue(self):
        d = self.today
        key = create_rental("A", "User", "Team", 3, d, d)
        rows = storage.read_rows("rentals.csv")
        rows[0]["start_date"] = (d-timedelta(days=2)).isoformat()
        rows[0]["end_date"] = (d-timedelta(days=1)).isoformat()
        storage.write_rows("rentals.csv", storage.RENTAL_FIELDS, rows)
        self.assertEqual(available_quantity("A", d+timedelta(days=20), d+timedelta(days=21)), 7)
        register_return(key, 3)
        self.assertEqual(available_quantity("A", d, d), 10)

if __name__ == "__main__": unittest.main()
