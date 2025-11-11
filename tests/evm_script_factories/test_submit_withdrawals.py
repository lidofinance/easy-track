from collections import namedtuple
from typing import Iterable

import pytest
from brownie import (
    CSLikeModuleStub,
    SubmitWithdrawals,
    reverts,
)

from utils.evm_script import encode_call_script, encode_calldata

ValidatorWithdrawalInfo = namedtuple(
    "ValidatorWithdrawalInfo",
    [
        "no_id",
        "key_index",
        "exit_balance",
        "slashing_penalty",
    ],
)


def create_calldata(values: Iterable[ValidatorWithdrawalInfo]):
    return encode_calldata("(uint256,uint256,uint256,uint256)[]", [values])


@pytest.fixture(scope="module")
def module(owner):
    module = owner.deploy(CSLikeModuleStub)
    module.mock_setNodeOperatorsCount(1000)
    return module


@pytest.fixture(scope="module")
def factory(owner, module):
    return SubmitWithdrawals.deploy(
        owner,
        module,
        {"from": owner},
    )


def test_deploy(owner, module, factory):
    assert factory.trustedCaller() == owner
    assert factory.module() == module


def test_create_evm_script_reverts_if_called_by_stranger(stranger, factory):
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_create_evm_script_reverts_if_empty_withdrawal_list(owner, factory):
    EVM_SCRIPT_CALLDATA = create_calldata([])
    with reverts("EMPTY_WITHDRAWAL_LIST"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=0,
                    slashing_penalty=1,
                ),
            ]
        ),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
                ValidatorWithdrawalInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=0,
                    slashing_penalty=1,
                ),
            ]
        ),
    ],
)
def test_create_evm_script_reverts_if_zero_exit_balance(owner, factory, values):
    EVM_SCRIPT_CALLDATA = create_calldata(values)
    with reverts("ZERO_EXIT_BALANCE"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=1001,
                    key_index=1,
                    exit_balance=1,
                    slashing_penalty=1,
                ),
            ]
        ),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
                ValidatorWithdrawalInfo(
                    no_id=1001,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                ),
            ]
        ),
    ],
)
def test_create_evm_script_reverts_if_non_existing_operator(owner, factory, values):
    EVM_SCRIPT_CALLDATA = create_calldata(values)
    with reverts("OPERATOR_DOES_NOT_EXIST"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
            ],
        ),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
                ValidatorWithdrawalInfo(
                    no_id=1,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                ),
            ]
        ),
    ],
)
def test_create_evm_script(owner, factory, module, values):
    """Must create correct EVMScript if all requirements are met"""

    EVM_SCRIPT_CALLDATA = create_calldata(values)
    evm_script = factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [
            (
                module.address,
                module.submitWithdrawals.encode_input(values),
            )
        ]
    )

    assert evm_script == expected_evm_script


@pytest.mark.parametrize(
    "values",
    [
        pytest.param([]),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=0,
                    slashing_penalty=0,
                ),
            ]
        ),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=1,
                    key_index=2,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
            ]
        ),
        pytest.param(
            [
                ValidatorWithdrawalInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                ),
                ValidatorWithdrawalInfo(
                    no_id=1,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                ),
            ]
        ),
    ],
)
def test_decode_evm_script_call_data(factory, values):
    """Must decode EVMScript call data correctly"""

    EVM_SCRIPT_CALLDATA = create_calldata(values)
    decoded_list = factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)

    assert len(decoded_list) == len(values), "Unexpected length of the decoded list"
    for actual, expected in zip(decoded_list, values):
        assert actual == expected
