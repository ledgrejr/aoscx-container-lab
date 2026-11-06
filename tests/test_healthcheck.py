import contextlib
import io
import json
import unittest

import healthcheck


class HealthcheckTests(unittest.TestCase):
    def test_report_contains_only_local_health_metadata(self):
        report = healthcheck.health_report()

        self.assertEqual(report["application"], "aoscx-container-healthcheck")
        self.assertEqual(report["status"], "healthy")
        self.assertEqual(report["checks"], {"process": "ok"})
        self.assertEqual(report["version"], "0.1.0")
        self.assertEqual(set(report), {"application", "checks", "status", "version"})

    def test_check_emits_one_json_line_and_exits(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = healthcheck.main(["--check"])

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "healthy")
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_nonpositive_interval_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            healthcheck.main(["--interval", "0"])

        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()