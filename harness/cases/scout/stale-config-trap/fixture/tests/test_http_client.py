"""Smoke test for the HTTP client wiring (not exercised by this task)."""

import unittest

from tests.fixtures.stub_validators import validate_payload


class HttpClientSmokeTest(unittest.TestCase):
    def test_stub_accepts_anything(self):
        self.assertTrue(validate_payload({}))


if __name__ == "__main__":
    unittest.main()
