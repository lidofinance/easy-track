import tempfile
import unittest
from pathlib import Path

from eth_abi import encode
from web3 import Web3

from utils.lido_lend_artifacts import load_lido_lend_artifacts


class TestLidoLendArtifacts(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.protocol = """[artifact]
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
"""
        (self.root / "protocol.toml").write_text(self.protocol)
        self.exit_books = """[artifact]
kind = "exit-books-deployment"
deployment = "test"
chain_id = 1
config_hash = "test-hash"
[exit_books]
morpho = "0x0000000000000000000000000000000000000010"
erc4626 = "0x0000000000000000000000000000000000000011"
"""

    def test_default_still_requires_markets(self):
        with self.assertRaisesRegex(ValueError, "deployment has no market artifacts"):
            load_lido_lend_artifacts(self.root)

    def test_protocol_only_mode_accepts_missing_markets_directory(self):
        result = load_lido_lend_artifacts(self.root, require_markets=False)
        self.assertEqual(result["markets"], {})
        self.assertEqual(result["protocol"]["protocol"]["core"], "0x0000000000000000000000000000000000000001")

    def test_protocol_only_mode_accepts_empty_markets_directory(self):
        (self.root / "markets").mkdir()
        self.assertEqual(load_lido_lend_artifacts(self.root, require_markets=False)["markets"], {})

    def test_positional_exit_books_argument_is_preserved(self):
        (self.root / "exit-books.toml").write_text(self.exit_books)
        result = load_lido_lend_artifacts(self.root, True, require_markets=False)
        self.assertEqual(result["exit_books"]["exit_books"]["morpho"], "0x0000000000000000000000000000000000000010")

    def test_protocol_only_mode_still_requires_requested_exit_books(self):
        with self.assertRaisesRegex(ValueError, "exit books artifact does not exist"):
            load_lido_lend_artifacts(self.root, require_exit_books=True, require_markets=False)

    def test_protocol_metadata_mismatch_is_rejected(self):
        (self.root / "protocol.toml").write_text(self.protocol.replace("chain_id = 1", "chain_id = 2", 1))
        with self.assertRaisesRegex(ValueError, "protocol and artifact metadata disagree on chain_id"):
            load_lido_lend_artifacts(self.root, require_markets=False)

    def test_exit_books_from_another_deployment_are_rejected(self):
        (self.root / "exit-books.toml").write_text(
            self.exit_books.replace('deployment = "test"', 'deployment = "other"')
        )
        with self.assertRaisesRegex(ValueError, "belongs to a different deployment"):
            load_lido_lend_artifacts(self.root, require_markets=False)

    def test_resources_from_later_deployment_steps_can_have_different_config_hashes(self):
        (self.root / "protocol.toml").write_text(
            self.protocol.replace('config_hash = "test-hash"', 'config_hash = "protocol-body-hash"', 1)
        )
        (self.root / "exit-books.toml").write_text(self.exit_books.replace("test-hash", "replacement-books-hash"))
        result = load_lido_lend_artifacts(self.root, require_exit_books=True, require_markets=False)
        self.assertEqual(result["exit_books"]["artifact"]["config_hash"], "replacement-books-hash")

    def test_config_hash_is_not_required_to_identify_a_deployment(self):
        (self.root / "protocol.toml").write_text(self.protocol.replace('config_hash = "test-hash"\n', ""))
        load_lido_lend_artifacts(self.root, require_markets=False)

    def test_compatibility_hash_matches_across_resources_when_present(self):
        (self.root / "protocol.toml").write_text(
            self.protocol.replace("[artifact]", '[artifact]\ncompatibility_hash = "protocol-version"')
        )
        for compatibility in ("protocol-version", "other-version", None):
            with self.subTest(compatibility=compatibility):
                books = self.exit_books.replace("test-hash", "later-step-hash")
                if compatibility is not None:
                    books = books.replace("[artifact]", f'[artifact]\ncompatibility_hash = "{compatibility}"')
                (self.root / "exit-books.toml").write_text(books)
                if compatibility == "protocol-version":
                    load_lido_lend_artifacts(self.root, require_exit_books=True, require_markets=False)
                else:
                    with self.assertRaisesRegex(ValueError, "different compatibility_hash"):
                        load_lido_lend_artifacts(self.root, require_exit_books=True, require_markets=False)

    def test_present_malformed_market_is_rejected_in_both_modes(self):
        (self.root / "markets").mkdir()
        (self.root / "markets/broken.toml").write_text('[artifact]\nkind = "wrong"\n')
        for require_markets in (False, True):
            with self.subTest(require_markets=require_markets):
                with self.assertRaisesRegex(ValueError, "not a market-deployment artifact"):
                    load_lido_lend_artifacts(self.root, require_markets=require_markets)

    def _write_typed_market(self):
        loan, collateral, oracle, irm = [f"0x{n:040x}" for n in (11, 12, 13, 3)]
        market_id = Web3.keccak(
            encode(["(address,address,address,address,uint256)"], [(loan, collateral, oracle, irm, 950000000000000000)])
        ).hex()
        text = f"""core = "0x0000000000000000000000000000000000000001"
role = "weth-wsteth"
[header]
version = 1
kind = "market"
run = "test"
chainId = 1
name = "weth-wsteth"
[plan]
name = "weth-wsteth"
[plan.market]
loanToken = "{loan}"
collateralToken = "{collateral}"
oracle = "{oracle}"
guardianSignals = "0x000000000000000000000000000000000000000f"
lltv = 950000000000000000
[plan.curve]
curveSteepness = 4000000000000000000
adjustmentSpeed = 1585489599188
targetUtilization = 900000000000000000
initialRateAtTarget = 713470319
minRateAtTarget = 31709791
maxRateAtTarget = 1585489599
maxBorrowRate = 1585489599
[addresses]
id = "{market_id}"
controller = "0x000000000000000000000000000000000000000d"
vault = "0x000000000000000000000000000000000000000e"
guardianSignals = "0x000000000000000000000000000000000000000f"
irmConfig = "0x0000000000000000000000000000000000000010"
[addresses.params]
loanToken = "{loan}"
collateralToken = "{collateral}"
oracle = "{oracle}"
irm = "{irm}"
lltv = 950000000000000000
"""
        directory = self.root / "markets"
        directory.mkdir(exist_ok=True)
        path = directory / "weth-wsteth.toml"
        path.write_text(text)
        return path, text

    def test_typed_market_binds_to_historical_protocol(self):
        self._write_typed_market()
        market = load_lido_lend_artifacts(self.root)["markets"]["weth-wsteth"]
        self.assertEqual(market["market"]["lltv"], 950000000000000000)
        self.assertEqual(market["curve"]["initial_rate_at_target"], 713470319)

    def test_typed_market_identity_mismatch_is_rejected(self):
        path, text = self._write_typed_market()
        for old, new, reason in (
            ("version = 1", "version = 2", "unsupported typed"),
            ('kind = "market"', 'kind = "protocol"', "unsupported typed"),
            ('run = "test"', 'run = "other"', "different deployment"),
            ("chainId = 1", "chainId = 2", "different deployment or chain"),
            (
                'core = "0x0000000000000000000000000000000000000001"',
                'core = "0x0000000000000000000000000000000000000002"',
                "core does not match",
            ),
            ('name = "weth-wsteth"', 'name = "other"', "name does not match"),
            ("lltv = 950000000000000000", "lltv = 940000000000000000", "lltv differs"),
        ):
            with self.subTest(field=old):
                path.write_text(text.replace(old, new, 1))
                with self.assertRaisesRegex(ValueError, reason):
                    load_lido_lend_artifacts(self.root)

    def test_typed_market_id_mismatch_is_rejected(self):
        path, text = self._write_typed_market()
        path.write_text(text.replace('id = "0x', 'id = "0x00', 1))
        with self.assertRaisesRegex(ValueError, "artifact id does not match"):
            load_lido_lend_artifacts(self.root)


if __name__ == "__main__":
    unittest.main()
