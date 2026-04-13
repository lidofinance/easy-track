import pytest
from brownie import (
    interface,
    AllowConsolidationPair,
    ConsolidationMigratorStub,
    CSModuleNodeOperatorsStub,
    MetaRegistryStub,
    NodeOperatorsRegistryStub,
)

from utils.evm_script import encode_calldata


SOURCE_MODULE_ID = 1
TARGET_MODULE_ID = 2
LOCAL_TARGET_OPERATOR_IDS = [0, 1]
LOCAL_OVERWRITE_TARGET_OPERATOR_ID = 2
LOCAL_GROUP_ID = 1


def create_calldata(submitter, source_operator_id, target_operator_ids):
    return encode_calldata(
        ["address", "uint256", "uint256[]"],
        [submitter, source_operator_id, target_operator_ids],
    )


def _encode_nor_external_operator_data(module_id, node_operator_id):
    return (
        b"\x00"
        + int(module_id).to_bytes(1, "big")
        + int(node_operator_id).to_bytes(8, "big")
    )


def _decode_nor_external_operator_data(data):
    raw = data
    if isinstance(raw, str):
        raw = bytes.fromhex(raw[2:])
    else:
        raw = bytes(raw)

    assert len(raw) == 10
    assert raw[0] == 0
    return raw[1], int.from_bytes(raw[2:], "big")


def _find_linked_operator_ids(meta_registry, source_module_id):
    for group_id in range(1, meta_registry.getOperatorGroupsCount()):
        group = meta_registry.getOperatorGroup(group_id)
        sub_node_operators = group[0]
        external_operators = group[1]
        if len(sub_node_operators) == 0:
            continue

        target_operator_ids = [sub_node_operator[0] for sub_node_operator in sub_node_operators]
        if len(target_operator_ids) == 0:
            continue

        for external_operator in external_operators:
            module_id, node_operator_id = _decode_nor_external_operator_data(
                external_operator[0]
            )
            if module_id == source_module_id:
                return node_operator_id, target_operator_ids

    raise AssertionError("No linked source/target operators found in MetaRegistry")


@pytest.fixture(scope="module")
def source_module(
    owner,
    use_deployed_contracts_from_env,
    active_nor_module,
):
    if use_deployed_contracts_from_env:
        return active_nor_module

    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(1, {"from": owner})
    return registry


@pytest.fixture(scope="module")
def target_module(owner, use_deployed_contracts_from_env, active_curated_module):
    if use_deployed_contracts_from_env:
        return active_curated_module

    module = owner.deploy(CSModuleNodeOperatorsStub)
    all_local_target_operator_ids = LOCAL_TARGET_OPERATOR_IDS + [LOCAL_OVERWRITE_TARGET_OPERATOR_ID]
    module.setNodeOperatorsCount(max(all_local_target_operator_ids) + 1, {"from": owner})
    for target_operator_id in all_local_target_operator_ids:
        module.setNodeOperatorIsActive(target_operator_id, True, {"from": owner})
    return module


@pytest.fixture(scope="module")
def meta_registry_contract(owner, use_deployed_contracts_from_env, target_module):
    if use_deployed_contracts_from_env:
        return interface.IMetaRegistry(target_module.META_REGISTRY())

    return owner.deploy(MetaRegistryStub)


@pytest.fixture(scope="module")
def consolidation_migrator(
    owner,
    use_deployed_contracts_from_env,
    active_sr_consolidation_migrator,
    source_module,
    target_module,
):
    if use_deployed_contracts_from_env:
        assert active_sr_consolidation_migrator.sourceModule() == source_module.address
        assert active_sr_consolidation_migrator.targetModule() == target_module.address
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
    voting,
    et_contracts,
    source_module,
    target_module,
    consolidation_migrator,
    meta_registry_contract,
    use_deployed_contracts_from_env,
    ensure_module_in_staking_router,
):
    if use_deployed_contracts_from_env:
        ensure_module_in_staking_router(target_module, "CM")
    else:
        target_module.setMetaRegistry(meta_registry_contract.address, {"from": owner})

    factory = owner.deploy(
        AllowConsolidationPair,
        consolidation_migrator.address,
    )

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
def linked_operator_ids(
    owner,
    use_deployed_contracts_from_env,
    source_module,
    consolidation_migrator,
    meta_registry_contract,
    ensure_legacy_module_operator,
):
    if use_deployed_contracts_from_env:
        source_module_id = consolidation_migrator.sourceModuleId()
        return _find_linked_operator_ids(
            meta_registry_contract,
            source_module_id,
        )

    source_operator_id = ensure_legacy_module_operator(source_module)
    # Local-stub setup for MetaRegistry link emulation:
    # source operator is stored as external operator entry, target operators as sub node operators.
    meta_registry_contract.setExternalOperatorGroupId(
        _encode_nor_external_operator_data(SOURCE_MODULE_ID, source_operator_id),
        LOCAL_GROUP_ID,
        {"from": owner},
    )
    meta_registry_contract.setNodeOperatorGroupId(
        LOCAL_OVERWRITE_TARGET_OPERATOR_ID,
        LOCAL_GROUP_ID,
        {"from": owner},
    )
    for target_operator_id in LOCAL_TARGET_OPERATOR_IDS:
        meta_registry_contract.setNodeOperatorGroupId(
            target_operator_id,
            LOCAL_GROUP_ID,
            {"from": owner},
        )
    return source_operator_id, LOCAL_TARGET_OPERATOR_IDS


@pytest.fixture(scope="module")
def source_operator_id(linked_operator_ids):
    return linked_operator_ids[0]


@pytest.fixture(scope="module")
def target_operator_ids(linked_operator_ids):
    return linked_operator_ids[1]


@pytest.fixture(scope="module")
def source_operator_creator(
    owner,
    source_module,
    source_operator_id,
    use_deployed_contracts_from_env,
    impersonate_account,
):
    reward_address = source_module.getNodeOperator(source_operator_id, False)[2]
    if use_deployed_contracts_from_env:
        return impersonate_account(reward_address)
    return owner


def test_allow_consolidation_pair_via_motion_scenario(
    source_operator_creator,
    easytrack_executor,
    consolidation_migrator,
    allow_consolidation_pair_factory,
    source_operator_id,
    target_operator_ids,
):
    for target_operator_id in target_operator_ids:
        assert not consolidation_migrator.isPairAllowed(
            source_operator_id,
            target_operator_id,
        )

    evm_script_calldata = create_calldata(
        source_operator_creator.address,
        source_operator_id,
        target_operator_ids,
    )

    tx = easytrack_executor(
        source_operator_creator,
        allow_consolidation_pair_factory,
        evm_script_calldata,
    )

    allowed_targets = consolidation_migrator.getAllowedTargets(source_operator_id)
    for target_operator_id in target_operator_ids:
        assert consolidation_migrator.isPairAllowed(
            source_operator_id,
            target_operator_id,
        )
        assert consolidation_migrator.getSubmitter(
            source_operator_id,
            target_operator_id,
        ) == source_operator_creator.address
        assert target_operator_id in allowed_targets
    assert "ConsolidationPairAllowed" in tx.events


def test_allow_consolidation_pair_overwrites_submitter_via_second_motion(
    owner,
    stranger,
    use_deployed_contracts_from_env,
    source_operator_creator,
    easytrack_executor,
    consolidation_migrator,
    allow_consolidation_pair_factory,
    source_operator_id,
):
    if use_deployed_contracts_from_env:
        pytest.skip("local stub only")

    overwrite_target_ids = [LOCAL_OVERWRITE_TARGET_OPERATOR_ID]

    first_calldata = create_calldata(
        owner.address,
        source_operator_id,
        overwrite_target_ids,
    )
    easytrack_executor(
        source_operator_creator,
        allow_consolidation_pair_factory,
        first_calldata,
    )

    assert consolidation_migrator.getSubmitter(
        source_operator_id,
        LOCAL_OVERWRITE_TARGET_OPERATOR_ID,
    ) == owner.address
    assert consolidation_migrator.getAllowedTargets(source_operator_id).count(
        LOCAL_OVERWRITE_TARGET_OPERATOR_ID
    ) == 1

    second_calldata = create_calldata(
        stranger.address,
        source_operator_id,
        overwrite_target_ids,
    )
    easytrack_executor(
        source_operator_creator,
        allow_consolidation_pair_factory,
        second_calldata,
    )

    assert consolidation_migrator.getSubmitter(
        source_operator_id,
        LOCAL_OVERWRITE_TARGET_OPERATOR_ID,
    ) == stranger.address
    assert consolidation_migrator.getAllowedTargets(source_operator_id).count(
        LOCAL_OVERWRITE_TARGET_OPERATOR_ID
    ) == 1
