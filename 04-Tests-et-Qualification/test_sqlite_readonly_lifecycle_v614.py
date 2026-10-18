"""Read-only worker resource regression tests. Author: Abdelhalim Talbi."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from async_portfolio import load_portfolio_readonly
from graph_prepare import prepare_graph

class TestReadOnlyLifecycleV614(unittest.TestCase):
    def test_portfolio_invalid_mode_no_database_created(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing.sqlite"
            with self.assertRaises(ValueError):load_portfolio_readonly(p,mode="bad")
            self.assertFalse(p.exists())

    def test_portfolio_missing_database_no_creation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing.sqlite"
            with self.assertRaises(sqlite3.OperationalError):load_portfolio_readonly(p)
            self.assertFalse(p.exists())

    def test_graph_missing_database_no_creation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing.sqlite"
            req=(str(p),"id","TOUS","",(),10,900)
            with self.assertRaises(sqlite3.OperationalError):prepare_graph(req)
            self.assertFalse(p.exists())

    def test_graph_cancelled_before_connect(self):
        with patch('graph_prepare.sqlite3.connect',side_effect=AssertionError('connected')):
            with self.assertRaises(Exception) as exc:
                prepare_graph(('none','id','TOUS','',(),10,900),cancel_check=lambda:True)
            self.assertEqual(type(exc.exception).__name__,'RouteCancelled')

if __name__=='__main__':unittest.main()
