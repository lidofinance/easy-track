import pytest
import brownie
from brownie import (
    CreateOrUpdateOperatorGroup,
    CuratedModuleStub,
    MetaRegistryStub,
    StakingRouterStub,
)

from utils.evm_script import encode_calldata


FACTORY_NAME = "CMv2"


def create_calldata(group_id, sub_node_operators, external_operators):
    return encode_calldata(
        ["uint256", "((uint64,uint16)[],(bytes)[])"],
        [group_id, (sub_node_operators, external_operators)],
    )


def make_nor_external_operator(module_id, node_operator_id):
    data = bytes([0, module_id]) + int(node_operator_id).to_bytes(8, "big")
    return (data,)


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

    permissions = (
        meta_registry_contract.address
        + meta_registry_contract.createOrUpdateOperatorGroup.signature[2:]
    )
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
            "sub_node_operators": [(1, 6000), (2, 4000)],
            "external_operators": [make_nor_external_operator(1, 11)],
        }

    csm_module_id = ensure_module_in_staking_router(active_cs_module, "CSM")
    curated_operator_id = ensure_legacy_module_operator(curated_module_contract)
    csm_operator_id = ensure_module_operator(active_cs_module)
    return {
        "group_id": meta_registry_contract.NO_GROUP_ID(),
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

    assert created_event["groupId"] == groups_count_before


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
            sub_node_operators=scenario_group_input["sub_node_operators"],
            external_operators=scenario_group_input["external_operators"],
        ),
    )
    group_id = groups_count_before

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
            sub_node_operators=updated_sub_node_operators,
            external_operators=scenario_group_input["external_operators"],
        ),
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1

    if not use_deployed_contracts_from_env:
        updated_event = update_tx.events["OperatorGroupUpdated"]
        if isinstance(updated_event, list):
            updated_event = updated_event[-1]
        assert updated_event["groupId"] == group_id


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
            sub_node_operators=scenario_group_input["sub_node_operators"],
            external_operators=scenario_group_input["external_operators"],
        ),
    )
    group_id = groups_count_before

    clear_tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        create_calldata(
            group_id=group_id,
            sub_node_operators=[],
            external_operators=[],
        ),
    )

    assert meta_registry_contract.getOperatorGroupsCount() == groups_count_before + 1

    if not use_deployed_contracts_from_env:
        cleared_event = clear_tx.events["OperatorGroupCleared"]
        if isinstance(cleared_event, list):
            cleared_event = cleared_event[-1]
        assert cleared_event["groupId"] == group_id
