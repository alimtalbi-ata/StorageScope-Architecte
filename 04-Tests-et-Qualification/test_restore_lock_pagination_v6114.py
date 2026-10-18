"""StorageScope v6.114 pagination regression tests."""
import importlib.util
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "03-Sources" / "restore_lock_pagination.py"
spec = importlib.util.spec_from_file_location("restore_lock_pagination", SOURCE)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
paginate = module.paginate_diagnostics

class PaginationTests(unittest.TestCase):
    def test_empty(self):
        result = paginate([])
        self.assertEqual((result.total, result.pages, result.rows), (0, 1, ()))
    def test_first_page(self):
        result = paginate([{"id": n} for n in range(205)])
        self.assertEqual(len(result.rows), 100)
        self.assertTrue(result.has_next)
        self.assertFalse(result.has_previous)
    def test_last_page(self):
        result = paginate([{"id": n} for n in range(205)], page=3)
        self.assertEqual([row["id"] for row in result.rows], list(range(200, 205)))
        self.assertFalse(result.has_next)
    def test_invalid_size(self):
        for value in (0, 501, True, "100"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                paginate([], page_size=value)
    def test_invalid_page(self):
        for value in (0, -1, 2, True, 1.2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                paginate([], page=value)
    def test_invalid_row(self):
        with self.assertRaises(TypeError):
            paginate([{"id": 1}, None])
    def test_input_unchanged(self):
        rows = [{"id": 1}, {"id": 2}]
        paginate(rows, page_size=1)
        self.assertEqual(rows, [{"id": 1}, {"id": 2}])

if __name__ == "__main__":
    unittest.main()
