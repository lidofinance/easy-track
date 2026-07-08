import pytest
from eth_abi import encode
from brownie import reverts, LidoLendSetMarketIrm, LidoLendCoreStub, IrmRouterStub, ZERO_ADDRESS

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (2).to_bytes(32, "big")
LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
LLTV = 800000000000000000
EOA = "0x" + "ee" * 20


def create_calldata(market_id, irm):
    return "0x" + encode(["bytes32", "address"], [market_id, str(irm)]).hex()


@pytest.fixture(scope="module")
def router_stub(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def market_params(router_stub):
    return (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router_stub.address, LLTV)


@pytest.fixture(scope="module")
def new_irm(owner):
    return IrmRouterStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def core_stub(owner, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.setMarketParams(MARKET_ID, market_params, {"from": owner})
    return core


@pytest.fixture(scope="module")
def factory(owner, core_stub):
    return LidoLendSetMarketIrm.deploy(owner, core_stub, {"from": owner})


def test_deploy(owner, core_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.lidoLend() == core_stub


def test_create_evm_script_called_by_stranger(stranger, factory, new_irm):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata(MARKET_ID, new_irm))


def test_create_evm_script_zero_irm(owner, factory):
    "Must revert with message 'ZERO_IRM' if the new IRM is the zero address"
    with reverts("ZERO_IRM"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, ZERO_ADDRESS))


def test_create_evm_script_irm_not_contract(owner, factory):
    "Must revert with message 'IRM_NOT_CONTRACT' if the new IRM has no code"
    with reverts("IRM_NOT_CONTRACT"):
        factory.createEVMScript(owner, create_calldata(MARKET_ID, EOA))


def test_create_evm_script_market_not_found(owner, factory, new_irm):
    "Must revert with 'MARKET_NOT_FOUND' if the market was never created on the core (no params.irm)"
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata(UNKNOWN_MARKET_ID, new_irm))


def test_create_evm_script(owner, router_stub, market_params, new_irm, factory):
    "Must create correct EVMScript targeting the market's router when the new IRM is a non-zero contract"
    evm_script = factory.createEVMScript(owner, create_calldata(MARKET_ID, new_irm))
    expected_evm_script = encode_call_script(
        [(router_stub.address, router_stub.setMarketIrm.encode_input(market_params, new_irm))]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, new_irm):
    "Must decode EVMScript call data correctly"
    decoded_market_id, decoded_irm = factory.decodeEVMScriptCallData(create_calldata(MARKET_ID, new_irm))
    assert decoded_market_id == "0x" + MARKET_ID.hex()
    assert decoded_irm == new_irm


def test_target_is_the_shared_router_regardless_of_market_id(owner, new_irm):
    "Unlike the guardian/controller factories, the resolved target here is the domain's shared IrmRouter (`marketParams.irm`), the same for every market — the marketId only selects the payload. So EasyTrack's permission `(router, setMarketIrm)` does NOT scope this factory to a single market; any market's IRM can be re-routed through one registration."
    router = IrmRouterStub.deploy({"from": owner})
    mp_a = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV)
    mp_b = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, router.address, LLTV + 1)
    core = LidoLendCoreStub.deploy({"from": owner})
    market_a, market_b = (1).to_bytes(32, "big"), (2).to_bytes(32, "big")
    core.setMarketParams(market_a, mp_a, {"from": owner})
    core.setMarketParams(market_b, mp_b, {"from": owner})

    factory = LidoLendSetMarketIrm.deploy(owner, core, {"from": owner})
    script_a = factory.createEVMScript(owner, create_calldata(market_a, new_irm))
    script_b = factory.createEVMScript(owner, create_calldata(market_b, new_irm))

    assert script_a == encode_call_script([(router.address, router.setMarketIrm.encode_input(mp_a, new_irm))])
    assert script_b == encode_call_script([(router.address, router.setMarketIrm.encode_input(mp_b, new_irm))])
    assert script_a != script_b
