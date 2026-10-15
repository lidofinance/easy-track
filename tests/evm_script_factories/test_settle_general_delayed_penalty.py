from typing import NamedTuple

import pytest
from brownie import AccountingStub, BaseModuleStub, SettleGeneralDelayedPenalty, Wei, reverts

from utils.evm_script import encode_call_script, encode_calldata

FACTORY_NAME = "CSM v3"
LOCK_NONCE = 42;


def create_calldata(lock_info_list):
    return encode_calldata(["(uint256,uint256)[]"], [lock_info_list])


class LockInfo(NamedTuple):
    no_id: int
    nonce: int = LOCK_NONCE


@pytest.fixture(scope="module")
def accounting(owner):
    return owner.deploy(AccountingStub)


@pytest.fixture(scope="module")
def module(owner, accounting):
    module = owner.deploy(BaseModuleStub)
    module.mock_setNodeOperatorsCount(1000, {"from": owner})
    module.mock_setAccounting(accounting.address, {"from": owner})
    return module


@pytest.fixture(scope="module")
def factory(owner, module):
    return SettleGeneralDelayedPenalty.deploy(owner, FACTORY_NAME, module, {"from": owner})


@pytest.fixture()
def lock_bond(request, accounting, owner):
    for no_id in request.param:
        accounting.mock_setLock(no_id, Wei(1), LOCK_NONCE, {"from": owner})


def test_deploy(owner, module, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.module() == module
    assert factory.name() == FACTORY_NAME


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, factory):
    EMPTY_CALLDATA = create_calldata([])
    with reverts("EMPTY_LOCK_INFO_LIST"):
        factory.createEVMScript(owner, EMPTY_CALLDATA)


@pytest.mark.parametrize('lock_bond', [(0, 1)], indirect=True)
@pytest.mark.usefixtures('lock_bond')
def test_non_sorted_calldata(owner, factory):
    "Must revert with message 'NODE_OPERATORS_OUT_OF_ORDER' when operator ids are out of order"

    with reverts("NODE_OPERATORS_OUT_OF_ORDER"):
        NON_SORTED_CALLDATA = create_calldata([LockInfo(no_id=1), LockInfo(no_id=0)])
        factory.createEVMScript(owner, NON_SORTED_CALLDATA)

    with reverts("NODE_OPERATORS_OUT_OF_ORDER"):
        NON_SORTED_CALLDATA = create_calldata([LockInfo(no_id=0), LockInfo(no_id=0)])
        factory.createEVMScript(owner, NON_SORTED_CALLDATA)


def test_operator_id_out_of_range(owner, factory, module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"
    node_operators_count = module.getNodeOperatorsCount()
    CALLDATA = create_calldata([LockInfo(node_operators_count, LOCK_NONCE)])
    with reverts("OUT_OF_RANGE_NODE_OPERATOR_ID"):
        factory.createEVMScript(owner, CALLDATA)


@pytest.mark.parametrize('lock_bond', [(0,)], indirect=True)
@pytest.mark.usefixtures('lock_bond')
def test_create_evm_script(owner, factory, module):
    "Must create correct EVMScript if all requirements are met"
    lock = LockInfo(0, LOCK_NONCE)
    node_operator_ids = [lock.no_id]
    nonces = [lock.nonce]

    EVM_SCRIPT_CALLDATA = create_calldata([lock])
    evm_script = factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(module.address, module.settleGeneralDelayedPenalty.encode_input(node_operator_ids, nonces))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    lock_info_list = [
        LockInfo(0, 1000),
        LockInfo(1, 2000),
        LockInfo(2, 3000),
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(lock_info_list)
    decoded_lock_info_list = factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_lock_info_list == lock_info_list


@pytest.mark.parametrize("invalid_calldata", ["0x", "0x01"], ids=["empty", "malformed"])
def test_decode_evm_script_call_data_reverts_on_invalid_calldata(
    factory, invalid_calldata
):
    with reverts():
        factory.decodeEVMScriptCallData(invalid_calldata)


def test_lock_should_be_greater_than_zero(owner, factory):
    "Must revert with message 'NO_LOCK_TO_SETTLE' when locked amount is zero"
    CALLDATA = create_calldata([LockInfo(0)])
    with reverts("NO_LOCK_TO_SETTLE"):
        factory.createEVMScript(owner, CALLDATA)


@pytest.mark.parametrize('lock_bond', [(0,)], indirect=True)
@pytest.mark.usefixtures('lock_bond')
def test_lock_should_have_expected_nonce(owner, factory):
    "Must revert with message 'INVALID_LOCK_NONCE' when nonce mismatches"
    CALLDATA = create_calldata([LockInfo(0, LOCK_NONCE - 1)])
    with reverts("INVALID_LOCK_NONCE"):
        factory.createEVMScript(owner, CALLDATA)

    CALLDATA = create_calldata([LockInfo(0, LOCK_NONCE + 1)])
    with reverts("INVALID_LOCK_NONCE"):
        factory.createEVMScript(owner, CALLDATA)
