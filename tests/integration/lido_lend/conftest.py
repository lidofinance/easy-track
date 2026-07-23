"""
Lido Lend EasyTrack scenario tests: drive each factory through the real EasyTrack + EVMScriptExecutor +
Aragon stack on a mainnet-like fork, then assert the effect. Without external configuration the suite deploys
strict local stubs. Set LIDO_LEND_REGISTRY to a Lido Lend registry.toml and optionally LIDO_LEND_MARKET to the
primary market name; the loader reads activation-<market>.toml files next to the registry. Set
LIDO_LEND_ATTACH=1 to attach to an already-running external Anvil (see the monkeypatch below).
"""

import os
from pathlib import Path

import pytest
from brownie import interface, web3
from eth_abi import encode
try:
    import tomllib
except ImportError:
    import tomli as tomllib

import constants
from utils.config import get_network_name
from utils.deployed_easy_track import addresses as easy_track_addresses
from utils.lido import addresses as lido_addresses
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


def _role(name):
    return web3.keccak(text=name)


def _impersonated_account(address, accounts):
    """Explicitly re-impersonate on every use.

    Brownie caches Account objects across test snapshots, while Hardhat/Anvil may roll back the backend's
    impersonation state. Relying on accounts.at(..., force=True) alone then leaves a cached account without a
    signer and produces `ValueError: No Signer available`.
    """
    client = web3.client_version.lower()
    if "anvil" in client:
        method = "anvil_impersonateAccount"
    elif "hardhat" in client:
        method = "hardhat_impersonateAccount"
    else:
        raise pytest.UsageError(f"Lido Lend scenarios require Hardhat or Anvil, connected to {web3.client_version}")

    response = web3.provider.make_request(method, [str(address)])
    if response.get("error"):
        raise pytest.UsageError(f"{method} failed for {address}: {response['error']}")
    account = accounts.at(address, force=True)
    set_account_balance(account.address)
    return account


class _Deployment:
    def __init__(self, data, local=False):
        self.admin = data["admin"]
        self.easy_track = data.get("easyTrack", "")
        self.easy_track_admin = data.get("easyTrackAdmin")
        self.evm_script_executor = data.get("evmScriptExecutor")
        self.contracts = data["contracts"]
        self.market = dict(data["market"])
        m = self.market
        market_params = (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])
        derived_id = bytes(web3.keccak(encode([_MP_TYPE], [market_params])))
        if "id" in self.market:
            assert self.market["id"] == derived_id, "registry market id does not match its activation market params"
        else:
            self.market["id"] = derived_id
        self.local = local

    def has(self, name):
        value = self.contracts.get(name)
        return value is not None and str(getattr(value, "address", value)) != _ZERO

    def contract(self, name):
        value = self.contracts[name]
        return value if self.local else getattr(interface, _INTERFACE[name])(value)


# Deployment-specific addresses come exclusively from the external registry.
_ZERO = "0x0000000000000000000000000000000000000000"

# Generic valid curve used by the locally deployed test market.
_DEFAULT_TEST_CURVE_PARAMS = (
    4000000000000000000,
    1585489599188,
    900000000000000000,
    634195839,
    31709791,
    63419583967,
    0,
)


def _read_toml(path, label):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise pytest.UsageError(f"{label} does not exist: {path}")
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _as_int(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def _as_bytes32(value):
    raw = value[2:] if value.startswith("0x") else value
    if len(raw) != 64:
        raise pytest.UsageError(f"expected bytes32 hex value, got {value!r}")
    return bytes.fromhex(raw)


def _market_from_artifacts(name, registry_market, protocol, activation):
    params = activation["market_params"]
    curve = activation["curve_params"]
    activation_settings = activation["activation"]
    registry_id = _as_bytes32(registry_market["id"])
    if params["oracle"].lower() != registry_market["oracle"].lower():
        raise pytest.UsageError(f"market {name!r}: registry and activation plan disagree on oracle")
    if activation_settings["controller"].lower() != registry_market["controller"].lower():
        raise pytest.UsageError(f"market {name!r}: registry and activation plan disagree on controller")
    pausers = registry_market.get("pausers", [])
    if pausers and activation_settings["circuit_breaker"].lower() != pausers[0].lower():
        raise pytest.UsageError(f"market {name!r}: activation plan circuit breaker is not the first registry pauser")
    market = {
        "id": registry_id,
        "loanToken": params["loan_token"],
        "collateralToken": params["collateral_token"],
        "oracle": params["oracle"],
        "irm": params["irm"],
        "lltv": _as_int(params["lltv"]),
        "curve": protocol["adaptive_curve_irm"],
        "curveParams": (
            _as_int(curve["curve_steepness"]),
            _as_int(curve["adjustment_speed"]),
            _as_int(curve["target_utilization"]),
            _as_int(curve["initial_rate_at_target"]),
            _as_int(curve["min_rate_at_target"]),
            _as_int(curve["max_rate_at_target"]),
            _as_int(curve["max_borrow_rate"]),
        ),
        "controller": registry_market["controller"],
        "vault": registry_market["vault"],
        "pauser": activation_settings.get("pauser_committee", _ZERO),
    }
    derived_id = bytes(
        web3.keccak(
            encode(
                [_MP_TYPE],
                [(market["loanToken"], market["collateralToken"], market["oracle"], market["irm"], market["lltv"])],
            )
        )
    )
    if registry_id != derived_id:
        raise pytest.UsageError(
            f"market {name!r}: registry id does not match activation plan market params"
        )
    return market


def _load_registry_deployment():
    registry_path = os.environ.get("LIDO_LEND_REGISTRY")
    if not registry_path:
        return None

    registry_path = Path(registry_path).expanduser().resolve()
    registry = _read_toml(registry_path, "LIDO_LEND_REGISTRY")
    if registry.get("artifact", {}).get("kind") != "protocol-registry":
        raise pytest.UsageError(f"not a protocol registry: {registry_path}")

    protocol = registry["protocol"]
    # `protocol.network` is deployment metadata and may contain an arbitrary deployment label. Resolve the
    # pre-existing EasyTrack/Lido addresses from the Brownie network actually running the tests.
    network_name = get_network_name()
    et = easy_track_addresses(network_name)
    lido = lido_addresses(network_name)
    if protocol["evm_script_executor"].lower() != et.evm_script_executor.lower():
        raise pytest.UsageError(
            "registry executor does not match the deployed EasyTrack executor for "
            f"{network_name}: {protocol['evm_script_executor']} != {et.evm_script_executor}"
        )

    registry_markets = registry.get("markets", {})
    if not registry_markets:
        raise pytest.UsageError(f"registry has no markets: {registry_path}")
    primary_name = os.environ.get("LIDO_LEND_MARKET", next(iter(registry_markets)))
    if primary_name not in registry_markets:
        raise pytest.UsageError(
            f"LIDO_LEND_MARKET={primary_name!r} is absent from {registry_path}; "
            f"available: {', '.join(registry_markets)}"
        )

    activation_path = registry_path.parent / f"activation-{primary_name}.toml"
    activation = _read_toml(activation_path, f"activation plan for market {primary_name!r}")
    if activation.get("artifact", {}).get("kind") != "activation-plan":
        raise pytest.UsageError(f"not an activation plan: {activation_path}")
    for field in ("deployment", "chain_id", "config_hash"):
        if activation["artifact"].get(field) != registry["artifact"].get(field):
            raise pytest.UsageError(
                f"activation plan for market {primary_name!r} has a different artifact {field}"
            )

    registry_market = registry_markets[primary_name]
    primary = _market_from_artifacts(primary_name, registry_market, protocol, activation)
    pausers = registry_market.get("pausers", [])
    contracts = {
        "core": protocol["core"],
        "owner": protocol["owner_facade"],
        "controller": primary["controller"],
        "guardianSignals": registry_market["guardian_signals"],
        "riskStewardDashboard": protocol["risk_steward_dashboard"],
        "irmRouter": protocol["irm_router"],
        "adaptiveCurveIrm": protocol["adaptive_curve_irm"],
    }
    exit_books = registry.get("exit_books", {})
    if "morpho" in exit_books:
        contracts["morphoExitBook"] = exit_books["morpho"]
    if "erc4626" in exit_books:
        contracts["erc4626ExitBook"] = exit_books["erc4626"]
    if pausers:
        contracts["circuitBreaker"] = pausers[0]

    required_code = {
        **contracts,
        "market.vault": primary["vault"],
        "market.loan_token": primary["loanToken"],
        "market.collateral_token": primary["collateralToken"],
        "market.oracle": primary["oracle"],
    }
    missing_code = [
        f"{label}={address}"
        for label, address in required_code.items()
        if address == _ZERO or len(web3.eth.get_code(address)) == 0
    ]
    if missing_code:
        raise pytest.UsageError(
            "registry points to addresses without code on the connected Anvil fork: "
            + ", ".join(missing_code)
        )

    return {
        "admin": protocol["agent"],
        "easyTrack": et.easy_track,
        "easyTrackAdmin": lido.aragon.voting,
        "evmScriptExecutor": protocol["evm_script_executor"],
        "contracts": contracts,
        "market": primary,
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
    "Handles to registry-provided Lido Lend contracts or strict local stubs."
    data = _load_registry_deployment()
    if data is not None:
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
    circuit_breaker = CircuitBreakerStub.deploy(_ZERO, {"from": deployer})
    vault = LidoLendVaultStub.deploy({"from": deployer})

    market = {
        "loanToken": loan_token.address,
        "collateralToken": collateral_token.address,
        "oracle": oracle.address,
        "irm": irm_router.address,
        "lltv": 800000000000000000,
        "curve": curve.address,
        "curveParams": _DEFAULT_TEST_CURVE_PARAMS,
        "controller": controller.address,
        "vault": vault.address,
        "pauser": admin.address,
    }
    deployment = _Deployment(
        {
            "admin": admin.address,
            "easyTrackAdmin": easy_track_admin.address,
            "contracts": {
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
            "market": market,
        },
        local=True,
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

    # Mirror the production two-hop authorization path. The executor receives capability roles on the facade
    # later in the `easy_track` fixture; the facade itself is the caller seen by controller/GuardianSignals.
    controller.grantRole(controller.MANAGER_ROLE(), owner, {"from": deployer})
    controller.grantRole(controller.UNFREEZER_ROLE(), owner, {"from": deployer})
    guardian_signals.grantRole(guardian_signals.MANAGER_ROLE(), owner, {"from": deployer})
    guardian_signals.grantRole(guardian_signals.ACCESS_RESTORER_ROLE(), owner, {"from": deployer})

    # Scenario setup occasionally needs to establish a precondition directly. Keep that test-only authority
    # separate from the executor so assertions still catch accidental direct executor permissions.
    controller.grantRole(controller.MANAGER_ROLE(), admin, {"from": deployer})
    controller.grantRole(controller.UNFREEZER_ROLE(), admin, {"from": deployer})
    controller.grantRole(controller.FREEZER_ROLE(), admin, {"from": deployer})
    guardian_signals.grantRole(guardian_signals.MANAGER_ROLE(), admin, {"from": deployer})
    guardian_signals.grantRole(guardian_signals.ACCESS_RESTORER_ROLE(), admin, {"from": deployer})
    guardian_signals.grantRole(guardian_signals.ACCESS_LIMITER_ROLE(), admin, {"from": deployer})

    owner.setEnforceRoles(True, {"from": deployer})
    controller.setEnforceRoles(True, {"from": deployer})
    guardian_signals.setEnforceRoles(True, {"from": deployer})
    dashboard.setEnforceRoles(True, {"from": deployer})
    morpho.setEnforceRoles(True, {"from": deployer})
    erc4626.setEnforceRoles(True, {"from": deployer})

    return deployment


@pytest.fixture
def admin(lido_lend, accounts):
    "The Lido Lend role admin (Agent), impersonated so tests can set up preconditions directly."
    if len(web3.eth.get_code(lido_lend.admin)) == 0:
        return accounts.at(lido_lend.admin, force=True)
    return _impersonated_account(lido_lend.admin, accounts)


@pytest.fixture
def impersonate(accounts):
    "Return a freshly re-impersonated, funded account after any test snapshot rollback."

    def _impersonate(address):
        return _impersonated_account(address, accounts)

    return _impersonate


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
        executor = et.evmScriptExecutor()
        expected_executor = lido_lend.evm_script_executor
        if expected_executor:
            assert executor.lower() == expected_executor.lower()
        et_admin = _impersonated_account(lido_lend.easy_track_admin, accounts)
        et.grantRole(et.DEFAULT_ADMIN_ROLE(), deployer, {"from": et_admin})

        owner = lido_lend.contract("owner")
        assert owner.hasRole(_role("MARKET_CREATOR_ROLE"), executor)
        assert owner.hasRole(_role("MARKET_MANAGER_ROLE"), executor)
        assert owner.hasRole(_role("GUARDIAN_MANAGER_ROLE"), executor)

        controller = lido_lend.contract("controller")
        guardian_signals = lido_lend.contract("guardianSignals")
        assert controller.hasRole(controller.MANAGER_ROLE(), owner)
        assert controller.hasRole(controller.UNFREEZER_ROLE(), owner)
        assert not controller.hasRole(controller.MANAGER_ROLE(), executor)
        assert not controller.hasRole(controller.UNFREEZER_ROLE(), executor)
        assert guardian_signals.hasRole(guardian_signals.MANAGER_ROLE(), owner)
        assert guardian_signals.hasRole(guardian_signals.ACCESS_RESTORER_ROLE(), owner)
        assert not guardian_signals.hasRole(guardian_signals.MANAGER_ROLE(), executor)
        assert not guardian_signals.hasRole(guardian_signals.ACCESS_RESTORER_ROLE(), executor)
        return et

    # Local mock: a fresh EasyTrack + EVMScriptExecutor the deployer fully controls. The executor receives
    # facade/singleton capabilities only; controller and GuardianSignals roles stay on the facade.
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

    owner = lido_lend.contract("owner")
    owner.grantRole(_role("MARKET_CREATOR_ROLE"), ex, {"from": admin})
    owner.grantRole(_role("MARKET_MANAGER_ROLE"), ex, {"from": admin})
    owner.grantRole(_role("GUARDIAN_MANAGER_ROLE"), ex, {"from": admin})

    dashboard_addr = lido_lend.contracts.get("riskStewardDashboard")
    if dashboard_addr and getattr(dashboard_addr, "address", dashboard_addr) != _ZERO:
        dashboard = lido_lend.contract("riskStewardDashboard")
        dashboard.grantRole(dashboard.STEWARD_ADMIN_ROLE(), ex, {"from": admin})

    for name in ("morphoExitBook", "erc4626ExitBook"):
        exit_book_addr = lido_lend.contracts.get(name)
        if exit_book_addr and getattr(exit_book_addr, "address", exit_book_addr) != _ZERO:
            exit_book = lido_lend.contract(name)
            exit_book.grantRole(exit_book.ALLOWLIST_MANAGER_ROLE(), ex, {"from": admin})

    adaptive_curve_irm = lido_lend.contract("adaptiveCurveIrm")
    if adaptive_curve_irm.manager() != ex:
        adaptive_curve_irm.setManager(ex, {"from": admin})
    irm_router = lido_lend.contract("irmRouter")
    if irm_router.manager() != ex:
        irm_router.setManager(ex, {"from": admin})
    return et


def _market_params(market):
    m = market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _route_curve(lido_lend, market, accounts):
    "Route the market's curve on the router as its current manager (createMarket requires the IRM to be set)."
    router = lido_lend.contract("irmRouter")
    mgr = _impersonated_account(router.manager(), accounts)
    router.setMarketIrm(_market_params(market), market["curve"], {"from": mgr})


def _set_curve_params(lido_lend, market, accounts):
    "Set the market's curve params on the AdaptiveCurveIrm as its current manager (createMarket's borrowRate ping reverts otherwise)."
    curve = lido_lend.contract("adaptiveCurveIrm")
    mgr = _impersonated_account(curve.manager(), accounts)
    curve.setMarketCurveParams(_market_params(market), market["curveParams"], {"from": mgr})


def _ensure_market_created(lido_lend, market, accounts, executor):
    core = lido_lend.contract("core")
    if core.market(market["id"])["lastUpdate"] != 0:
        return
    _set_curve_params(lido_lend, market, accounts)
    _route_curve(lido_lend, market, accounts)
    caller = _impersonated_account(executor, accounts)
    lido_lend.contract("owner").createMarket(
        _market_params(market), market["controller"], False, {"from": caller}
    )


@pytest.fixture
def created_market(lido_lend, easy_track, accounts):
    "Ensure the descriptor market is activated on the core so the domain-scoped factories can resolve `marketController(id)` / `idToMarketParams(id)` / `router.marketIrm(id)`. Mirrors the on-chain activation order: route the IRM curve, then createMarket (which requires the IRM already set)."
    _ensure_market_created(lido_lend, lido_lend.market, accounts, easy_track.evmScriptExecutor())
    return lido_lend


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
