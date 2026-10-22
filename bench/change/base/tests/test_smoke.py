import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Smoke(unittest.TestCase):
    def run_wms(self, db, *args, user="alice"):
        cmd = [sys.executable, "-m", "wms", "--db", db, "--json", "--now", "2026-03-05T10:00:00Z"]
        cmd += ["--user", user] if user else []
        return subprocess.run(cmd + list(args), cwd=ROOT, capture_output=True, text=True)

    def test_receive_and_value(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "wms.db")
            for user, args in [(None, ["init", "--currency", "EUR", "--admin", "alice"]),
                               ("alice", ["warehouse", "add", "WH1", "--name", "Main"]),
                               ("alice", ["location", "add", "WH1/A-01"]),
                               ("alice", ["product", "add", "BOLT", "--name", "Bolt"])]:
                self.assertEqual(self.run_wms(db, *args, user=user).returncode, 0)
            r = self.run_wms(db, "receive", "BOLT", "10", "--at", "WH1/A-01", "--cost", "0.5")
            self.assertEqual(r.returncode, 0, r.stderr)
            v = json.loads(self.run_wms(db, "valuation").stdout)
            self.assertEqual(v["total"], "5.00")


if __name__ == "__main__":
    unittest.main()
