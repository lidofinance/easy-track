import pytest
from brownie import (
    ZERO_ADDRESS,
    CreateOrUpdateOperatorGroup,
    MetaRegistryStub,
    reverts,
)

from utils.evm_script import encode_call_script, encode_calldata
from utils.hardhat_helpers import get_last_tx_revert_reason


FACTORY_NAME = "CM v2"


def create_calldata(group_id, sub_node_operators, external_operators):
    return encode_calldata(
        ["uint256", "((uint64,uint16)[],(bytes)[])"],
        [group_id, (sub_node_operators, external_operators)],
    )


def make_nor_external_operator_data(module_id, node_operator_id):
    return bytes([0, module_id]) + int(node_operator_id).to_bytes(8, "big")


def make_nor_external_operator(module_id, node_operator_id):
    return (make_nor_external_operator_data(module_id, node_operator_id),)


def as_decoded_external_operators(external_operators):
    return [("0x" + item[0].hex(),) for item in external_operators]


def expected_evm_script(meta_registry, group_id, sub_node_operators, external_operators):
    call_data = meta_registry.createOrUpdateOperatorGroup.encode_input(
        group_id,
        (sub_node_operators, external_operators),
    )
    return encode_call_script([(meta_registry.address, call_data)])


def assert_constructor_reverts(owner, trusted_caller, module, revert_reason):
    try:
        with reverts(revert_reason):
            CreateOrUpdateOperatorGroup.deploy(
                trusted_caller,
                FACTORY_NAME,
                module,
                0,
                {"from": owner},
            )
    except ValueError:
        if revert_reason != get_last_tx_revert_reason():
            raise


def assert_create_evm_script_equals(
    factory,
    creator,
    meta_registry,
    group_id,
    sub_node_operators,
    external_operators,
):
    calldata = create_calldata(group_id, sub_node_operators, external_operators)
    evm_script = factory.createEVMScript(creator, calldata)
    assert evm_script == expected_evm_script(
        meta_registry,
        group_id,
        sub_node_operators,
        external_operators,
    )


def assert_create_evm_script_reverts(
    factory,
    creator,
    group_id,
    sub_node_operators,
    external_operators,
    revert_reason,
):
    calldata = create_calldata(group_id, sub_node_operators, external_operators)
    with reverts(revert_reason):
        factory.createEVMScript(creator, calldata)


ALLOWED_EXT_MODULE_ID = 1


@pytest.fixture(scope="module")
def curated_module_stub(owner, CuratedModuleStub):
    module = owner.deploy(CuratedModuleStub)
    module.mock_setNodeOperatorsCount(100, {"from": owner})
    return module


@pytest.fixture(scope="module")
def meta_registry_stub(owner, curated_module_stub, CuratedModuleStub, StakingRouterStub):
    registry = owner.deploy(MetaRegistryStub)

    external_module_1 = owner.deploy(CuratedModuleStub)
    external_module_1.mock_setNodeOperatorsCount(10_000, {"from": owner})
    external_module_2 = owner.deploy(CuratedModuleStub)
    external_module_2.mock_setNodeOperatorsCount(10_000, {"from": owner})

    staking_router = owner.deploy(StakingRouterStub)
    staking_router.setStakingModule(1, external_module_1.address, {"from": owner})
    staking_router.setStakingModule(2, external_module_2.address, {"from": owner})

    registry.setModule(curated_module_stub.address, {"from": owner})
    registry.setStakingRouter(staking_router.address, {"from": owner})

    # Wire the registry back onto the curated module so `module.META_REGISTRY()` resolves.
    curated_module_stub.mock_setMetaRegistry(registry.address, {"from": owner})

    return registry


@pytest.fixture(scope="module")
def factory(owner, curated_module_stub, meta_registry_stub):
    return owner.deploy(
        CreateOrUpdateOperatorGroup,
        owner.address,
        FACTORY_NAME,
        curated_module_stub,
        ALLOWED_EXT_MODULE_ID,
    )


# -----------------------
# Deployment
# -----------------------


def test_deploy(owner, meta_registry_stub, curated_module_stub, factory):
    assert factory.trustedCaller() == owner
    assert factory.name() == FACTORY_NAME
    assert factory.module() == curated_module_stub
    assert factory.metaRegistry() == meta_registry_stub
    assert factory.stakingRouter() == meta_registry_stub.STAKING_ROUTER()
    assert factory.allowedExternalModuleId() == ALLOWED_EXT_MODULE_ID


def test_deploy_reverts_with_zero_module(owner):
    assert_constructor_reverts(
        owner=owner,
        trusted_caller=owner.address,
        module=ZERO_ADDRESS,
        revert_reason="ZERO_MODULE_ADDRESS",
    )


def test_deploy_reverts_with_zero_trusted_caller(owner, curated_module_stub):
    assert_constructor_reverts(
        owner=owner,
        trusted_caller=ZERO_ADDRESS,
        module=curated_module_stub,
        revert_reason="TRUSTED_CALLER_IS_ZERO_ADDRESS",
    )


# -----------------------
# Permission and Decode
# -----------------------


def test_create_evm_script_called_by_stranger(stranger, factory):
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, "0x")


def test_encode_nor_external_operator_data(factory):
    module_id = 7
    node_operator_id = 255

    expected = "0x" + make_nor_external_operator_data(module_id, node_operator_id).hex()

    assert factory.encodeNORExtOperatorData(module_id, node_operator_id) == expected


def test_decode_nor_external_operator_data(factory):
    module_id = 7
    node_operator_id = 255
    encoded = "0x" + make_nor_external_operator_data(module_id, node_operator_id).hex()

    decoded_module_id, decoded_node_operator_id = factory.decodeNORExtOperatorData(
        encoded
    )

    assert decoded_module_id == module_id
    assert decoded_node_operator_id == node_operator_id


def test_decode_evm_script_call_data(factory):
    group_id = 0
    sub_node_operators = [(1, 6000), (2, 4000)]
    external_operators = [
        make_nor_external_operator(1, 11),
        make_nor_external_operator(2, 22),
    ]
    calldata = create_calldata(group_id, sub_node_operators, external_operators)

    decoded_group_id, decoded_group_info = factory.decodeEVMScriptCallData(calldata)

    assert decoded_group_id == group_id
    assert decoded_group_info[0] == sub_node_operators
    assert decoded_group_info[1] == as_decoded_external_operators(
        external_operators
    )


@pytest.mark.parametrize("invalid_calldata", ["0x", "0x01"], ids=["empty", "malformed"])
def test_decode_reverts_with_invalid_calldata(factory, invalid_calldata):
    with reverts():
        factory.decodeEVMScriptCallData(invalid_calldata)


def test_create_evm_script_reverts_with_malformed_calldata(owner, factory):
    with reverts():
        factory.createEVMScript(owner, "0x01")


# -----------------------
# Create Path
# -----------------------


def test_create_group_success(owner, meta_registry_stub, factory):
    assert_create_evm_script_equals(
        factory=factory,
        creator=owner,
        meta_registry=meta_registry_stub,
        group_id=0,
        sub_node_operators=[(1, 7000), (2, 3000)],
        external_operators=[
            make_nor_external_operator(1, 1001),
            make_nor_external_operator(1, 2002),
        ],
    )


def test_create_group_reverts_with_empty_sub_node_operators(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[],
        external_operators=[],
        revert_reason="EMPTY_GROUP",
    )


def test_create_group_reverts_with_empty_sub_node_operators_and_non_empty_external(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[],
        external_operators=[make_nor_external_operator(1, 1)],
        revert_reason="EMPTY_GROUP",
    )


def test_create_group_reverts_with_unsorted_sub_node_operators(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(2, 5000), (1, 5000)],
        external_operators=[],
        revert_reason="SUB_NODE_OPERATORS_NOT_SORTED",
    )


def test_create_group_reverts_with_duplicate_sub_node_operators(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 5000), (1, 5000)],
        external_operators=[],
        revert_reason="SUB_NODE_OPERATORS_NOT_SORTED",
    )


def test_create_group_reverts_with_shares_sum_mismatch(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 5000), (2, 4000)],
        external_operators=[],
        revert_reason="SUB_NODE_OPERATOR_SHARES_SUM_MISMATCH",
    )


def test_create_group_reverts_with_unsorted_external_operators(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[
            make_nor_external_operator(1, 2),
            make_nor_external_operator(1, 1),
        ],
        revert_reason="EXTERNAL_OPERATORS_NOT_SORTED",
    )


def test_create_group_reverts_with_duplicate_external_operators(owner, factory):
    duplicate_external_operator = make_nor_external_operator(1, 1)
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[
            duplicate_external_operator,
            duplicate_external_operator,
        ],
        revert_reason="EXTERNAL_OPERATORS_NOT_SORTED",
    )


def test_create_group_reverts_with_missing_sub_node_operator(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(100, 10000)],
        external_operators=[],
        revert_reason="SUB_NODE_OPERATOR_DOES_NOT_EXIST",
    )


def test_create_group_reverts_with_invalid_external_operator_data_length(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[(bytes([0, 1]),)],
        revert_reason="INVALID_EXTERNAL_OPERATOR_DATA_LENGTH",
    )


def test_create_group_reverts_with_unsupported_external_operator_type(owner, factory):
    invalid_external_operator_data = bytes([1, 1]) + int(1).to_bytes(8, "big")
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[(invalid_external_operator_data,)],
        revert_reason="UNSUPPORTED_EXTERNAL_OPERATOR_TYPE",
    )


def test_create_group_reverts_with_not_allowed_external_module(owner, factory):
    # Module 2 exists in the router but is NOT the allowed one (allowed = 1)
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[make_nor_external_operator(2, 1)],
        revert_reason="EXTERNAL_MODULE_NOT_ALLOWED",
    )


def test_create_group_reverts_with_missing_external_module(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[make_nor_external_operator(99, 1)],
        revert_reason="EXTERNAL_MODULE_NOT_ALLOWED",
    )


def test_create_group_reverts_with_missing_external_operator(owner, factory):
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=0,
        sub_node_operators=[(1, 10000)],
        external_operators=[make_nor_external_operator(1, 10_000)],
        revert_reason="EXTERNAL_OPERATOR_DOES_NOT_EXIST",
    )


# -----------------------
# Update Path
# -----------------------


def test_update_group_success(owner, meta_registry_stub, factory):
    meta_registry_stub.setGroupsCount(3, {"from": owner})
    assert_create_evm_script_equals(
        factory=factory,
        creator=owner,
        meta_registry=meta_registry_stub,
        group_id=1,
        sub_node_operators=[(10, 10000)],
        external_operators=[make_nor_external_operator(1, 1234)],
    )


def test_update_group_clear_success(owner, meta_registry_stub, factory):
    meta_registry_stub.setGroupsCount(3, {"from": owner})
    assert_create_evm_script_equals(
        factory=factory,
        creator=owner,
        meta_registry=meta_registry_stub,
        group_id=1,
        sub_node_operators=[],
        external_operators=[],
    )


def test_update_group_reverts_with_invalid_empty_shape(owner, meta_registry_stub, factory):
    meta_registry_stub.setGroupsCount(3, {"from": owner})
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=1,
        sub_node_operators=[],
        external_operators=[make_nor_external_operator(1, 1)],
        revert_reason="INVALID_EMPTY_GROUP_UPDATE",
    )


@pytest.mark.parametrize(
    "group_id, sub_node_operators, external_operators",
    [
        pytest.param(2, [(1, 10000)], [], id="equal_to_groups_count"),
        pytest.param(3, [(1, 10000)], [], id="greater_than_groups_count"),
        pytest.param(3, [], [], id="clear_update"),
    ],
)
def test_update_group_reverts_with_invalid_group_id(
    owner,
    meta_registry_stub,
    factory,
    group_id,
    sub_node_operators,
    external_operators,
):
    meta_registry_stub.setGroupsCount(2, {"from": owner})
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=group_id,
        sub_node_operators=sub_node_operators,
        external_operators=external_operators,
        revert_reason="INVALID_GROUP_ID",
    )


# -----------------------
# Non-Zero NO_GROUP_ID
# -----------------------


def test_update_group_clear_reverts_with_invalid_group_id_when_no_group_id_is_non_zero(
    owner,
    meta_registry_stub,
    factory,
):
    meta_registry_stub.setNoGroupId(10, {"from": owner})
    meta_registry_stub.setGroupsCount(2, {"from": owner})
    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=2,
        sub_node_operators=[],
        external_operators=[],
        revert_reason="INVALID_GROUP_ID",
    )


def test_create_and_update_with_non_zero_no_group_id(owner, meta_registry_stub, factory):
    meta_registry_stub.setNoGroupId(10, {"from": owner})
    meta_registry_stub.setGroupsCount(12, {"from": owner})

    assert_create_evm_script_equals(
        factory=factory,
        creator=owner,
        meta_registry=meta_registry_stub,
        group_id=10,
        sub_node_operators=[(1, 6000), (2, 4000)],
        external_operators=[],
    )
    assert_create_evm_script_equals(
        factory=factory,
        creator=owner,
        meta_registry=meta_registry_stub,
        group_id=1,
        sub_node_operators=[(3, 10000)],
        external_operators=[],
    )


def test_create_reverts_with_invalid_group_id_when_no_group_id_is_out_of_range(
    owner,
    meta_registry_stub,
    factory,
):
    meta_registry_stub.setNoGroupId(10, {"from": owner})
    meta_registry_stub.setGroupsCount(2, {"from": owner})

    assert_create_evm_script_reverts(
        factory=factory,
        creator=owner,
        group_id=10,
        sub_node_operators=[(1, 10000)],
        external_operators=[],
        revert_reason="INVALID_GROUP_ID",
    )
