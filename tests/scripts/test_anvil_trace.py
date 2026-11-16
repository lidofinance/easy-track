import copy
import unittest

from utils.anvil_trace import normalize_trace_memory


class AnvilTraceTests(unittest.TestCase):
    def test_prefixed_memory_decodes_without_changing_bytes_or_stack(self):
        words = ["00" * 31 + "20", "ff" * 32]
        stack = ["0x40", "0x00"]
        response = {"result": {"structLogs": [{"op": "REVERT", "memory": ["0x" + w for w in words], "stack": stack}]}}
        step = normalize_trace_memory(response)["result"]["structLogs"][0]
        self.assertEqual(bytes.fromhex("".join(step["memory"])), b"\x00" * 31 + b"\x20" + b"\xff" * 32)
        self.assertEqual(step["stack"], stack)
        self.assertEqual(step["op"], "REVERT")

    def test_unprefixed_empty_and_absent_memory_are_preserved(self):
        expected = {"result": {"structLogs": [{"memory": ["00" * 32]}, {"memory": []}, {"op": "STOP"}]}}
        self.assertEqual(normalize_trace_memory(copy.deepcopy(expected)), expected)

    def test_errors_and_empty_results_are_preserved(self):
        for response in ({"error": {"message": "unsupported"}}, {"result": None}, {"result": {}}):
            with self.subTest(response=response):
                self.assertIs(normalize_trace_memory(response), response)
