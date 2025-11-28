from collections import namedtuple
from typing import Iterable

import pytest
from brownie import (
    CSLikeModuleStub,
    ReportSlashedValidatorsAsWithdrawn,
)

from utils.evm_script import encode_calldata

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


def create_calldata(values: Iterable[WithdrawnValidatorInfo]):
    return encode_calldata("(uint256,uint256,uint256,uint256,bool)[]", [values])


@pytest.fixture(scope="module")
def module(owner):
    module = owner.deploy(CSLikeModuleStub)
    module.mock_setNodeOperatorsCount(1000)
    return module


@pytest.fixture(scope="module")
def factory(owner, et_contracts, voting, module):
    factory = ReportSlashedValidatorsAsWithdrawn.deploy(
        owner,
        "MY_LOVELY_FACTORY",
        module,
        {"from": owner},
    )

    permissions = module.address + module.reportWithdrawnValidators.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )

    return factory


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
                    slashing_penalty=0,
                    is_slashed=True,
                ),
            ]
        ),
    ],
)
def test_submit_withdrawals_scenario(
    easytrack_executor,
    owner,
    factory,
    values: list[WithdrawnValidatorInfo],
):
    """Must create correct EVMScript if all requirements are met"""

    EVM_SCRIPT_CALLDATA = create_calldata(values)
    tx = easytrack_executor(owner, factory, EVM_SCRIPT_CALLDATA)
    withdrawal_evts: list[dict] = tx.events["GotValidatorInfo"]
    assert len(withdrawal_evts) == len(values)
    for evt, req in zip(withdrawal_evts, values):
        assert evt["info"]["nodeOperatorId"] == req.no_id
        assert evt["info"]["keyIndex"] == req.key_index
        assert evt["info"]["exitBalance"] == req.exit_balance
        assert evt["info"]["slashingPenalty"] == req.slashing_penalty
        assert evt["info"]["isSlashed"] == req.is_slashed
