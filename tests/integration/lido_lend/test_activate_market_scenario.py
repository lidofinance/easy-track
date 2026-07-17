import pytest
from brownie import reverts, LidoLendActivateMarket, web3
from eth_abi import encode

PAUSER_COMMITTEE = "0x" + "cc" * 20

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE, CURVE_PARAMS_ABI_TYPE as CURVE_PARAMS_TYPE

CURVE_PARAMS = (4000000000000000000, 1585489599188, 900000000000000000, 634195839, 31709791, 63419583967, 0)
ACTIVATE_TYPES = [MARKET_PARAMS_ABI_TYPE, CURVE_PARAMS_TYPE, "address", "address", "bool"]


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _activate_prereqs(lido_lend, easy_track):
    "Common handles for the activation scenarios against the fresh local EasyTrack fixture."
    core = lido_lend.contract("core")
    if core.market(lido_lend.market["id"])["lastUpdate"] != 0:
        pytest.skip("descriptor market already created on the core; activate scenario needs a fresh market")
    if not lido_lend.has("circuitBreaker"):
        pytest.skip("descriptor lacks circuitBreaker; activation scenario needs it")
    circuit_breaker = lido_lend.contract("circuitBreaker")

    if easy_track.evmScriptExecutor() != circuit_breaker.ADMIN():
        pytest.skip("EasyTrack executor is not the CircuitBreaker admin; activation cannot run through it")
    return core, circuit_breaker, easy_track


def _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track, admin):
    "Deploy an ActivateMarket factory and register it on EasyTrack (4-call activation permission)."
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
    easy_track.addEVMScriptFactory(factory, perm, {"from": deployer})
    executor = easy_track.evmScriptExecutor()
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), executor, {"from": admin})
    return factory, irm_router


def _calldata(lido_lend, enable_settlement):
    m = lido_lend.market
    return "0x" + encode(
        ACTIVATE_TYPES, [_market_params(lido_lend), CURVE_PARAMS, m["controller"], PAUSER_COMMITTEE, enable_settlement],
    ).hex()


def test_activate_market_scenario(
    lido_lend, easy_track, deployer, trusted_caller, stranger, enact_motion, advance_time, admin
):
    "Activate a deployed-but-INERT market: bind the IRM curve, create it on the core, register the pauser."
    core, circuit_breaker, easy_track = _activate_prereqs(lido_lend, easy_track)
    m = lido_lend.market
    market_id = m["id"]

    assert core.market(market_id)["lastUpdate"] == 0
    factory, irm_router = _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track, admin)

    calldata = _calldata(lido_lend, True)
    enact_motion(easy_track, factory, calldata, trusted_caller)

    assert core.market(market_id)["lastUpdate"] != 0
    assert irm_router.marketIrm(market_id) == m["curve"]
    assert circuit_breaker.getPauser(m["controller"]) == PAUSER_COMMITTEE
    assert core.isSettlementEnabled(market_id)

    tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})
    motion_id = tx.events["MotionCreated"]["_motionId"]
    advance_time(easy_track.motionDuration() + 100)
    with reverts():
        easy_track.enactMotion(motion_id, tx.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger})


def test_activate_market_without_settlement_scenario(
    lido_lend, easy_track, deployer, trusted_caller, enact_motion, admin
):
    "Activate with enableSettlement=False: the market is created with its settlement queue disabled."
    core, _, easy_track = _activate_prereqs(lido_lend, easy_track)
    market_id = lido_lend.market["id"]

    factory, _ = _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track, admin)
    enact_motion(easy_track, factory, _calldata(lido_lend, False), trusted_caller)

    assert core.market(market_id)["lastUpdate"] != 0
    assert not core.isSettlementEnabled(market_id)
