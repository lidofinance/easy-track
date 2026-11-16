import os
import subprocess
from pathlib import Path

import pytest
from brownie import LidoLendExitBookActions, web3
from eth_abi import encode

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE


def test_lending_integrations_after_easy_track_activation(
    lido_lend, activate_market, easy_track, deployer, trusted_caller, register_factory, permission, enact_motion
):
    directory = os.environ.get("LENDING_DIR")
    if not directory:
        pytest.skip("set LENDING_DIR to run the lending integration suite")
    assert not lido_lend.local, "Lending regression requires deployment artifacts"
    lending = Path(directory).resolve()
    artifacts = Path(os.environ["LIDO_LEND_ARTIFACTS_DIR"]).resolve()
    assert artifacts.parent == lending / "deployed", "Artifact path must belong to the lending checkout"
    assert any(market["name"] == "weth-wsteth" for market in lido_lend.markets), "Missing lending suite market"
    activate_market(enable_settlement=True, fee=0)
    assert lido_lend.contract("core").market(lido_lend.market["id"])["lastUpdate"] != 0

    market = lido_lend.market
    morpho_book = lido_lend.contract("morphoExitBook")
    vault_book = lido_lend.contract("erc4626ExitBook")
    factory = deployer.deploy(LidoLendExitBookActions, trusted_caller, morpho_book, vault_book)
    register_factory(
        factory, permission((morpho_book, morpho_book.setMarketAllowed), (vault_book, vault_book.setVaultAllowed))
    )
    params = (market["loanToken"], market["collateralToken"], market["oracle"], market["irm"], market["lltv"])
    payloads = (
        encode([f"{MARKET_PARAMS_ABI_TYPE}[]", "bool"], [[params], True]),
        encode(["address[]", "bool"], [[market["vault"]], True]),
    )
    for action, payload in enumerate(payloads):
        calldata = "0x" + encode(["uint8", "bytes"], [action, payload]).hex()
        enact_motion(easy_track, factory, calldata, trusted_caller)
    assert morpho_book.isMarketAllowed(market["id"])
    assert vault_book.isVaultAllowed(market["vault"])

    reports = Path(os.environ.get("REPORT_DIR", "reports/lido-lend")).resolve()
    reports.mkdir(parents=True, exist_ok=True)
    report = reports / f"lending-{lido_lend.market['name']}.log"
    block_hash = web3.eth.get_block("latest")["hash"]
    with report.open("w") as output:
        result = subprocess.run(
            [
                "make",
                "test-fork",
                f"RUN={artifacts.name}",
                "PREPARE=true",
                f"RPC_URL={web3.provider.endpoint_uri}",
                "FORK_BLOCK=",
                "TEST_SEED=1",
            ],
            cwd=lending,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=1800,
        )
    assert result.returncode == 0, report.read_text()[-12000:]
    assert web3.eth.get_block("latest")["hash"] == block_hash, "Lending tests changed the caller's node"
