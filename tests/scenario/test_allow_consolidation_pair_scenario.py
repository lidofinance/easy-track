import pytest
from brownie import (
    AllowConsolidationPair,
    CSLikeModuleStub,
    ConsolidationMigratorStub,
    NodeOperatorsRegistryStub,
)

from utils.evm_script import encode_calldata


SOURCE_MODULE_ID = 1
TARGET_MODULE_ID = 2
SOURCE_OPERATOR_ID = 0
TARGET_OPERATOR_ID = 3


def create_calldata(consolidation_manager, source_operator_id, target_operator_id):
    return encode_calldata(
        ["address", "uint256", "uint256"],
        [consolidation_manager, source_operator_id, target_operator_id],
    )


@pytest.fixture(scope="module")
def source_module_stub(owner):
    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID + 1, {"from": owner})
    return registry


@pytest.fixture(scope="module")
def target_module_stub(owner):
    module = owner.deploy(CSLikeModuleStub)
    module.mock_setNodeOperatorsCount(TARGET_OPERATOR_ID + 2, {"from": owner})
    return module


@pytest.fixture(scope="module")
def consolidation_migrator_stub(owner, source_module_stub, target_module_stub):
    return owner.deploy(
        ConsolidationMigratorStub,
        SOURCE_MODULE_ID,
        TARGET_MODULE_ID,
        source_module_stub.address,
        target_module_stub.address,
    )


@pytest.fixture(scope="module")
def allow_consolidation_pair_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    source_module_stub,
    consolidation_migrator_stub,
):
    # AllowConsolidationPair currently validates `msg.sender` as source operator owner.
    # In EasyTrack flow msg.sender is EasyTrack contract itself.
    source_module_stub.setNodeOperatorRewardAddress(
        SOURCE_OPERATOR_ID,
        et_contracts.easy_track.address,
        {"from": owner},
    )

    factory = owner.deploy(AllowConsolidationPair, consolidation_migrator_stub.address)

    permissions = (
        consolidation_migrator_stub.address
        + consolidation_migrator_stub.allowPair.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_allow_consolidation_pair_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    consolidation_migrator_stub,
    allow_consolidation_pair_factory,
):
    assert not consolidation_migrator_stub.isPairAllowed(
        SOURCE_OPERATOR_ID,
        TARGET_OPERATOR_ID,
    )

    evm_script_calldata = create_calldata(
        commitee_multisig.address,
        SOURCE_OPERATOR_ID,
        TARGET_OPERATOR_ID,
    )

    tx = easytrack_executor(
        commitee_multisig,
        allow_consolidation_pair_factory,
        evm_script_calldata,
    )

    assert consolidation_migrator_stub.isPairAllowed(
        SOURCE_OPERATOR_ID,
        TARGET_OPERATOR_ID,
    )
    assert TARGET_OPERATOR_ID in consolidation_migrator_stub.getAllowedTargets(
        SOURCE_OPERATOR_ID
    )
    assert "ConsolidationPairAllowed" in tx.events
