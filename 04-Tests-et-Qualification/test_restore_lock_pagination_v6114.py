"""StorageScope v6.114 pagination regression tests (stdlib only)."""
import importlib.util
import pathlib
import sys
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "03-Sources" / "restore_lock_pagination.py"
spec = importlib.util.spec_from_file_location("restore_lock_pagination", SOURCE)
module = importlib.util.module_from_spec(spec)
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
    def test_invalid_row_on_selected_page(self):
        with self.assertRaises(TypeError):
            paginate([{"id": 1}, None])
    def test_input_unchanged(self):
        rows = [{"id": 1}, {"id": 2}]
        paginate(rows, page_size=1)
        self.assertEqual(rows, [{"id": 1}, {"id": 2}])
    def test_generator(self):
        result = paginate(({"id": i} for i in range(12)), page=2, page_size=5)
        self.assertEqual([r["id"] for r in result.rows], list(range(5, 10)))
    def test_reject_mapping_as_collection(self):
        with self.assertRaises(TypeError):
            paginate({"id": 1})
    def test_large_sequence_reads_only_one_page(self):
        class LargeSequence:
            def __len__(self):
                return 1000000
            def __getitem__(self, key):
                if not isinstance(key, slice):
                    raise AssertionError("must only slice selected page")
                return [{"id": i} for i in range(*key.indices(len(self)))]
        from collections.abc import Sequence
        class Instrumented(LargeSequence, Sequence):
            pass
        result = paginate(Instrumented(), page=9000, page_size=100)
        self.assertEqual((len(result.rows), result.rows[0]["id"]), (100, 899900))
    def test_page_out_of_bounds(self):
        with self.assertRaises(ValueError):
            paginate([{"id": 1}], page=2)

if __name__ == "__main__":
    unittest.main()
