#!/usr/bin/env python3
"""Regression test for the unterminated-asciiz infinite loop.

Uses only the standard library, so it runs with `python -m unittest` and
needs no test dependencies:

    python -m unittest discover tests
"""

import io
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import py3d


class ReadAsciizTest(unittest.TestCase):

    def test_unterminated_string_raises_instead_of_hanging(self):
        """A string with no NUL before EOF must raise, not spin forever.

        Guarded by a timeout: before the fix `_read_asciiz` never returned,
        so without this the test would hang the whole suite instead of
        failing.
        """
        result = {}

        def call():
            try:
                py3d._read_asciiz(io.BytesIO(b"no NUL before EOF"))
                result["outcome"] = "returned"
            except Exception as exc:
                result["outcome"] = type(exc).__name__

        worker = threading.Thread(target=call, daemon=True)
        worker.start()
        worker.join(5.0)

        self.assertFalse(
            worker.is_alive(),
            "_read_asciiz did not return after 5s: the read loop never "
            "terminates when f.read() keeps returning b'' at EOF")
        self.assertEqual(result.get("outcome"), "ValueError")

    def test_terminated_strings_are_unaffected(self):
        self.assertEqual(py3d._read_asciiz(io.BytesIO(b"hello\0rest")),
                         "hello")
        self.assertEqual(py3d._read_asciiz(io.BytesIO(b"\0")), "")

    def test_string_longer_than_one_read_block(self):
        """Crossing the 1024-byte block boundary still works."""
        payload = b"x" * 3000 + b"\0"
        self.assertEqual(py3d._read_asciiz(io.BytesIO(payload)), "x" * 3000)

    def test_stream_is_positioned_after_the_terminator(self):
        stream = io.BytesIO(b"abc\0tail")
        py3d._read_asciiz(stream)
        self.assertEqual(stream.read(), b"tail")


if __name__ == "__main__":
    unittest.main()
