import pytest
from brownie import (
    CreateOrUpdateOperatorGroup,
    MetaRegistryStub,
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
def meta_registry_stub(owner):
    return owner.deploy(MetaRegistryStub)


@pytest.fixture(scope="module")
def create_or_update_operator_group_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    meta_registry_stub,
):
    factory = owner.deploy(
        CreateOrUpdateOperatorGroup,
        commitee_multisig,
        FACTORY_NAME,
        meta_registry_stub.address,
    )

    permissions = (
        meta_registry_stub.address
        + meta_registry_stub.createOrUpdateOperatorGroup.signature[2:]
    )
    et_contracts.easy_track.addEVMScriptFactory(
        factory.address,
        permissions,
        {"from": voting},
    )
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_create_operator_group_via_motion_scenario(
    commitee_multisig,
    easytrack_executor,
    meta_registry_stub,
    create_or_update_operator_group_factory,
):
    groups_count_before = meta_registry_stub.getOperatorGroupsCount()

    evm_script_calldata = create_calldata(
        group_id=meta_registry_stub.NO_GROUP_ID(),
        sub_node_operators=[(1, 6000), (2, 4000)],
        external_operators=[make_nor_external_operator(1, 11)],
    )

    tx = easytrack_executor(
        commitee_multisig,
        create_or_update_operator_group_factory,
        evm_script_calldata,
    )

    assert meta_registry_stub.getOperatorGroupsCount() == groups_count_before + 1

    created_event = tx.events["OperatorGroupCreated"]
    if isinstance(created_event, list):
        created_event = created_event[-1]

    assert created_event["groupId"] == groups_count_before
