"""Artifact-loader regressions; run with unittest without Brownie or a fork."""

import tempfile
import unittest
from pathlib import Path

from utils.lido_lend_artifacts import load_lido_lend_artifacts


class TestLidoLendArtifacts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.protocol = '''[artifact]
kind = "protocol-deployment"
deployment = "test"
chain_id = 1
config_hash = "test-hash"
[protocol]
deployment = "test"
network = "mainnet"
chain_id = 1
config_hash = "test-hash"
core = "0x0000000000000000000000000000000000000001"
owner_facade = "0x0000000000000000000000000000000000000002"
irm_router = "0x0000000000000000000000000000000000000003"
adaptive_curve_irm = "0x0000000000000000000000000000000000000004"
factory = "0x0000000000000000000000000000000000000005"
risk_steward_dashboard = "0x0000000000000000000000000000000000000006"
circuit_breaker = "0x0000000000000000000000000000000000000007"
agent = "0x0000000000000000000000000000000000000008"
evm_script_executor = "0x0000000000000000000000000000000000000009"
'''
        (self.root / 'protocol.toml').write_text(self.protocol)
        self.exit_books = '''[artifact]
kind = "exit-books-deployment"
deployment = "test"
chain_id = 1
config_hash = "test-hash"
[exit_books]
morpho = "0x0000000000000000000000000000000000000010"
erc4626 = "0x0000000000000000000000000000000000000011"
'''

    def test_default_still_requires_markets(self):
        with self.assertRaisesRegex(ValueError, 'deployment has no market artifacts'):
            load_lido_lend_artifacts(self.root)

    def test_protocol_only_mode_accepts_missing_markets_directory(self):
        result = load_lido_lend_artifacts(self.root, require_markets=False)
        self.assertEqual(result['markets'], {})
        self.assertEqual(result['protocol']['protocol']['core'], '0x0000000000000000000000000000000000000001')

    def test_protocol_only_mode_accepts_empty_markets_directory(self):
        (self.root / 'markets').mkdir()
        self.assertEqual(load_lido_lend_artifacts(self.root, require_markets=False)['markets'], {})

    def test_positional_exit_books_argument_is_preserved(self):
        (self.root / 'exit-books.toml').write_text(self.exit_books)
        result = load_lido_lend_artifacts(self.root, True, require_markets=False)
        self.assertEqual(result['exit_books']['exit_books']['morpho'], '0x0000000000000000000000000000000000000010')

    def test_protocol_only_mode_still_requires_requested_exit_books(self):
        with self.assertRaisesRegex(ValueError, 'exit books artifact does not exist'):
            load_lido_lend_artifacts(self.root, require_exit_books=True, require_markets=False)

    def test_protocol_metadata_mismatch_is_rejected(self):
        (self.root / 'protocol.toml').write_text(self.protocol.replace('chain_id = 1', 'chain_id = 2', 1))
        with self.assertRaisesRegex(ValueError, 'protocol and artifact metadata disagree on chain_id'):
            load_lido_lend_artifacts(self.root, require_markets=False)

    def test_exit_books_from_another_deployment_are_rejected(self):
        (self.root / 'exit-books.toml').write_text(self.exit_books.replace('deployment = "test"', 'deployment = "other"'))
        with self.assertRaisesRegex(ValueError, 'belongs to a different deployment'):
            load_lido_lend_artifacts(self.root, require_markets=False)

    def test_present_malformed_market_is_rejected_in_both_modes(self):
        (self.root / 'markets').mkdir()
        (self.root / 'markets/broken.toml').write_text('[artifact]\nkind = "wrong"\n')
        for require_markets in (False, True):
            with self.subTest(require_markets=require_markets):
                with self.assertRaisesRegex(ValueError, 'not a market-deployment artifact'):
                    load_lido_lend_artifacts(self.root, require_markets=require_markets)


if __name__ == '__main__':
    unittest.main()
