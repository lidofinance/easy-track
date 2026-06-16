import pytest
import brownie
from brownie import (
    CreateOrUpdateOperatorGroup,
    CuratedModuleStub,
    MetaRegistryStub,
    StakingRouterStub,
)

from utils.evm_script import encode_calldata


FACTORY_NAME = "CM v2"
GROUP_INFO_TYPE = "(string,(uint64,uint16)[],(bytes)[])"


def empty_group_info():
    return ("", [], [])


def create_calldata(
    group_id,
    sub_node_operators,
    external_operators,
    name,
    current_group_info=None,
):
    return encode_calldata(
        ["uint256", GROUP_INFO_TYPE, GROUP_INFO_TYPE],
        [
            group_id,
            current_group_info or empty_group_info(),
            (name, sub_node_operators, external_operators),
        ],
    )


def make_nor_external_operator(module_id, node_operator_id):
    data = bytes([0, module_id]) + int(node_operator_id).to_bytes(8, "big")
    return (data,)


def factory_permissions(factory, meta_registry):
    return (
        factory.address
        + factory.validateInputData.signature[2:]
        + meta_registry.address[2:]
        + meta_registry.createOrUpdateOperatorGroup.signature[2:]
    )


@pytest.fixture(scope="module")
def curated_module_contract(owner, use_deployed_contracts_from_env, active_curated_module):
    if use_deployed_contracts_from_env:
        return active_curated_module

    module = owner.deploy(CuratedModuleStub)
    module.mock_setNodeOperatorsCount(100, {"from": owner})
    return module


@pytest.fixture(scope="module")
def meta_registry_contract(
    owner,
    use_deployed_contracts_from_env,
    curated_module_contract,
):
    if use_deployed_contracts_from_env:
        return brownie.interface.IMetaRegistry(curated_module_contract.META_REGISTRY())

    registry = owner.deploy(MetaRegistryStub)

    external_module = owner.deploy(CuratedModuleStub)
    external_module.mock_setNodeOperatorsCount(100, {"from": owner})

    staking_router = owner.deploy(StakingRouterStub)
    staking_router.setStakingModule(1, external_module.address, {"from": owner})

    registry.setModule(curated_module_contract.address, {"from": owner})
    registry.setStakingRouter(staking_router.address, {"from": owner})

    # Wire the registry back onto the curated module so `module.META_REGISTRY()` resolves.
    curated_module_contract.mock_setMetaRegistry(registry.address, {"from": owner})

    return registry


@pytest.fixture(scope="module")
def create_or_update_operator_group_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    meta_registry_contract,
    curated_module_contract,
    use_deployed_contracts_from_env,
    active_cs_module,
    ensure_module_in_staking_router,
    ensure_module_unpaused,
    ensure_legacy_module_operator,
    ensure_module_operator,
):
    if use_deployed_contracts_from_env:
        ensure_module_in_staking_router(curated_module_contract, "CM")
        csm_module_id = ensure_module_in_staking_router(active_cs_module, "CSM")
        ensure_module_unpaused(active_cs_module)
        ensure_legacy_module_operator(curated_module_contract)
        ensure_module_operator(active_cs_module)
        allowed_ext_module_id = csm_module_id
    else:
        allowed_ext_module_id = 1

    factory = owner.deploy(
        CreateOrUpdateOperatorGroup,
        commitee_multisig,
        FACTORY_NAME,
        curated_module_contract.address,
        allowed_ext_module_id,
    )

    permissions = factory_permissions(factory, meta_registry_contract)
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


@pytest.fixture(scope="module")
def scenario_group_input(
    use_deployed_contracts_from_env,
    meta_registry_contract,
    curated_module_contract,
    active_cs_module,
    ensure_module_in_staking_router,
    ensure_legacy_module_operator,
    ensure_module_operator,
):
    if not use_deployed_contracts_from_env:
        return {
            "group_id": meta_registry_contract.NO_GROUP_ID(),
            "name": "Test Group",
            "sub_node_operators": [(1, 6000), (2, 4000)],
            "external_operators": [make_nor_external_operator(1, 11)],
        }

    csm_module_id = ensure_module_in_staking_router(active_cs_module, "CSM")
    curated_operator_id = ensure_legacy_module_operator(curated_module_contract)
    csm_operator_id = ensure_module_operator(active_cs_module)
    return {
        "group_id": meta_registry_contract.NO_GROUP_ID(),
        "name": "Test Group",
        "sub_node_operators": [(curated_operator_id, 10_000)],
        "external_operators": [make_nor_external_operator(csm_module_id, csm_operator_id)],
    }


def test_create_operator_group_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    scenario_group_input,
):
    groups_count_before = meta_registry_contract.getOperatorGroupsCount()

    evm_script_calldata = create_calldata(
        group_id=scenario_group_input["group_id"],
        name=scenario_group_input["name"],
        sub_node_operators=scenario_group_input["sub_node_operators"],
        external_operators=scenario_group_input["external_operators"],
    )

    tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        evm_script_calldata,
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1

    created_event = tx.events["OperatorGroupCreated"]
    if isinstance(created_event, list):
        created_event = created_event[-1]

    assert created_event["groupId"] == groups_count_before + 1


def test_update_operator_group_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    scenario_group_input,
    use_deployed_contracts_from_env,
):
    groups_count_before = meta_registry_contract.getOperatorGroupsCount()

    create_tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=scenario_group_input["group_id"],
            name=scenario_group_input["name"],
            sub_node_operators=scenario_group_input["sub_node_operators"],
            external_operators=scenario_group_input["external_operators"],
        ),
    )
    group_id = groups_count_before + 1

    updated_sub_node_operators = list(scenario_group_input["sub_node_operators"])
    if len(updated_sub_node_operators) == 1:
        updated_sub_node_operators = [(updated_sub_node_operators[0][0], 10_000)]
    else:
        first_operator_id = updated_sub_node_operators[0][0]
        last_operator_id = updated_sub_node_operators[-1][0]
        updated_sub_node_operators = [(first_operator_id, 5_500), (last_operator_id, 4_500)]

    update_tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=group_id,
            name="Updated Group",
            sub_node_operators=updated_sub_node_operators,
            external_operators=scenario_group_input["external_operators"],
            current_group_info=meta_registry_contract.getOperatorGroup(group_id),
        ),
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1

    if not use_deployed_contracts_from_env:
        updated_event = update_tx.events["OperatorGroupUpdated"]
        if isinstance(updated_event, list):
            updated_event = updated_event[-1]
        assert updated_event["groupId"] == group_id


def test_migrate_sub_operator_between_groups_scenario(
    owner,
    commitee_multisig,
    et_contracts,
    stranger,
    chain,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    use_deployed_contracts_from_env,
):
    """
    Two motions are created while both are still pending (before either is
    enacted), then enacted one by one in the correct order:

      Motion 1 update group A to remove operator X
      Motion 2 create group B with operator X   (created BEFORE motion 1 executes)

    The factory is stateless so it cannot detect the overlap at creation time.
    Executing motion 1 first frees operator X so that motion 2 succeeds.
    """
    if use_deployed_contracts_from_env:
        pytest.skip("local stub only")

    # -----------------------------------------------------------------
    # Prerequisite – create group A directly, not part of the motions under test
    # -----------------------------------------------------------------
    groups_count_before = meta_registry_contract.getOperatorGroupsCount()
    no_group_id = meta_registry_contract.NO_GROUP_ID()

    meta_registry_contract.createOrUpdateOperatorGroup(
        no_group_id,
        ("Group A", [(1, 5_000), (2, 5_000)], []),
        {"from": owner},
    )
    group_a_id = groups_count_before + 1

    # -----------------------------------------------------------------
    # Create both motions BEFORE enacting either of them
    # -----------------------------------------------------------------
    calldata_update_a = create_calldata(
        group_id=group_a_id,
        name="Group A",
        sub_node_operators=[(1, 10_000)],
        external_operators=[],
        current_group_info=meta_registry_contract.getOperatorGroup(group_a_id),
    )
    calldata_create_b = create_calldata(
        group_id=no_group_id,
        name="Group B",
        sub_node_operators=[(2, 10_000)],
        external_operators=[],
    )

    tx_motion1 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_update_a,
        {"from": commitee_multisig},
    )
    tx_motion2 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_create_b,
        {"from": commitee_multisig},
    )

    chain.sleep(72 * 60 * 60 + 100)

    # -----------------------------------------------------------------
    # Enact motion 1 first (removes operator X from group A)
    # -----------------------------------------------------------------
    et_contracts.easy_track.enactMotion(
        tx_motion1.events["MotionCreated"]["_motionId"],
        calldata_update_a,
        {"from": stranger},
    )

    # -----------------------------------------------------------------
    # Enact motion 2 (creates group B with now-free operator X)
    # -----------------------------------------------------------------
    et_contracts.easy_track.enactMotion(
        tx_motion2.events["MotionCreated"]["_motionId"],
        calldata_create_b,
        {"from": stranger},
    )

    group_b_id = groups_count_before + 2
    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 2
    assert meta_registry_contract.getNodeOperatorGroupId(1) == group_a_id
    assert meta_registry_contract.getNodeOperatorGroupId(2) == group_b_id


def test_migrate_sub_operator_between_existing_groups_scenario(
    owner,
    commitee_multisig,
    et_contracts,
    stranger,
    chain,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    use_deployed_contracts_from_env,
):
    """Move a sub-node-operator from group A to already existing group B."""
    if use_deployed_contracts_from_env:
        pytest.skip("local stub only")

    groups_count_before = meta_registry_contract.getOperatorGroupsCount()
    no_group_id = meta_registry_contract.NO_GROUP_ID()

    meta_registry_contract.createOrUpdateOperatorGroup(
        no_group_id,
        ("Group A", [(1, 5_000), (2, 5_000)], []),
        {"from": owner},
    )
    group_a_id = groups_count_before + 1

    meta_registry_contract.createOrUpdateOperatorGroup(
        no_group_id,
        ("Group B", [(3, 10_000)], []),
        {"from": owner},
    )
    group_b_id = groups_count_before + 2

    calldata_update_a = create_calldata(
        group_id=group_a_id,
        name="Group A",
        sub_node_operators=[(1, 10_000)],
        external_operators=[],
        current_group_info=meta_registry_contract.getOperatorGroup(group_a_id),
    )
    calldata_update_b = create_calldata(
        group_id=group_b_id,
        name="Group B",
        sub_node_operators=[(2, 5_000), (3, 5_000)],
        external_operators=[],
        current_group_info=meta_registry_contract.getOperatorGroup(group_b_id),
    )

    tx_motion1 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_update_a,
        {"from": commitee_multisig},
    )
    tx_motion2 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_update_b,
        {"from": commitee_multisig},
    )

    chain.sleep(72 * 60 * 60 + 100)

    et_contracts.easy_track.enactMotion(
        tx_motion1.events["MotionCreated"]["_motionId"],
        calldata_update_a,
        {"from": stranger},
    )
    et_contracts.easy_track.enactMotion(
        tx_motion2.events["MotionCreated"]["_motionId"],
        calldata_update_b,
        {"from": stranger},
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 2
    assert meta_registry_contract.getNodeOperatorGroupId(1) == group_a_id
    assert meta_registry_contract.getNodeOperatorGroupId(2) == group_b_id
    assert meta_registry_contract.getNodeOperatorGroupId(3) == group_b_id


def test_migrate_sub_operator_conflict_scenario(
    commitee_multisig,
    easytrack_executor,
    et_contracts,
    stranger,
    chain,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    scenario_group_input,
    use_deployed_contracts_from_env,
):
    """
    Two motions are created while both are still pending, but enacted in the
    WRONG order — motion 2 (create group B with operator X) fires BEFORE
    motion 1 (remove operator X from group A).

    MetaRegistry must reject motion 2 because operator X is still assigned
    to group A at execution time.
    """
    sub_ops = list(scenario_group_input["sub_node_operators"])

    if len(sub_ops) < 2:
        if use_deployed_contracts_from_env:
            pytest.skip("need at least 2 sub-operators for migration test on live contracts")
        pytest.skip("need at least 2 sub-operators")

    groups_count_before = meta_registry_contract.getOperatorGroupsCount()

    easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=scenario_group_input["group_id"],
            name=scenario_group_input["name"],
            sub_node_operators=sub_ops,
            external_operators=scenario_group_input["external_operators"],
        ),
    )
    group_a_id = groups_count_before + 1

    migrating_op_id = sub_ops[-1][0]
    remaining_ops = [(sub_ops[0][0], 10_000)]
    group_b_ops = [(migrating_op_id, 10_000)]

    calldata_update_a = create_calldata(
        group_id=group_a_id,
        name=scenario_group_input["name"],
        sub_node_operators=remaining_ops,
        external_operators=scenario_group_input["external_operators"],
        current_group_info=meta_registry_contract.getOperatorGroup(group_a_id),
    )
    calldata_create_b = create_calldata(
        group_id=scenario_group_input["group_id"],
        name="Group B",
        sub_node_operators=group_b_ops,
        external_operators=[],
    )

    tx_motion1 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_update_a,
        {"from": commitee_multisig},
    )
    tx_motion2 = et_contracts.easy_track.createMotion(
        create_or_update_operator_group_factory,
        calldata_create_b,
        {"from": commitee_multisig},
    )

    chain.sleep(72 * 60 * 60 + 100)

    # Enact motion 2 FIRST — operator X is still in group A → must revert
    with brownie.reverts():
        et_contracts.easy_track.enactMotion(
            tx_motion2.events["MotionCreated"]["_motionId"],
            calldata_create_b,
            {"from": stranger},
        )

    # Clean up: cancel both motions
    et_contracts.easy_track.cancelMotion(
        tx_motion2.events["MotionCreated"]["_motionId"], {"from": commitee_multisig}
    )
    et_contracts.easy_track.cancelMotion(
        tx_motion1.events["MotionCreated"]["_motionId"], {"from": commitee_multisig}
    )

    # Group count unchanged — neither motion landed
    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1


def test_clear_operator_group_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    meta_registry_contract,
    create_or_update_operator_group_factory,
    scenario_group_input,
    use_deployed_contracts_from_env,
):
    groups_count_before = meta_registry_contract.getOperatorGroupsCount()

    easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=scenario_group_input["group_id"],
            name=scenario_group_input["name"],
            sub_node_operators=scenario_group_input["sub_node_operators"],
            external_operators=scenario_group_input["external_operators"],
        ),
    )
    group_id = groups_count_before + 1

    clear_tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=group_id,
            name="",
            sub_node_operators=[],
            external_operators=[],
            current_group_info=meta_registry_contract.getOperatorGroup(group_id),
        ),
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1

    if not use_deployed_contracts_from_env:
        cleared_event = clear_tx.events["OperatorGroupCleared"]
        if isinstance(cleared_event, list):
            cleared_event = cleared_event[-1]
        assert cleared_event["groupId"] == group_id
