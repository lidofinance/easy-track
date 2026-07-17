
import pytest
from brownie import LidoLendActivateMarket, LidoLendSetMarketExitBookAllowed, accounts, web3
from eth_abi import encode
from utils.test_helpers import set_account_balance
from utils.lido_lend import MARKET_PARAMS_ABI_TYPE, CURVE_PARAMS_ABI_TYPE as CURVE_PARAMS_TYPE

PAUSER_COMMITTEE = "0x" + "cc" * 20
CURVE_PARAMS = (4000000000000000000, 1585489599188, 900000000000000000, 634195839, 31709791, 63419583967, 0)


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _admin(lido_lend):
    a = accounts.at(lido_lend.admin, force=True)
    set_account_balance(a.address)
    return a


def _register(easy_track, deployer, factory, perm):
    easy_track.addEVMScriptFactory(factory, perm, {"from": deployer})


def _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion):
    "Create the market via an ActivateMarket motion (setMarketIrm -> createMarket -> registerPauser)."
    owner = lido_lend.contract("owner")
    irm_router = lido_lend.contract("irmRouter")
    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    factory = deployer.deploy(
        LidoLendActivateMarket, trusted_caller, owner, irm_router, adaptive_curve_irm, circuit_breaker
    )
    create_sel = web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
    perm = (
        "0x"
        + adaptive_curve_irm.address[2:] + adaptive_curve_irm.setMarketCurveParams.signature[2:]
        + irm_router.address[2:] + irm_router.setMarketIrm.signature[2:]
        + owner.address[2:] + create_sel
        + circuit_breaker.address[2:] + circuit_breaker.registerPauser.signature[2:]
    )
    _register(easy_track, deployer, factory, perm)
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), easy_track.evmScriptExecutor(), {"from": _admin(lido_lend)})
    calldata = "0x" + encode(
        [MARKET_PARAMS_ABI_TYPE, CURVE_PARAMS_TYPE, "address", "address", "bool"],
        [_market_params(lido_lend), CURVE_PARAMS, lido_lend.market["controller"], PAUSER_COMMITTEE, True],
    ).hex()
    enact_motion(easy_track, factory, calldata, trusted_caller)


def test_set_market_exit_book_allowed_scenario(
    lido_lend, easy_track, deployer, trusted_caller, enact_motion
):
    "Allow-list a freshly-activated market on both exit books via one motion, then dis-allow via another."
    core = lido_lend.contract("core")
    m = lido_lend.market
    market_id = m["id"]

    if core.market(market_id)["lastUpdate"] != 0:
        pytest.skip("descriptor market already created on the core; this scenario activates a fresh market first")
    if not lido_lend.has("circuitBreaker"):
        pytest.skip("descriptor lacks circuitBreaker; scenario needs it")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    if easy_track.evmScriptExecutor() != circuit_breaker.ADMIN():
        pytest.skip("EasyTrack executor is not the CircuitBreaker admin; cannot activate here")

    morpho = lido_lend.contract("morphoExitBook")
    erc4626 = lido_lend.contract("erc4626ExitBook")

    _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion)
    assert core.market(market_id)["lastUpdate"] != 0
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    admin = _admin(lido_lend)
    executor = easy_track.evmScriptExecutor()
    morpho.grantRole(morpho.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})
    erc4626.grantRole(erc4626.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})

    factory = deployer.deploy(LidoLendSetMarketExitBookAllowed, trusted_caller, morpho, erc4626)
    perm = (
        "0x"
        + morpho.address[2:] + morpho.setMarketAllowed.signature[2:]
        + erc4626.address[2:] + erc4626.setVaultAllowed.signature[2:]
    )
    _register(easy_track, deployer, factory, perm)

    def calldata(allowed):
        return "0x" + encode(
            [MARKET_PARAMS_ABI_TYPE, "address", "bool"],
            [_market_params(lido_lend), m["vault"], allowed],
        ).hex()

    enact_motion(easy_track, factory, calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, factory, calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])
