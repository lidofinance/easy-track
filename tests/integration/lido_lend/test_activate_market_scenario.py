import pytest
from brownie import reverts, LidoLendActivateMarket, EasyTrack, accounts, web3
from eth_abi import encode

PAUSER_COMMITTEE = "0x" + "cc" * 20

ACTIVATE_TYPES = ["(address,address,address,address,uint256)", "address", "address", "address", "bool"]


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _activate_prereqs(lido_lend):
    "Common skips + handles for the activation scenarios; skips cleanly if the scenario cannot run here."
    core = lido_lend.contract("core")
    if core.market(lido_lend.market["id"])["lastUpdate"] != 0:
        pytest.skip("descriptor market already created on the core; activate scenario needs a fresh market")
    if not lido_lend.has("circuitBreaker") or not lido_lend.easy_track:
        pytest.skip("descriptor lacks circuitBreaker / real easyTrack; activate scenario needs both")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    easy_track = EasyTrack.at(lido_lend.easy_track)
    if easy_track.evmScriptExecutor() != circuit_breaker.ADMIN():
        pytest.skip("descriptor easyTrack executor is not the CircuitBreaker admin; activation cannot run through it")
    return core, circuit_breaker, easy_track


def _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track):
    "Deploy an ActivateMarket factory and register it on the real EasyTrack (3-call activation permission)."
    owner = lido_lend.contract("owner")
    irm_router = lido_lend.contract("irmRouter")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    factory = deployer.deploy(LidoLendActivateMarket, trusted_caller, owner, irm_router, circuit_breaker)
    create_sel = web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
    perm = (
        "0x"
        + irm_router.address[2:] + irm_router.setMarketIrm.signature[2:]
        + owner.address[2:] + create_sel
        + circuit_breaker.address[2:] + circuit_breaker.registerPauser.signature[2:]
    )
    voting = accounts.at(lido_lend.easy_track_admin, force=True)
    web3.provider.make_request("anvil_setBalance", [voting.address, hex(10**22)])
    easy_track.addEVMScriptFactory(factory, perm, {"from": voting})

    admin = accounts.at(lido_lend.admin, force=True)
    web3.provider.make_request("anvil_setBalance", [admin.address, hex(10**22)])
    executor = easy_track.evmScriptExecutor()
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), executor, {"from": admin})
    return factory, irm_router


def _calldata(lido_lend, enable_settlement):
    m = lido_lend.market
    return "0x" + encode(
        ACTIVATE_TYPES,
        [_market_params(lido_lend), m["curve"], m["controller"], PAUSER_COMMITTEE, enable_settlement],
    ).hex()


def test_activate_market_scenario(lido_lend, deployer, trusted_caller, stranger, enact_motion, advance_time):
    "Activate a deployed-but-INERT market: bind the IRM curve, create it on the core, register the pauser."
    core, circuit_breaker, easy_track = _activate_prereqs(lido_lend)
    m = lido_lend.market
    market_id = m["id"]

    assert core.market(market_id)["lastUpdate"] == 0
    factory, irm_router = _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track)

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


def test_activate_market_without_settlement_scenario(lido_lend, deployer, trusted_caller, enact_motion):
    "Activate with enableSettlement=False: the market is created with its settlement queue disabled."
    core, _, easy_track = _activate_prereqs(lido_lend)
    market_id = lido_lend.market["id"]

    factory, _ = _deploy_and_register(lido_lend, deployer, trusted_caller, easy_track)
    enact_motion(easy_track, factory, _calldata(lido_lend, False), trusted_caller)

    assert core.market(market_id)["lastUpdate"] != 0
    assert not core.isSettlementEnabled(market_id)
