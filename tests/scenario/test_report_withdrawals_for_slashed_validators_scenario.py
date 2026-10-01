from collections import namedtuple
from typing import Iterable

import pytest
from brownie import (
    BaseModuleStub,
    ReportWithdrawalsForSlashedValidators,
)

from utils.evm_script import encode_calldata

FACTORY_NAME = "CSM v3"

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
def module(
    owner,
    use_deployed_contracts_from_env,
    active_cs_module,
    ensure_module_in_staking_router,
    ensure_module_unpaused,
    ensure_module_operator,
):
    if use_deployed_contracts_from_env:
        ensure_module_in_staking_router(active_cs_module, "CSM")
        ensure_module_unpaused(active_cs_module)
        ensure_module_operator(active_cs_module)
        return active_cs_module

    module = owner.deploy(BaseModuleStub)
    module.mock_setNodeOperatorsCount(1000)
    return module


@pytest.fixture(scope="module")
def factory(owner, et_contracts, voting, module):
    factory = ReportWithdrawalsForSlashedValidators.deploy(
        owner,
        FACTORY_NAME,
        module,
        {"from": owner},
    )

    permissions = module.address + module.reportSlashedWithdrawnValidators.signature[2:]
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
                    slashing_penalty=1,
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
    use_deployed_contracts_from_env,
    module,
    ensure_module_operator,
    ensure_key_reported_slashed,
    values: list[WithdrawnValidatorInfo],
):
    """Must create correct EVMScript if all requirements are met"""
    if use_deployed_contracts_from_env:
        no_id = ensure_module_operator(module)
        ensure_key_reported_slashed(module, no_id, key_index=0)
        values = [
            WithdrawnValidatorInfo(
                no_id=no_id,
                key_index=0,
                exit_balance=1,
                slashing_penalty=1,
                is_slashed=True,
            ),
        ]
    else:
        for v in values:
            module.mock_setValidatorSlashed(v.no_id, v.key_index, True)

    EVM_SCRIPT_CALLDATA = create_calldata(values)
    if use_deployed_contracts_from_env:
        evm_script = factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA, {"from": owner})
        assert evm_script != b""
        return

    tx = easytrack_executor(owner, factory, EVM_SCRIPT_CALLDATA)
    withdrawal_evts: list[dict] = tx.events["GotValidatorInfo"]
    assert len(withdrawal_evts) == len(values)
    for evt, req in zip(withdrawal_evts, values):
        assert evt["info"]["nodeOperatorId"] == req.no_id
        assert evt["info"]["keyIndex"] == req.key_index
        assert evt["info"]["exitBalance"] == req.exit_balance
        assert evt["info"]["slashingPenalty"] == req.slashing_penalty
        assert evt["info"]["isSlashed"] == req.is_slashed
