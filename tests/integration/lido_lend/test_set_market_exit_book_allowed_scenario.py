import pytest
from brownie import (
    AdaptiveCurveConfigStub,
    LidoLendActivateMarket,
    LidoLendSetErc4626ExitBookAllowed,
    LidoLendSetMorphoExitBookAllowed,
    web3,
)
from eth_abi import encode
from utils.lido_lend import MARKET_PARAMS_ABI_TYPE


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _register(easy_track, deployer, factory, perm):
    easy_track.addEVMScriptFactory(factory, perm, {"from": deployer})


def _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion, admin):
    "Create the market via an ActivateMarket motion, appoint its steward, and register its pauser."
    owner = lido_lend.contract("owner")
    irm_router = lido_lend.contract("irmRouter")
    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    dashboard = lido_lend.contract("riskStewardDashboard")
    factory = deployer.deploy(
        LidoLendActivateMarket,
        trusted_caller,
        owner,
        irm_router,
        adaptive_curve_irm,
        circuit_breaker,
        dashboard,
    )
    irm_config = deployer.deploy(AdaptiveCurveConfigStub, lido_lend.market["curveParams"])
    create_sel = web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
    perm = (
        "0x"
        + adaptive_curve_irm.address[2:]
        + adaptive_curve_irm.applyIrmConfig.signature[2:]
        + irm_router.address[2:]
        + irm_router.setMarketIrm.signature[2:]
        + owner.address[2:]
        + create_sel
        + dashboard.address[2:]
        + dashboard.addMarketSteward.signature[2:]
        + circuit_breaker.address[2:]
        + circuit_breaker.registerPauser.signature[2:]
    )
    _register(easy_track, deployer, factory, perm)
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), easy_track.evmScriptExecutor(), {"from": admin})
    calldata = (
        "0x"
        + encode(
            [MARKET_PARAMS_ABI_TYPE, "address", "address", "address", "address", "bool"],
            [
                _market_params(lido_lend),
                irm_config.address,
                lido_lend.market["controller"],
                lido_lend.market["steward"],
                lido_lend.market["pauser"],
                True,
            ],
        ).hex()
    )
    enact_motion(easy_track, factory, calldata, trusted_caller)


def test_set_market_exit_book_allowed_scenario(
    lido_lend, easy_track, deployer, trusted_caller, enact_motion, admin, skip_if_already_activated
):
    "Allow-list a freshly-activated market independently on both exit books."
    core = lido_lend.contract("core")
    m = lido_lend.market
    market_id = m["id"]

    def unavailable(message):
        if lido_lend.local:
            pytest.skip(message)
        raise pytest.UsageError(message)

    if not lido_lend.has("morphoExitBook") or not lido_lend.has("erc4626ExitBook"):
        unavailable("deployment has no exit books")
    skip_if_already_activated(check_exit_books=True)
    if not lido_lend.has("circuitBreaker"):
        unavailable("descriptor lacks circuitBreaker; scenario needs it")
    if m["pauser"] == "0x" + "00" * 20:
        unavailable("activation scenario requires a nonzero pauser committee")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    if easy_track.evmScriptExecutor() != circuit_breaker.ADMIN():
        unavailable("EasyTrack executor is not the CircuitBreaker admin; cannot activate here")

    morpho = lido_lend.contract("morphoExitBook")
    erc4626 = lido_lend.contract("erc4626ExitBook")

    _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion, admin)
    assert core.market(market_id)["lastUpdate"] != 0
    assert lido_lend.contract("riskStewardDashboard").isMarketSteward(market_id, m["steward"])
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    executor = easy_track.evmScriptExecutor()
    morpho.grantRole(morpho.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})
    erc4626.grantRole(erc4626.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})

    morpho_factory = deployer.deploy(LidoLendSetMorphoExitBookAllowed, trusted_caller, morpho)
    erc4626_factory = deployer.deploy(LidoLendSetErc4626ExitBookAllowed, trusted_caller, erc4626)
    _register(
        easy_track,
        deployer,
        morpho_factory,
        "0x" + morpho.address[2:] + morpho.setMarketAllowed.signature[2:],
    )
    _register(
        easy_track,
        deployer,
        erc4626_factory,
        "0x" + erc4626.address[2:] + erc4626.setVaultAllowed.signature[2:],
    )

    def morpho_calldata(allowed):
        return "0x" + encode([f"{MARKET_PARAMS_ABI_TYPE}[]", "bool"], [[_market_params(lido_lend)], allowed]).hex()

    def erc4626_calldata(allowed):
        return "0x" + encode(["address[]", "bool"], [[m["vault"]], allowed]).hex()

    enact_motion(easy_track, morpho_factory, morpho_calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, erc4626_factory, erc4626_calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, morpho_factory, morpho_calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, erc4626_factory, erc4626_calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])
