from collections import namedtuple
from typing import Iterable

import pytest
from brownie import (
    BaseModuleStub,
    ReportWithdrawalsForSlashedValidators,
    reverts,
)

from utils.evm_script import encode_call_script, encode_calldata
from utils.hardhat_helpers import get_last_tx_revert_reason

WithdrawnValidatorInfo = namedtuple(
    "WithdrawnValidatorInfo",
    [
        "no_id",
        "key_index",
        "exit_balance",
        "slashing_penalty",
        "is_slashed",
    ],
)

FACTORY_NAME = "MY_LOVELY_FACTORY"


def create_calldata(values: Iterable[WithdrawnValidatorInfo]):
    return encode_calldata("(uint256,uint256,uint256,uint256,bool)[]", [values])


@pytest.fixture(scope="module")
def module(owner):
    module = owner.deploy(BaseModuleStub)
    module.mock_setNodeOperatorsCount(1000)
    return module


@pytest.fixture(scope="module")
def factory(owner, module):
    return ReportWithdrawalsForSlashedValidators.deploy(
        owner,
        FACTORY_NAME,
        module,
        {"from": owner},
    )


def test_deploy(owner, module, factory):
    assert factory.trustedCaller() == owner
    assert factory.name() == FACTORY_NAME
    assert factory.module() == module


def test_deploy_reverts_on_zero_module_address(owner):
    try:
        with reverts("ZERO_MODULE_ADDRESS"):
            ReportWithdrawalsForSlashedValidators.deploy(
                owner,
                FACTORY_NAME,
                "0x0000000000000000000000000000000000000000",
                {"from": owner},
            )
    except ValueError:
        if "ZERO_MODULE_ADDRESS" != get_last_tx_revert_reason():
            raise


def test_create_evm_script_reverts_if_called_by_stranger(stranger, factory):
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_create_evm_script_reverts_if_empty_withdrawal_list(owner, factory):
    EVM_SCRIPT_CALLDATA = create_calldata([])
    with reverts("EMPTY_VALIDATOR_INFO_LIST"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=0,
                    slashing_penalty=1,
                    is_slashed=True,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=0,
                    slashing_penalty=1,
                    is_slashed=True,
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
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=1,
                    slashing_penalty=0,
                    is_slashed=True,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=1,
                    exit_balance=1,
                    slashing_penalty=0,
                    is_slashed=True,
                ),
            ]
        ),
    ],
)
def test_create_evm_script_reverts_if_zero_slashing_penalty(owner, factory, values):
    EVM_SCRIPT_CALLDATA = create_calldata(values)
    with reverts("INVALID_SLASHING_PENALTY"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=1001,
                    key_index=1,
                    exit_balance=1,
                    slashing_penalty=1,
                    is_slashed=True,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=1001,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                    is_slashed=True,
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
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=1,
                    exit_balance=1,
                    slashing_penalty=1,
                    is_slashed=False,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=False,
                ),
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                    is_slashed=False,
                ),
            ]
        ),
    ],
)
def test_create_evm_script_reverts_if_not_slashed(owner, factory, values):
    EVM_SCRIPT_CALLDATA = create_calldata(values)
    with reverts("VALIDATOR_NOT_SLASHED"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=1,
                    exit_balance=30000,
                    slashing_penalty=1,
                    is_slashed=True,
                ),
            ],
            id="descending_operator_ids",
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=1,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=5,
                    exit_balance=30000,
                    slashing_penalty=1,
                    is_slashed=True,
                ),
            ],
            id="same_operator_id",
        ),
    ],
)
def test_create_evm_script_reverts_if_not_sorted(owner, factory, values):
    EVM_SCRIPT_CALLDATA = create_calldata(values)
    with reverts("NOT_SORTED"):
        factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
            ],
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=1,
                    is_slashed=True,
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
                module.reportSlashedWithdrawnValidators.encode_input(values),
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
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=0,
                    slashing_penalty=0,
                    is_slashed=True,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=2,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
            ]
        ),
        pytest.param(
            [
                WithdrawnValidatorInfo(
                    no_id=0,
                    key_index=0,
                    exit_balance=100500,
                    slashing_penalty=16,
                    is_slashed=True,
                ),
                WithdrawnValidatorInfo(
                    no_id=1,
                    key_index=3,
                    exit_balance=30000,
                    slashing_penalty=0,
                    is_slashed=True,
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


@pytest.mark.parametrize("invalid_calldata", ["0x", "0x01"], ids=["empty", "malformed"])
def test_decode_evm_script_call_data_reverts_on_invalid_calldata(factory, invalid_calldata):
    with reverts():
        factory.decodeEVMScriptCallData(invalid_calldata)
