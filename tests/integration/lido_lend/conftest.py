"""
Lido Lend EasyTrack scenario tests: drive each factory through the real EasyTrack + EVMScriptExecutor +
Aragon stack on a mainnet-like fork, then assert the effect. Deployed addresses live in `_DEPLOYMENTS`
below (keyed by network, like `utils/lido.py`); fill them in for a deploy to run this suite. Addresses
are zeroed in the commit (per-deploy, not committed); an unknown network or code-less core skips. Set
LIDO_LEND_ATTACH=1 to attach to an already-running external anvil (see the monkeypatch below).
"""

import os

import pytest
from brownie import interface, web3
from eth_abi import encode

import constants
from utils.config import get_network_name


# Attaching to an external anvil needs two brownie internals patched (opt-in via LIDO_LEND_ATTACH): register
# the native anvil backend (else attach falls back to ganache, whose impersonation RPC anvil lacks), and stub
# `_find_rpc_process_pid` (it hangs on macOS; we must not kill an externally-owned node anyway).
if os.environ.get("LIDO_LEND_ATTACH") == "1":
    import importlib

    _rpc = importlib.import_module("brownie.network.rpc")  # the module (the attr is shadowed by an Rpc instance)
    _anvil_backend = importlib.import_module("brownie.network.rpc.anvil")

    _rpc.ATTACH_BACKENDS = {"anvil": _anvil_backend, **_rpc.ATTACH_BACKENDS}
    _rpc.Rpc._find_rpc_process_pid = lambda self, laddr: os.getpid()


# descriptor key -> brownie interface (raw ABI committed under interfaces/).
_INTERFACE = {
    "core": "LidoLend",
    "owner": "LidoLendOwner",
    "controller": "LidoLendMarketController",
    "guardianSignals": "GuardianSignals",
    "riskStewardDashboard": "RiskStewardDashboard",
    "irmRouter": "IrmRouter",
    "adaptiveCurveIrm": "AdaptiveCurveIrm",
    "morphoExitBook": "MorphoExitBook",
    "erc4626ExitBook": "Erc4626ExitBook",
    "circuitBreaker": "CircuitBreaker",
}

_MP_TYPE = "(address,address,address,address,uint256)"


class _Deployment:
    def __init__(self, data):
        self.admin = data["admin"]
        self.easy_track = data["easyTrack"]
        self.easy_track_admin = data["easyTrackAdmin"]
        self.contracts = data["contracts"]
        self.market = dict(data["market"])
        # marketId is not stored — it is the Morpho id, keccak256(abi.encode(marketParams)), so we derive it
        # (as bytes, which abi-encoding as bytes32 and contract calls both need). test_market_id_consistency
        # asserts this derivation matches the on-chain controller.marketId().
        m = self.market
        market_params = (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])
        self.market["id"] = bytes(web3.keccak(encode([_MP_TYPE], [market_params])))

    def has(self, name):
        return name in self.contracts

    def contract(self, name):
        return getattr(interface, _INTERFACE[name])(self.contracts[name])


# Addresses are per-deploy and must not be committed — fill them in locally for the network under test.
_ZERO = "0x0000000000000000000000000000000000000000"

# mainnet == mainnet-fork; WETH/wstETH market.
_MAINNET = {
    "admin": _ZERO,
    "easyTrack": _ZERO,
    "easyTrackAdmin": _ZERO,
    "contracts": {
        "core": _ZERO,
        "owner": _ZERO,
        "controller": _ZERO,
        "guardianSignals": _ZERO,
        "riskStewardDashboard": _ZERO,
        "irmRouter": _ZERO,
        "adaptiveCurveIrm": _ZERO,
        "morphoExitBook": _ZERO,
        "erc4626ExitBook": _ZERO,
        "circuitBreaker": _ZERO,
    },
    "market": {
        "loanToken": _ZERO,
        "collateralToken": _ZERO,
        "oracle": _ZERO,
        "irm": _ZERO,
        "lltv": 800000000000000000,
        "curve": _ZERO,
        "controller": _ZERO,
        "vault": _ZERO,
        "pauser": _ZERO,
    },
}

_DEPLOYMENTS = {
    "mainnet": _MAINNET,
    "mainnet-fork": _MAINNET,
}


@pytest.fixture(scope="module")
def lido_lend():
    "Handles to the Lido Lend protocol deployed on this network (see `_DEPLOYMENTS`)."
    data = _DEPLOYMENTS.get(get_network_name())
    if data is None:
        pytest.skip(f"no Lido Lend deployment recorded for network '{get_network_name()}'")
    if len(web3.eth.get_code(data["contracts"]["core"])) == 0:
        pytest.skip(f"Lido Lend core has no code at {data['contracts']['core']} on '{get_network_name()}'; not deployed here")
    return _Deployment(data)


@pytest.fixture
def admin(lido_lend, accounts):
    "The Lido Lend role admin (Agent), impersonated so tests can set up preconditions directly."
    voting = accounts.at(lido_lend.admin, force=True)
    web3.provider.make_request("anvil_setBalance", [voting.address, hex(10**22)])
    return voting


@pytest.fixture
def easy_track(lido_lend, admin, EasyTrack, EVMScriptExecutor, lido_contracts, deployer):
    "A fresh EasyTrack + EVMScriptExecutor, with the executor granted every role the Lido Lend factories act through."
    et = deployer.deploy(
        EasyTrack,
        lido_contracts.ldo,
        deployer,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    executor = deployer.deploy(EVMScriptExecutor, lido_contracts.aragon.calls_script, et)
    executor.transferOwnership(lido_contracts.aragon.voting, {"from": deployer})
    et.setEVMScriptExecutor(executor, {"from": deployer})

    ex = executor.address
    gs = lido_lend.contract("guardianSignals")
    gs.grantRole(gs.MANAGER_ROLE(), ex, {"from": admin})
    gs.grantRole(gs.ACCESS_RESTORER_ROLE(), ex, {"from": admin})
    controller = lido_lend.contract("controller")
    controller.grantRole(controller.MANAGER_ROLE(), ex, {"from": admin})
    controller.grantRole(controller.UNFREEZER_ROLE(), ex, {"from": admin})
    dashboard = lido_lend.contract("riskStewardDashboard")
    dashboard.grantRole(dashboard.STEWARD_ADMIN_ROLE(), ex, {"from": admin})
    lido_lend.contract("adaptiveCurveIrm").setManager(ex, {"from": admin})
    lido_lend.contract("irmRouter").setManager(ex, {"from": admin})
    return et


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _route_curve(lido_lend, accounts):
    "Route the market's curve on the router as its current manager (createMarket requires the IRM to be set)."
    router = lido_lend.contract("irmRouter")
    mgr = accounts.at(router.manager(), force=True)
    web3.provider.make_request("anvil_setBalance", [mgr.address, hex(10**22)])
    router.setMarketIrm(_market_params(lido_lend), lido_lend.market["curve"], {"from": mgr})


@pytest.fixture
def created_market(lido_lend, admin, accounts):
    "Ensure the descriptor market is activated on the core so the domain-scoped factories can resolve `marketController(id)` / `idToMarketParams(id)` / `router.marketIrm(id)`. Mirrors the on-chain activation order: route the IRM curve, then createMarket (which requires the IRM already set)."
    core = lido_lend.contract("core")
    market_id = lido_lend.market["id"]
    if core.market(market_id)["lastUpdate"] == 0:
        _route_curve(lido_lend, accounts)
        owner = lido_lend.contract("owner")
        owner.grantRole(owner.MARKET_CREATOR_ROLE(), admin, {"from": admin})
        owner.createMarket(_market_params(lido_lend), lido_lend.market["controller"], False, {"from": admin})
    return lido_lend


@pytest.fixture
def route_market_curve(lido_lend, accounts):
    "Route the market's curve on the router (also done by created_market; kept for tests that call it explicitly)."

    def _route():
        _route_curve(lido_lend, accounts)

    return _route


@pytest.fixture
def register_factory(easy_track, deployer):
    "Registers an EVMScript factory on the fresh EasyTrack (deployed with the deployer as its admin)."

    def _register(factory, perm):
        easy_track.addEVMScriptFactory(factory, perm, {"from": deployer})

    return _register


@pytest.fixture
def permission():
    "Builds an EVMScript factory permission blob: concatenation of (target address + 4-byte selector) per call."

    def _permission(*calls):
        blob = "0x"
        for target, method in calls:
            blob += str(target)[2:] + method.signature[2:]
        return blob

    return _permission


def _advance_time(seconds):
    # brownie's anvil backend issues `evm_mine [1]`, which anvil >=1.x reads as an (invalid) timestamp;
    # drive time travel via raw RPC instead so it works against an attached anvil node.
    web3.provider.make_request("evm_increaseTime", [seconds])
    web3.provider.make_request("evm_mine", [])


@pytest.fixture
def advance_time():
    "Advances chain time past a duration via raw RPC (brownie's anvil backend mine call is incompatible)."
    return _advance_time


@pytest.fixture
def enact_motion(stranger):
    "Runs a full motion lifecycle against the real EasyTrack: create -> wait out the objection window -> enact."

    def _enact(easy_track, factory, calldata, trusted_caller):
        tx = easy_track.createMotion(factory, calldata, {"from": trusted_caller})
        motion_id = tx.events["MotionCreated"]["_motionId"]
        _advance_time(easy_track.motionDuration() + 100)
        easy_track.enactMotion(
            motion_id, tx.events["MotionCreated"]["_evmScriptCallData"], {"from": stranger}
        )
        return tx

    return _enact
