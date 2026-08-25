import pytest
from brownie import LidoLendExitBookActions
from eth_abi import encode
from utils.lido_lend import MARKET_PARAMS_ABI_TYPE


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def test_set_market_exit_book_allowed_scenario(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    enact_motion,
    admin,
    activate_market,
    register_factory,
):
    "Allow-list a freshly-activated market independently on both exit books."
    m = lido_lend.market
    market_id = m["id"]

    def unavailable(message):
        if lido_lend.local:
            pytest.skip(message)
        raise pytest.UsageError(message)

    if not lido_lend.has("morphoExitBook") or not lido_lend.has("erc4626ExitBook"):
        unavailable("deployment has no exit books")

    morpho = lido_lend.contract("morphoExitBook")
    erc4626 = lido_lend.contract("erc4626ExitBook")

    activate_market(check_exit_books=True)
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    executor = easy_track.evmScriptExecutor()
    morpho.grantRole(morpho.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})
    erc4626.grantRole(erc4626.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})

    exit_book_factory = deployer.deploy(LidoLendExitBookActions, trusted_caller)
    register_factory(
        exit_book_factory,
        "0x"
        + morpho.address[2:]
        + morpho.setMarketAllowed.signature[2:]
        + erc4626.address[2:]
        + erc4626.setVaultAllowed.signature[2:],
    )

    def morpho_calldata(allowed):
        payload = encode(
            ["address", f"{MARKET_PARAMS_ABI_TYPE}[]", "bool"],
            [morpho.address, [_market_params(lido_lend)], allowed],
        )
        return "0x" + encode(["uint8", "bytes"], [0, payload]).hex()

    def erc4626_calldata(allowed):
        payload = encode(["address", "address[]", "bool"], [erc4626.address, [m["vault"]], allowed])
        return "0x" + encode(["uint8", "bytes"], [1, payload]).hex()

    enact_motion(easy_track, exit_book_factory, morpho_calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, exit_book_factory, erc4626_calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, exit_book_factory, morpho_calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, exit_book_factory, erc4626_calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])
