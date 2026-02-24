import pytest
from brownie import (
    AllowConsolidationPair,
    ConsolidationMigratorStub,
    NodeOperatorsRegistryStub,
)

from utils.evm_script import encode_calldata


SOURCE_MODULE_ID = 1
TARGET_MODULE_ID = 2


def create_calldata(consolidation_manager, source_operator_id, target_operator_id):
    return encode_calldata(
        ["address", "uint256", "uint256"],
        [consolidation_manager, source_operator_id, target_operator_id],
    )


@pytest.fixture(scope="module")
def source_module(owner, use_deployed_contracts_from_env, active_nor_module):
    if use_deployed_contracts_from_env:
        return active_nor_module

    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(1, {"from": owner})
    return registry


@pytest.fixture(scope="module")
def target_module(owner, use_deployed_contracts_from_env, active_curated_module):
    if use_deployed_contracts_from_env:
        return active_curated_module

    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(1, {"from": owner})
    return registry


@pytest.fixture(scope="module")
def consolidation_migrator(
    owner,
    use_deployed_contracts_from_env,
    active_sr_consolidation_migrator,
    source_module,
    target_module,
):
    if use_deployed_contracts_from_env:
        return active_sr_consolidation_migrator

    return owner.deploy(
        ConsolidationMigratorStub,
        SOURCE_MODULE_ID,
        TARGET_MODULE_ID,
        source_module.address,
        target_module.address,
    )


@pytest.fixture(scope="module")
def allow_consolidation_pair_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    source_module,
    target_module,
    consolidation_migrator,
    use_deployed_contracts_from_env,
    ensure_module_in_staking_router,
    ensure_legacy_module_operator,
    impersonate_account,
):
    if use_deployed_contracts_from_env:
        ensure_module_in_staking_router(target_module, "CM")

    source_operator_id = 0 if use_deployed_contracts_from_env else ensure_legacy_module_operator(source_module)
    target_operator_id = ensure_legacy_module_operator(target_module)

    # AllowConsolidationPair currently validates `msg.sender` as source operator owner.
    # In EasyTrack flow msg.sender is EasyTrack contract itself.
    reward_address = source_module.getNodeOperator(source_operator_id, False)[2]
    reward_sender = owner
    if use_deployed_contracts_from_env:
        reward_sender = impersonate_account(reward_address)

    source_module.setNodeOperatorRewardAddress(
        source_operator_id,
        et_contracts.easy_track.address,
        {"from": reward_sender},
    )

    factory = owner.deploy(AllowConsolidationPair, consolidation_migrator.address)

    permissions = (
        consolidation_migrator.address
        + consolidation_migrator.allowPair.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


@pytest.fixture(scope="module")
def source_operator_id(source_module, use_deployed_contracts_from_env, ensure_legacy_module_operator):
    if use_deployed_contracts_from_env:
        return 0
    return ensure_legacy_module_operator(source_module)


@pytest.fixture(scope="module")
def target_operator_id(target_module, ensure_legacy_module_operator):
    return ensure_legacy_module_operator(target_module)


def test_allow_consolidation_pair_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    consolidation_migrator,
    allow_consolidation_pair_factory,
    source_operator_id,
    target_operator_id,
):
    assert not consolidation_migrator.isPairAllowed(
        source_operator_id,
        target_operator_id,
    )

    evm_script_calldata = create_calldata(
        commitee_multisig.address,
        source_operator_id,
        target_operator_id,
    )

    tx = easytrack_executor(
        commitee_multisig,
        allow_consolidation_pair_factory,
        evm_script_calldata,
    )

    assert consolidation_migrator.isPairAllowed(
        source_operator_id,
        target_operator_id,
    )
    assert target_operator_id in consolidation_migrator.getAllowedTargets(
        source_operator_id
    )
    assert "ConsolidationPairAllowed" in tx.events
