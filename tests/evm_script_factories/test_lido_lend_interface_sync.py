"""Guards against drift between the hand-redeclared `contracts/interfaces/ILidoLend.sol` and the committed
deployed ABIs in `interfaces/*.json`. The factories build calldata from selectors/struct layouts declared in
ILidoLend.sol; if the real protocol renames a method, changes a parameter type, or reorders a struct field,
the redeclared interface silently diverges and the produced EVMScript would call a wrong/nonexistent method.
This runs in plain CI (no fork) — it only reads the committed ABI JSON.
"""

import json
import os

import pytest

_INTERFACES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "interfaces")

# Canonical input signatures every Lido Lend factory relies on, grouped by committed ABI file.
# UDVTs (Id) and interface-typed params (IIrm, IERC4626) appear as their ABI base types (bytes32/address);
# MarketParams / config structs appear as fully-expanded tuples — matching what the factories abi.encode.
_EXPECTED_SIGNATURES = {
    "LidoLend": [
        "marketController(bytes32)",
        "idToMarketParams(bytes32)",
    ],
    "LidoLendOwner": [
        "createMarket((address,address,address,address,uint256),address,bool)",
        "setMarketSupplyCap(bytes32,uint256)",
        "unfreezeMarket(bytes32)",
        "setMarketCollateralActivationConfig(bytes32,(uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40))",
        "setMarketSettlementConfig(bytes32,(uint16,uint96,uint96,uint16))",
        "setInstantActivation(bytes32,address,bool)",
        "addGuardian(bytes32,address)",
        "replaceGuardian(bytes32,address,address)",
        "removeGuardian(bytes32,address)",
        "setGuardiansQuorum(bytes32,uint256)",
        "setGuardiansSuspectWindow(bytes32,uint256)",
        "unbanGuardianSignals(bytes32[],address)",
    ],
    "IrmRouter": [
        "setMarketIrm((address,address,address,address,uint256),address)",
        "marketIrm(bytes32)",
    ],
    "AdaptiveCurveIrm": [
        "applyIrmConfig((address,address,address,address,uint256),address)",
    ],
    "CircuitBreaker": [
        "registerPauser(address,address)",
    ],
    "LidoLendMarketController": [
        "marketId()",
        "guardianSignals()",
        "setInstantActivation(address,bool)",
        "hasInstantActivation(address)",
        "setCollateralActivationConfig((uint40,uint40,uint128,uint128,uint40,uint128,uint40,uint40,uint40))",
        "collateralActivationConfig()",
        "setSettlementConfig((uint16,uint96,uint96,uint16))",
        "settlementConfig()",
        "setSupplyCap(uint256)",
        "supplyCap()",
        "unfreeze()",
        "isFrozen()",
    ],
    "GuardianSignals": [
        "addGuardian(address)",
        "removeGuardian(address)",
        "setQuorum(uint256)",
        "getQuorum()",
        "getGuardianCount()",
        "setSuspectWindow(uint256)",
        "getSuspectWindow()",
        "isGuardian(address)",
        "unban(bytes32,address)",
        "isBanned(bytes32,address)",
    ],
    "RiskStewardDashboard": [
        "addMarketSteward(bytes32,address)",
        "removeMarketSteward(bytes32,address)",
        "isMarketSteward(bytes32,address)",
    ],
    "MorphoExitBook": [
        "setMarketAllowed((address,address,address,address,uint256),bool)",
    ],
    "Erc4626ExitBook": [
        "setVaultAllowed(address,bool)",
    ],
}

# The two configs the factories re-encode and compare by keccak against the on-chain getter's return value:
# the getter's returned struct layout must match ILidoLend.sol field-for-field, else the SAME_CONFIG guard
# silently misbehaves. Keyed by (file, getter) -> expected component types of the returned struct.
_EXPECTED_RETURN_STRUCTS = {
    ("LidoLendMarketController", "collateralActivationConfig"): [
        "uint40",
        "uint40",
        "uint128",
        "uint128",
        "uint40",
        "uint128",
        "uint40",
        "uint40",
        "uint40",
    ],
    ("LidoLendMarketController", "settlementConfig"): ["uint16", "uint96", "uint96", "uint16"],
}


def _load_abi(name):
    with open(os.path.join(_INTERFACES_DIR, name + ".json")) as f:
        data = json.load(f)
    return data["abi"] if isinstance(data, dict) and "abi" in data else data


def _canon_type(component):
    "ABI type string, expanding tuples recursively (e.g. tuple[] -> (t1,t2)[])."
    t = component["type"]
    if t.startswith("tuple"):
        inner = ",".join(_canon_type(c) for c in component["components"])
        return "(" + inner + ")" + t[len("tuple") :]
    return t


def _input_signature(entry):
    return entry["name"] + "(" + ",".join(_canon_type(i) for i in entry["inputs"]) + ")"


@pytest.mark.parametrize(
    "abi_name,signature",
    [(name, sig) for name, sigs in _EXPECTED_SIGNATURES.items() for sig in sigs],
)
def test_factory_called_method_exists_in_deployed_abi(abi_name, signature):
    "Every method the factories call must exist with the exact input signature in the committed ABI."
    present = {_input_signature(e) for e in _load_abi(abi_name) if e.get("type") == "function"}
    assert signature in present, f"{signature} missing from interfaces/{abi_name}.json; ILidoLend.sol drifted"


@pytest.mark.parametrize(
    "abi_name,getter,expected_components",
    [(f, g, comps) for (f, g), comps in _EXPECTED_RETURN_STRUCTS.items()],
)
def test_config_getter_return_struct_layout(abi_name, getter, expected_components):
    "The config getters return a struct whose field layout must match ILidoLend.sol (keccak-compared by factories)."
    fns = [e for e in _load_abi(abi_name) if e.get("type") == "function" and e["name"] == getter]
    assert fns, f"{getter} missing from interfaces/{abi_name}.json"
    outputs = fns[0]["outputs"]
    assert len(outputs) == 1 and outputs[0]["type"].startswith("tuple"), f"{getter} must return a single struct"
    actual = [_canon_type(c) for c in outputs[0]["components"]]
    assert actual == expected_components, f"{getter} struct layout drifted: {actual} != {expected_components}"
