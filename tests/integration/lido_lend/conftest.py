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
from utils.test_helpers import set_account_balance


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

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE as _MP_TYPE


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


class _LocalDeployment:
    def __init__(self, admin, easy_track_admin, contracts, market):
        self.admin = admin
        self.easy_track = ""
        self.easy_track_admin = easy_track_admin
        self.contracts = contracts
        self.market = dict(market)
        market_params = (
            self.market["loanToken"],
            self.market["collateralToken"],
            self.market["oracle"],
            self.market["irm"],
            self.market["lltv"],
        )
        self.market["id"] = bytes(web3.keccak(encode([_MP_TYPE], [market_params])))

    def has(self, name):
        return name in self.contracts

    def contract(self, name):
        return self.contracts[name]


# Addresses are per-deploy and must not be committed — fill them in locally for the network under test.
_ZERO = "0x0000000000000000000000000000000000000000"

# mainnet == mainnet-fork; WETH/wstETH market.
# Addresses are per-deploy and MUST NOT be committed (see module docstring). Zeroed here so the committed
# suite runs in local-mock mode; fill them in locally to point the suite at a real deployment.
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


@pytest.fixture
def lido_lend(
    deployer,
    accounts,
    MockERC20,
    LidoLendCoreStub,
    LidoLendOwnerStub,
    LidoLendMarketControllerStub,
    GuardianSignalsStub,
    RiskStewardDashboardStub,
    IrmRouterStub,
    AdaptiveCurveIrmStub,
    MorphoExitBookStub,
    Erc4626ExitBookStub,
    CircuitBreakerStub,
    LidoLendVaultStub,
):
    "Handles to the Lido Lend protocol deployed on this network (see `_DEPLOYMENTS`)."
    data = _DEPLOYMENTS.get(get_network_name())
    if data is None:
        pytest.skip(f"no Lido Lend deployment recorded for network '{get_network_name()}'")
    if len(web3.eth.get_code(data["contracts"]["core"])) != 0:
        return _Deployment(data)

    loan_token = MockERC20.deploy(18, {"from": deployer})
    collateral_token = MockERC20.deploy(18, {"from": deployer})
    oracle = accounts[8]
    admin = accounts[7]
    easy_track_admin = accounts[9]
    bootstrap_guardian = accounts[6]

    # In local mock mode, the scenario suite uses the standard brownie test accounts directly.
    for account in accounts[:10]:
        set_account_balance(account.address)

    core = LidoLendCoreStub.deploy({"from": deployer})
    owner = LidoLendOwnerStub.deploy({"from": deployer})
    owner.setCore(core, {"from": deployer})
    controller = LidoLendMarketControllerStub.deploy({"from": deployer})
    guardian_signals = GuardianSignalsStub.deploy({"from": deployer})
    dashboard = RiskStewardDashboardStub.deploy({"from": deployer})
    irm_router = IrmRouterStub.deploy({"from": deployer})
    curve = AdaptiveCurveIrmStub.deploy({"from": deployer})
    morpho = MorphoExitBookStub.deploy({"from": deployer})
    erc4626 = Erc4626ExitBookStub.deploy({"from": deployer})
    circuit_breaker = CircuitBreakerStub.deploy("0x0000000000000000000000000000000000000000", {"from": deployer})
    vault = LidoLendVaultStub.deploy({"from": deployer})

    market = {
        "loanToken": loan_token.address,
        "collateralToken": collateral_token.address,
        "oracle": oracle.address,
        "irm": irm_router.address,
        "lltv": 800000000000000000,
        "curve": curve.address,
        "controller": controller.address,
        "vault": vault.address,
        "pauser": admin.address,
    }
    deployment = _LocalDeployment(
        admin.address,
        easy_track_admin.address,
        {
            "core": core,
            "owner": owner,
            "controller": controller,
            "guardianSignals": guardian_signals,
            "riskStewardDashboard": dashboard,
            "irmRouter": irm_router,
            "adaptiveCurveIrm": curve,
            "morphoExitBook": morpho,
            "erc4626ExitBook": erc4626,
            "circuitBreaker": circuit_breaker,
        },
        market,
    )

    controller.setGuardianSignals(guardian_signals, {"from": deployer})
    controller.setMarketId(deployment.market["id"], {"from": deployer})
    core.setMarketController(deployment.market["id"], controller, {"from": deployer})
    core.setMarketParams(
        deployment.market["id"],
        (
            deployment.market["loanToken"],
            deployment.market["collateralToken"],
            deployment.market["oracle"],
            deployment.market["irm"],
            deployment.market["lltv"],
        ),
        {"from": deployer},
    )
    vault.setMarketId(deployment.market["id"], {"from": deployer})
    morpho.setMarketVault(deployment.market["id"], vault, {"from": deployer})
    guardian_signals.addGuardian(bootstrap_guardian, {"from": deployer})

    return deployment


@pytest.fixture
def admin(lido_lend, accounts):
    "The Lido Lend role admin (Agent), impersonated so tests can set up preconditions directly."
    if len(web3.eth.get_code(lido_lend.admin)) == 0:
        return accounts.at(lido_lend.admin, force=True)
    voting = accounts.at(lido_lend.admin, force=True)
    web3.provider.make_request("anvil_setBalance", [voting.address, hex(10**22)])
    return voting


@pytest.fixture
def easy_track(lido_lend, admin, accounts, EasyTrack, EVMScriptExecutor, lido_contracts, deployer):
    "EasyTrack + EVMScriptExecutor with the executor holding every role the Lido Lend factories act through."
    # Real deployment: use the REAL EasyTrack, not a throwaway. Its executor is already the CircuitBreaker
    # admin (immutable, set to it at deploy) and already holds every protocol role our deploy granted, so a
    # fresh executor could never stand in — the CircuitBreaker cannot be repointed (no `setAdmin`), and the
    # activation motion's `registerPauser` is admin-gated to exactly this executor. We only need
    # factory-registration rights, so grant the deployer EasyTrack's DEFAULT_ADMIN_ROLE from the impersonated
    # EasyTrack admin (Aragon Voting); `register_factory` and the tests' inline `addEVMScriptFactory` then work
    # from `deployer` unchanged.
    if lido_lend.easy_track:
        et = EasyTrack.at(lido_lend.easy_track)
        et_admin = accounts.at(lido_lend.easy_track_admin, force=True)
        web3.provider.make_request("anvil_setBalance", [et_admin.address, hex(10**22)])
        et.grantRole(et.DEFAULT_ADMIN_ROLE(), deployer, {"from": et_admin})
        return et

    # Local mock: a fresh EasyTrack + EVMScriptExecutor the deployer fully controls, with the executor granted
    # every role on the stub protocol (including repointing the stub CircuitBreaker's admin at it).
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
    set_account_balance(executor.address)
    set_account_balance(et.address)

    ex = executor.address
    circuit_breaker = lido_lend.contract("circuitBreaker")
    if circuit_breaker.ADMIN() != ex:
        circuit_breaker.setAdmin(ex, {"from": deployer})

    gs = lido_lend.contract("guardianSignals")
    gs.grantRole(gs.MANAGER_ROLE(), ex, {"from": admin})
    gs.grantRole(gs.ACCESS_RESTORER_ROLE(), ex, {"from": admin})
    controller = lido_lend.contract("controller")
    controller.grantRole(controller.MANAGER_ROLE(), ex, {"from": admin})
    controller.grantRole(controller.UNFREEZER_ROLE(), ex, {"from": admin})

    dashboard_addr = lido_lend.contracts.get("riskStewardDashboard")
    if dashboard_addr and getattr(dashboard_addr, "address", dashboard_addr) != _ZERO:
        dashboard = lido_lend.contract("riskStewardDashboard")
        dashboard.grantRole(dashboard.STEWARD_ADMIN_ROLE(), ex, {"from": admin})

    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    if adaptive_curve_irm.manager() != ex:
        adaptive_curve_irm.setManager(ex, {"from": admin})
    irm_router = lido_lend.contract("irmRouter")
    if irm_router.manager() != ex:
        irm_router.setManager(ex, {"from": admin})
    return et


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


# Any curve params satisfying the factory/config bounds; used to configure a market's curve before creation.
_ACTIVATION_CURVE_PARAMS = (4000000000000000000, 1585489599188, 900000000000000000, 634195839, 31709791, 63419583967, 0)


def _route_curve(lido_lend, accounts):
    "Route the market's curve on the router as its current manager (createMarket requires the IRM to be set)."
    router = lido_lend.contract("irmRouter")
    mgr = accounts.at(router.manager(), force=True)
    web3.provider.make_request("anvil_setBalance", [mgr.address, hex(10**22)])
    router.setMarketIrm(_market_params(lido_lend), lido_lend.market["curve"], {"from": mgr})


def _set_curve_params(lido_lend, accounts):
    "Set the market's curve params on the AdaptiveCurveIrm as its current manager (createMarket's borrowRate ping reverts otherwise)."
    curve = lido_lend.contract("adaptiveCurveIrm")
    mgr = accounts.at(curve.manager(), force=True)
    web3.provider.make_request("anvil_setBalance", [mgr.address, hex(10**22)])
    curve.setMarketCurveParams(_market_params(lido_lend), _ACTIVATION_CURVE_PARAMS, {"from": mgr})


@pytest.fixture
def created_market(lido_lend, admin, accounts):
    "Ensure the descriptor market is activated on the core so the domain-scoped factories can resolve `marketController(id)` / `idToMarketParams(id)` / `router.marketIrm(id)`. Mirrors the on-chain activation order: route the IRM curve, then createMarket (which requires the IRM already set)."
    core = lido_lend.contract("core")
    market_id = lido_lend.market["id"]
    if core.market(market_id)["lastUpdate"] == 0:
        _set_curve_params(lido_lend, accounts)
        _route_curve(lido_lend, accounts)
        owner = lido_lend.contract("owner")
        if not lido_lend.easy_track:
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
