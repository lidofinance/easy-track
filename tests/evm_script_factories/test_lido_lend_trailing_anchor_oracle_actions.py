"""Unit tests for LidoLendTrailingAnchorOracleActions.

The expected values come from the rules of the Trailing Anchor Oracle in lido-lend-markets. They do not come
from the factory code.
"""

import pytest
from brownie import (
    LidoLendTrailingAnchorOracleActions,
    TrailingAnchorOracleAdapterStub,
    TrailingAnchorOracleStub,
    ZERO_ADDRESS,
    chain,
    interface,
    reverts,
    web3,
)
from eth_abi import encode

from utils.evm_script import encode_call_script
from utils.hardhat_helpers import get_last_tx_revert_reason

SET_PARAMETERS = 0
SET_PRICING_RESUMES_AT = 1

WAD = 10**18
HOUR = 60 * 60
DAY = 24 * HOUR

PARAMETERS_ABI_TYPE = "(uint64,uint64,uint64,uint64,uint64,uint64,uint40,uint40)"
# The fields of the oracle `Parameters` struct, in the order of the struct, with the default values of the spec.
DEFAULT_PARAMETERS = {
    "maxPriceAboveAnchor": 5 * 10**14,  # 0.05%
    "maxPriceBelowAnchor": 10**15,  # 0.1%
    "maxAnchorContinuousRiseRate": 6 * 10**16,  # 6% a year
    "maxAnchorContinuousFallRate": 10**16,  # 1% a year
    "maxAnchorBelowBase": 10**16,  # 1%
    "maxAnchorAboveBase": 2 * 10**15,  # 0.2%
    "reanchorDelay": 6 * HOUR,
    "reanchorWindow": DAY,
}


def parameters(**overrides):
    return tuple({**DEFAULT_PARAMETERS, **overrides}.values())


def set_parameters_calldata(oracle, params):
    payload = encode(["address", PARAMETERS_ABI_TYPE], [str(oracle), params])
    return "0x" + encode(["uint8", "bytes"], [SET_PARAMETERS, payload]).hex()


def set_pricing_resumes_at_calldata(oracle, resumes_at):
    payload = encode(["address", "uint40"], [str(oracle), resumes_at])
    return "0x" + encode(["uint8", "bytes"], [SET_PRICING_RESUMES_AT, payload]).hex()


def create_set_parameters_script(factory, creator, oracle, params):
    return factory.createEVMScript(creator, set_parameters_calldata(oracle, params))


def create_set_pricing_resumes_at_script(factory, creator, oracle, resumes_at):
    return factory.createEVMScript(creator, set_pricing_resumes_at_calldata(oracle, resumes_at))


def create_set_pricing_resumes_at_script_at(factory, creator, oracle, resumes_at, block_time):
    """Creates the script in a transaction, so that the checks run in a block with exactly `block_time`.

    The fixed gas limit skips the gas estimate, because the estimate runs at a different block time.
    """
    response = web3.provider.make_request("evm_setNextBlockTimestamp", [block_time])
    assert not response.get("error"), response
    calldata = set_pricing_resumes_at_calldata(oracle, resumes_at)
    return factory.createEVMScript.transact(creator, calldata, {"from": creator, "gas_limit": 1_000_000})


def expected_set_parameters_script(adapter, oracle, params):
    return encode_call_script([(adapter.address, adapter.setParameters.encode_input(oracle, params))])


def expected_set_pricing_resumes_at_script(adapter, oracle, resumes_at):
    return encode_call_script([(adapter.address, adapter.setPricingResumesAt.encode_input(oracle, resumes_at))])


@pytest.fixture(scope="module")
def executor(accounts):
    return accounts[7]


@pytest.fixture(scope="module")
def adapter(owner):
    return TrailingAnchorOracleAdapterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def oracle(owner, adapter):
    oracle = TrailingAnchorOracleStub.deploy({"from": owner})
    oracle.grantRole(oracle.MANAGER_ROLE(), adapter, {"from": owner})
    # The owner sets the current parameters of the oracle in the tests.
    oracle.grantRole(oracle.MANAGER_ROLE(), owner, {"from": owner})
    return oracle


@pytest.fixture(scope="module")
def unmanaged_oracle(owner):
    return TrailingAnchorOracleStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def factory(owner, adapter):
    return LidoLendTrailingAnchorOracleActions.deploy(owner, adapter, {"from": owner})


def test_deploy(owner, adapter, factory):
    assert factory.trustedCaller() == owner
    assert factory.adapter() == adapter


def test_deploy_rejects_zero_adapter(owner):
    # Brownie cannot build the trace of a reverted deployment on Hardhat, so the reason is read from the node.
    try:
        with reverts("ZERO_ADAPTER"):
            LidoLendTrailingAnchorOracleActions.deploy(owner, ZERO_ADDRESS, {"from": owner})
    except Exception as error:
        if get_last_tx_revert_reason() != "ZERO_ADAPTER":
            raise error


def test_create_evm_script_called_by_stranger(stranger, oracle, factory):
    "Must revert if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        create_set_parameters_script(factory, stranger, oracle, parameters())
    with reverts("CALLER_IS_FORBIDDEN"):
        create_set_pricing_resumes_at_script(factory, stranger, oracle, 0)


def test_rejects_unknown_action(owner, factory):
    calldata = "0x" + encode(["uint8", "bytes"], [255, b""]).hex()
    with reverts():
        factory.createEVMScript(owner, calldata)


def test_stub_and_factory_match_the_oracle_abi():
    "The stub and the factory must use the names, the types and the selectors of the real oracle"
    oracle_interface = interface.TrailingAnchorOracle
    for name, selector in TrailingAnchorOracleStub.signatures.items():
        if name in ("grantRole", "revokeRole"):
            # Test helpers of the stub. The real oracle has these names with its own access rules.
            continue
        assert oracle_interface.selectors.get(selector) == name

    decoder = next(e for e in LidoLendTrailingAnchorOracleActions.abi if e.get("name") == "decodeSetParametersPayload")
    setter = next(e for e in oracle_interface.abi if e.get("name") == "setParameters")
    assert [(c["name"], c["type"]) for c in decoder["outputs"][1]["components"]] == [
        (c["name"], c["type"]) for c in setter["inputs"][0]["components"]
    ]


@pytest.mark.parametrize(
    "calldata_for",
    [
        lambda oracle: set_parameters_calldata(oracle, parameters()),
        lambda oracle: set_pricing_resumes_at_calldata(oracle, 0),
    ],
)
def test_rejects_an_oracle_that_the_adapter_does_not_manage(owner, unmanaged_oracle, factory, calldata_for):
    "Must reject the motion while the adapter does not hold MANAGER_ROLE on the oracle"
    with reverts("ORACLE_NOT_MANAGED"):
        factory.createEVMScript(owner, calldata_for(unmanaged_oracle))


@pytest.mark.parametrize(
    "calldata_for",
    [
        lambda oracle: set_parameters_calldata(oracle, parameters()),
        lambda oracle: set_pricing_resumes_at_calldata(oracle, 0),
    ],
)
def test_rejects_a_zero_oracle(owner, factory, calldata_for):
    with reverts("ZERO_ORACLE"):
        factory.createEVMScript(owner, calldata_for(ZERO_ADDRESS))


# -------------
# SetParameters
# -------------


def test_create_set_parameters_evm_script(owner, adapter, oracle, factory):
    "Must create one call to the adapter with the oracle and the supplied parameters"
    params = parameters()
    script = create_set_parameters_script(factory, owner, oracle, params)
    assert script == expected_set_parameters_script(adapter, oracle, params)


def test_set_parameters_script_changes_the_oracle_through_the_adapter(owner, adapter, oracle, factory, executor):
    "The call in the script, sent by the executor, stores the parameters in the oracle"
    params = parameters(reanchorDelay=12 * HOUR)
    create_set_parameters_script(factory, owner, oracle, params)
    adapter.setParameters(oracle, params, {"from": executor})
    assert oracle.reanchorDelay() == 12 * HOUR


@pytest.mark.parametrize(
    "overrides,error",
    [
        ({"maxPriceAboveAnchor": 0}, "MAX_PRICE_ABOVE_ANCHOR_IS_ZERO"),
        ({"maxPriceBelowAnchor": 0}, "MAX_PRICE_BELOW_ANCHOR_IS_ZERO"),
        ({"maxPriceAboveAnchor": WAD}, "MAX_PRICE_ABOVE_ANCHOR_NOT_BELOW_WAD"),
        ({"maxPriceBelowAnchor": WAD}, "MAX_PRICE_BELOW_ANCHOR_NOT_BELOW_WAD"),
        ({"maxAnchorBelowBase": WAD}, "MAX_ANCHOR_BELOW_BASE_NOT_BELOW_WAD"),
        ({"maxAnchorAboveBase": WAD}, "MAX_ANCHOR_ABOVE_BASE_NOT_BELOW_WAD"),
        ({"maxAnchorContinuousRiseRate": WAD + 1}, "MAX_ANCHOR_CONTINUOUS_RISE_RATE_EXCEEDS_WAD"),
        ({"maxAnchorContinuousFallRate": WAD + 1}, "MAX_ANCHOR_CONTINUOUS_FALL_RATE_EXCEEDS_WAD"),
        ({"reanchorDelay": HOUR - 1}, "REANCHOR_DELAY_BELOW_MIN_REANCHOR_DELAY"),
        ({"reanchorWindow": HOUR - 1}, "REANCHOR_WINDOW_BELOW_MIN_REANCHOR_WINDOW"),
    ],
)
def test_set_parameters_rejects_value_out_of_range(owner, oracle, factory, overrides, error):
    "Must reject each value that the oracle refuses, with the error of that value"
    with reverts(error):
        create_set_parameters_script(factory, owner, oracle, parameters(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        # Over one hour, a rate of 100% a year moves the price by about 0.0114%. Both default bounds are larger.
        {"maxAnchorContinuousRiseRate": WAD, "maxAnchorContinuousFallRate": WAD, "reanchorDelay": HOUR},
        {"reanchorWindow": HOUR},
        {"maxAnchorContinuousRiseRate": 0, "maxAnchorContinuousFallRate": 0},
        {"maxAnchorBelowBase": 0, "maxAnchorAboveBase": 0},
        # The factory does not check the sizing rule. Bounds near a whole price pass the range checks.
        {"maxPriceAboveAnchor": WAD - 1, "maxPriceBelowAnchor": WAD - 1},
    ],
)
def test_set_parameters_accepts_values_on_the_edge_of_the_range(owner, adapter, oracle, factory, overrides):
    "Must accept the largest rates, the shortest delay and window, zero rates, a zero floor and ceiling, and wide bounds"
    params = parameters(**overrides)
    script = create_set_parameters_script(factory, owner, oracle, params)
    assert script == expected_set_parameters_script(adapter, oracle, params)


def test_set_parameters_rise_over_one_delay_edge(owner, adapter, oracle, factory):
    """A source that rises at the rise rate for one delay must stay inside the upper bound.

    The rise is x + x^2/2 + x^3/6 for x = rate * delay / 365 days, in WAD, with each term rounded down.
    At 8.76% a year and a one-hour delay, x is 0.00001, and the rise is 1e13 + 5e7 + 166.
    """
    overrides = {"maxAnchorContinuousRiseRate": 876 * 10**14, "reanchorDelay": HOUR}
    accepted = parameters(maxPriceAboveAnchor=10_000_050_000_166, **overrides)
    refused = parameters(maxPriceAboveAnchor=10_000_050_000_165, **overrides)

    script = create_set_parameters_script(factory, owner, oracle, accepted)
    assert script == expected_set_parameters_script(adapter, oracle, accepted)
    with reverts("RISE_OVER_DELAY_EXCEEDS_MAX_PRICE_ABOVE_ANCHOR"):
        create_set_parameters_script(factory, owner, oracle, refused)


def test_set_parameters_fall_over_one_delay_edge(owner, adapter, oracle, factory):
    """A source that falls at the fall rate for one delay must stay inside the lower bound.

    The fall is c / (1 + c), rounded down, with c from the rise formula. With the default 0.1% lower bound and
    a 48-hour delay, the largest fall rate is -ln(0.999) * 365 days / 48 hours, about 18.2591% a year.
    The rise rate is zero, so only the fall rule decides.
    """
    overrides = {"maxAnchorContinuousRiseRate": 0, "reanchorDelay": 48 * HOUR}
    accepted = parameters(maxAnchorContinuousFallRate=182_591_310_886_608_672, **overrides)
    refused = parameters(maxAnchorContinuousFallRate=182_591_310_886_608_673, **overrides)

    script = create_set_parameters_script(factory, owner, oracle, accepted)
    assert script == expected_set_parameters_script(adapter, oracle, accepted)
    with reverts("FALL_OVER_DELAY_EXCEEDS_MAX_PRICE_BELOW_ANCHOR"):
        create_set_parameters_script(factory, owner, oracle, refused)


def test_set_parameters_rejects_the_current_parameters(owner, oracle, factory):
    "A motion with the current values of the oracle would only drop its pending anchor"
    params = parameters()
    oracle.setParameters(params, {"from": owner})
    with reverts("SAME_PARAMETERS"):
        create_set_parameters_script(factory, owner, oracle, params)


@pytest.mark.parametrize("field", list(DEFAULT_PARAMETERS))
def test_set_parameters_accepts_a_change_of_one_field(owner, adapter, oracle, factory, field):
    "A difference in any one of the eight fields is a change"
    params = parameters()
    oracle.setParameters(parameters(**{field: DEFAULT_PARAMETERS[field] + 1}), {"from": owner})
    script = create_set_parameters_script(factory, owner, oracle, params)
    assert script == expected_set_parameters_script(adapter, oracle, params)


def test_decode_set_parameters_payload(oracle, factory):
    params = parameters()
    action, payload = factory.decodeEVMScriptCallData(set_parameters_calldata(oracle, params))
    assert action == SET_PARAMETERS
    assert factory.decodeSetParametersPayload(payload) == (oracle.address, params)


# -------------------
# SetPricingResumesAt
# -------------------


def test_create_set_pricing_resumes_at_evm_script(owner, adapter, oracle, factory):
    "Must create one call to the adapter with the oracle and the supplied time"
    resumes_at = chain[-1].timestamp + DAY
    script = create_set_pricing_resumes_at_script(factory, owner, oracle, resumes_at)
    assert script == expected_set_pricing_resumes_at_script(adapter, oracle, resumes_at)


def test_set_pricing_resumes_at_zero_ends_the_suspension(owner, adapter, oracle, factory):
    "Zero is the only value that ends a suspension"
    script = create_set_pricing_resumes_at_script(factory, owner, oracle, 0)
    assert script == expected_set_pricing_resumes_at_script(adapter, oracle, 0)


def test_set_pricing_resumes_at_rejects_a_time_that_is_not_in_the_future(owner, oracle, factory):
    """Anyone can enact a motion at any time after it passes.

    A suspension motion that is enacted after its end time would end a newer suspension. Thus the factory
    refuses each time that is not after the time of the block, except zero.
    """
    block_time = chain[-1].timestamp + HOUR

    create_set_pricing_resumes_at_script_at(factory, owner, oracle, block_time + 1, block_time)
    with reverts("PRICING_RESUMES_AT_NOT_IN_FUTURE"):
        create_set_pricing_resumes_at_script_at(factory, owner, oracle, block_time + 1, block_time + 1)
    with reverts("PRICING_RESUMES_AT_NOT_IN_FUTURE"):
        create_set_pricing_resumes_at_script_at(factory, owner, oracle, 1, block_time + 2)


def test_set_pricing_resumes_at_suspension_limit(owner, oracle, factory):
    "One call can suspend pricing for at most 7 days from the time of the block"
    block_time = chain[-1].timestamp + HOUR

    create_set_pricing_resumes_at_script_at(factory, owner, oracle, block_time + 7 * DAY, block_time)
    with reverts("INVALID_PRICING_RESUMES_AT"):
        create_set_pricing_resumes_at_script_at(factory, owner, oracle, block_time + 1 + 7 * DAY + 1, block_time + 1)


def test_decode_set_pricing_resumes_at_payload(oracle, factory):
    calldata = set_pricing_resumes_at_calldata(oracle, 1_800_000_000)
    action, payload = factory.decodeEVMScriptCallData(calldata)
    assert action == SET_PRICING_RESUMES_AT
    assert factory.decodeSetPricingResumesAtPayload(payload) == (oracle.address, 1_800_000_000)
