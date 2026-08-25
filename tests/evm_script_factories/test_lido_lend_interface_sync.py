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
        "accrueInterest((address,address,address,address,uint256))",
        "market(bytes32)",
        "marketController(bytes32)",
        "idToMarketParams(bytes32)",
        "supply((address,address,address,address,uint256),uint256,uint256,address,bytes)",
    ],
    "LidoLendOwner": [
        "createMarket((address,address,address,address,uint256),address,bool)",
        "setFee((address,address,address,address,uint256),uint256)",
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
    ],
    "AdaptiveCurveIrm": [
        "applyIrmConfig((address,address,address,address,uint256),address)",
    ],
    "CircuitBreaker": [
        "registerPauser(address,address)",
    ],
    "LidoLendMarketController": [
        "LIDO_LEND()",
        "marketId()",
        "guardianSignals()",
        "hasInstantActivation(address)",
        "collateralActivationConfig()",
        "settlementConfig()",
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
    ],
    "RiskStewardDashboard": [
        "LIDO_LEND()",
        "addMarketSteward(bytes32,address)",
        "removeMarketSteward(bytes32,address)",
        "isMarketSteward(bytes32,address)",
    ],
    "MorphoExitBook": [
        "setServiceFee(address,uint256)",
        "setMarketAllowed((address,address,address,address,uint256),bool)",
    ],
    "Erc4626ExitBook": [
        "setServiceFee(address,uint256)",
        "setVaultAllowed(address,bool)",
    ],
}

# Struct layouts read by the factories must match ILidoLend.sol field-for-field. Keyed by
# (file, getter) -> expected component types of the returned struct.
_EXPECTED_RETURN_STRUCTS = {
    ("LidoLend", "market"): ["uint128", "uint128", "uint128", "uint128", "uint128", "uint128"],
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
def test_factory_read_struct_layout(abi_name, getter, expected_components):
    "Struct fields read by factories must match ILidoLend.sol, including flattened public mapping getters."
    fns = [e for e in _load_abi(abi_name) if e.get("type") == "function" and e["name"] == getter]
    assert fns, f"{getter} missing from interfaces/{abi_name}.json"
    outputs = fns[0]["outputs"]
    components = outputs[0]["components"] if len(outputs) == 1 and outputs[0]["type"].startswith("tuple") else outputs
    actual = [_canon_type(c) for c in components]
    assert actual == expected_components, f"{getter} struct layout drifted: {actual} != {expected_components}"
