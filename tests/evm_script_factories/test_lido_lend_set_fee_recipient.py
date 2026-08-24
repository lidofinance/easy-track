import pytest
from brownie import LidoLendCoreStub, LidoLendOwnerStub, LidoLendSetFeeRecipient, reverts
from eth_abi import encode

from utils.evm_script import encode_call_script

MARKET_ID = (1).to_bytes(32, "big")
SECOND_MARKET_ID = (2).to_bytes(32, "big")
UNKNOWN_MARKET_ID = (3).to_bytes(32, "big")


def create_calldata(market_ids, new_fee_recipient):
    return "0x" + encode(["bytes32[]", "address"], [market_ids, str(new_fee_recipient)]).hex()


@pytest.fixture(scope="module")
def market_params(owner, stranger):
    return (owner.address, stranger.address, owner.address, stranger.address, 8 * 10**17)


@pytest.fixture(scope="module")
def second_market_params(owner, stranger):
    return (stranger.address, owner.address, stranger.address, owner.address, 7 * 10**17)


@pytest.fixture(scope="module")
def core_stub(owner, market_params, second_market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.activateMarket(MARKET_ID, market_params, False, {"from": owner})
    core.activateMarket(SECOND_MARKET_ID, second_market_params, False, {"from": owner})
    return core


@pytest.fixture(scope="module")
def owner_facade(owner, core_stub):
    facade = LidoLendOwnerStub.deploy({"from": owner})
    facade.setCore(core_stub, {"from": owner})
    core_stub.setOwner(facade, {"from": owner})
    return facade


@pytest.fixture(scope="module")
def factory(owner, owner_facade):
    return LidoLendSetFeeRecipient.deploy(owner, owner_facade, {"from": owner})


def test_deploy(owner, owner_facade, factory):
    assert factory.trustedCaller() == owner
    assert factory.lidoLendOwner() == owner_facade


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, create_calldata([MARKET_ID], stranger))


def test_create_evm_script_empty_market_ids(owner, stranger, factory):
    with reverts("EMPTY_MARKETS_LIST"):
        factory.createEVMScript(owner, create_calldata([], stranger))


def test_create_evm_script_market_not_found(owner, stranger, factory):
    with reverts("MARKET_NOT_FOUND"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID, UNKNOWN_MARKET_ID], stranger))


def test_create_evm_script_fee_recipient_already_set(owner, factory):
    with reverts("FEE_RECIPIENT_ALREADY_SET"):
        factory.createEVMScript(owner, create_calldata([MARKET_ID], "0x0000000000000000000000000000000000000000"))


def test_create_evm_script_accrues_every_market_before_recipient_change(
    owner,
    stranger,
    core_stub,
    owner_facade,
    market_params,
    second_market_params,
    factory,
):
    evm_script = factory.createEVMScript(
        owner,
        create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger),
    )

    assert evm_script == encode_call_script(
        [
            (core_stub.address, core_stub.accrueInterest.encode_input(market_params)),
            (core_stub.address, core_stub.accrueInterest.encode_input(second_market_params)),
            (owner_facade.address, owner_facade.setFeeRecipient.encode_input(stranger)),
        ]
    )


def test_decode_evm_script_call_data(stranger, factory):
    decoded_market_ids, decoded_recipient = factory.decodeEVMScriptCallData(
        create_calldata([MARKET_ID, SECOND_MARKET_ID], stranger)
    )
    assert decoded_market_ids == ["0x" + MARKET_ID.hex(), "0x" + SECOND_MARKET_ID.hex()]
    assert decoded_recipient == stranger
