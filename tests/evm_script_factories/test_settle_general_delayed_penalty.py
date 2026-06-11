from typing import NamedTuple

import pytest
from brownie import AccountingStub, BaseModuleStub, SettleGeneralDelayedPenalty, reverts

from utils.evm_script import encode_call_script, encode_calldata

FACTORY_NAME = "CSM v3"

LOCKED_BOND_NO_ID = 0
LOCKED_BOND_AMOUNT = 1000
LOCKED_BOND_UNTIL = 123456


def create_calldata(lock_info_list):
    return encode_calldata(["(uint256,uint256,uint256)[]"], [lock_info_list])


class LockInfo(NamedTuple):
    node_operator_id: int = LOCKED_BOND_NO_ID
    max_amount: int = LOCKED_BOND_AMOUNT
    until: int = LOCKED_BOND_UNTIL


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
def fill_module(accounting, owner):
    accounting.mock_setLockedBondInfo(LOCKED_BOND_NO_ID, LOCKED_BOND_AMOUNT, LOCKED_BOND_UNTIL, {"from": owner})


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


def test_non_sorted_calldata(owner, factory):
    "Must revert with message 'NODE_OPERATORS_OUT_OF_ORDER' when operator ids are out of order"
    with reverts("NODE_OPERATORS_OUT_OF_ORDER"):
        NON_SORTED_CALLDATA = create_calldata([LockInfo(1, 1, 0), LockInfo(0, 1, 0)])
        factory.createEVMScript(owner, NON_SORTED_CALLDATA)

    with reverts("NODE_OPERATORS_OUT_OF_ORDER"):
        NON_SORTED_CALLDATA = create_calldata([LockInfo(0, 1, 0), LockInfo(0, 1, 0)])
        factory.createEVMScript(owner, NON_SORTED_CALLDATA)


def test_operator_id_out_of_range(owner, factory, module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"
    node_operators_count = module.getNodeOperatorsCount()
    CALLDATA = create_calldata([LockInfo(node_operators_count, 1, 0)])
    with reverts("OUT_OF_RANGE_NODE_OPERATOR_ID"):
        factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, factory, module, fill_module):
    "Must create correct EVMScript if all requirements are met"
    lock = LockInfo(LOCKED_BOND_NO_ID, LOCKED_BOND_AMOUNT, LOCKED_BOND_UNTIL)
    node_operator_ids = [lock.node_operator_id]
    max_amounts = [lock.max_amount]

    EVM_SCRIPT_CALLDATA = create_calldata([lock])
    evm_script = factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(module.address, module.settleGeneralDelayedPenalty.encode_input(node_operator_ids, max_amounts))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    lock_info_list = [
        LockInfo(0, 1000, 100),
        LockInfo(1, 2000, 200),
        LockInfo(2, 3000, 300),
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


def test_max_amount_should_be_greater_than_zero(owner, factory, fill_module):
    "Must revert with message 'MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO' when max amount is zero"
    CALLDATA = create_calldata([LockInfo(max_amount=0)])
    with reverts("MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO"):
        factory.createEVMScript(owner, CALLDATA)


def test_max_amount_should_be_greater_than_actual_locked(owner, factory, fill_module):
    "Must revert when max amount is less than actual locked"
    CALLDATA = create_calldata([LockInfo(max_amount=LOCKED_BOND_AMOUNT - 1)])
    with reverts("MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED"):
        factory.createEVMScript(owner, CALLDATA)


def test_reverts_if_lock_until_changed(owner, factory, fill_module):
    CALLDATA = create_calldata([LockInfo(until=LOCKED_BOND_UNTIL + 1)])
    with reverts("OUTDATED_LOCK_SETTLE"):
        factory.createEVMScript(owner, CALLDATA)
