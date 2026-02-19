import pytest

from utils.evm_script import encode_calldata


FACTORY_NAME = "CSMv3"


def create_calldata(node_operator_ids, max_amounts):
    return encode_calldata(["uint256[]", "uint256[]"], [node_operator_ids, max_amounts])


@pytest.fixture(scope="module")
def module(owner):
    from brownie import CSLikeModuleStub

    module = owner.deploy(CSLikeModuleStub)
    module.mock_setNodeOperatorsCount(1000, {"from": owner})
    module.mock_setActualLockedBond(0, 1000, {"from": owner})
    return module


@pytest.fixture(scope="module")
def settle_general_delayed_penalty_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    module,
):
    from brownie import SettleGeneralDelayedPenalty

    factory = owner.deploy(
        SettleGeneralDelayedPenalty,
        commitee_multisig,
        FACTORY_NAME,
        module.address,
    )

    permissions = module.address + module.settleGeneralDelayedPenalty.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(factory.address, permissions, {"from": voting})
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_settle_general_delayed_penalty_scenario(
    commitee_multisig,
    easytrack_executor,
    module,
    settle_general_delayed_penalty_factory,
):
    node_operator_ids = [0]
    max_amounts = [1000]
    locked_before = module.getActualLockedBond(node_operator_ids[0])
    assert locked_before > 0
    evm_script_calldata = create_calldata(node_operator_ids, max_amounts)

    tx = easytrack_executor(
        commitee_multisig,
        settle_general_delayed_penalty_factory,
        evm_script_calldata,
    )

    assert "GeneralDelayedPenaltySettled" in tx.events
    assert module.lastSettledCount() == 1
    assert module.lastSettledFirstNodeOperatorId() == node_operator_ids[0]
    assert module.lastSettledFirstMaxAmount() == max_amounts[0]
    assert module.getActualLockedBond(node_operator_ids[0]) == 0
