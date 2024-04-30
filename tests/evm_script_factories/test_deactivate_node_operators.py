import pytest
from eth_abi import encode
from brownie import reverts, DeactivateNodeOperators, web3

from utils.evm_script import encode_call_script
from utils.permission_parameters import Op, Param, encode_permission_params

MANAGERS = [
    "0x0000000000000000000000000000000000000001",
    "0x0000000000000000000000000000000000000002",
]


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["(uint256,address)[]"],
            [data],
        ).hex()
    )


@pytest.fixture(scope="module")
def deactivate_node_operators_factory(owner, node_operators_registry, acl, voting):
    acl.grantPermission(
        voting,
        node_operators_registry,
        web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex(),
        {"from": voting},
    )
    for id, manager in enumerate(MANAGERS):
        acl.grantPermissionP(
            manager,
            node_operators_registry,
            web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
            encode_permission_params([Param(0, Op.EQ, id)]),
            {"from": voting},
        )
    return DeactivateNodeOperators.deploy(owner, node_operators_registry, acl, {"from": owner})


def test_deploy(node_operators_registry, owner, acl, deactivate_node_operators_factory):
    "Must deploy contract with correct data"
    assert deactivate_node_operators_factory.trustedCaller() == owner
    assert deactivate_node_operators_factory.nodeOperatorsRegistry() == node_operators_registry
    assert deactivate_node_operators_factory.acl() == acl


def test_create_evm_script_called_by_stranger(stranger, deactivate_node_operators_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        deactivate_node_operators_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, deactivate_node_operators_factory):
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([])
        deactivate_node_operators_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_non_sorted_calldata(owner, deactivate_node_operators_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALLDATA = create_calldata([(1, MANAGERS[1]), (0, MANAGERS[0])])
        deactivate_node_operators_factory.createEVMScript(owner, NON_SORTED_CALLDATA)

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALLDATA = create_calldata([(0, MANAGERS[0]), (0, MANAGERS[0])])
        deactivate_node_operators_factory.createEVMScript(owner, NON_SORTED_CALLDATA)


def test_operator_id_out_of_range(owner, deactivate_node_operators_factory, node_operators_registry):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALLDATA = create_calldata(
            [
                (
                    node_operators_count,
                    "0x0000000000000000000000000000000000000000",
                )
            ]
        )
        deactivate_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_node_operator_invalid_state(owner, deactivate_node_operators_factory, node_operators_registry, voting):
    "Must revert with message 'WRONG_OPERATOR_ACTIVE_STATE' when operator already active"

    node_operators_registry.deactivateNodeOperator(0, {"from": voting})

    with reverts("WRONG_OPERATOR_ACTIVE_STATE"):
        CALLDATA = create_calldata([(0, MANAGERS[0])])
        deactivate_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_manager_has_no_role(owner, deactivate_node_operators_factory, node_operators_registry, acl, voting):
    "Must revert with message 'MANAGER_HAS_NO_ROLE' when manager has no MANAGE_SIGNING_KEYS role"

    CALLDATA = create_calldata([(2, MANAGERS[0])])
    with reverts("MANAGER_HAS_NO_ROLE"):
        deactivate_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_manager_has_another_role_operator(
    owner, deactivate_node_operators_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'MANAGER_HAS_NO_ROLE' when manager has MANAGE_SIGNING_KEYS role with wrong param operator"

    manager = "0x0000000000000000000000000000000000000001"
    operator = 2

    acl.grantPermissionP(
        manager,
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        encode_permission_params([Param(0, Op.NEQ, operator)]),
        {"from": voting},
    )

    CALLDATA = create_calldata([(operator, manager)])
    with reverts("MANAGER_HAS_NO_ROLE"):
        deactivate_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_manager_has_role_for_another_operator(
    owner, deactivate_node_operators_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'MANAGER_HAS_NO_ROLE' when manager has MANAGE_SIGNING_KEYS role with wrong param operator"

    manager = "0x0000000000000000000000000000000000000001"
    operator = 2

    acl.grantPermissionP(
        manager,
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        encode_permission_params([Param(0, Op.EQ, operator + 1)]),
        {"from": voting},
    )

    CALLDATA = create_calldata([(operator, manager)])
    with reverts("MANAGER_HAS_NO_ROLE"):
        deactivate_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, deactivate_node_operators_factory, node_operators_registry, acl):
    "Must create correct EVMScript if all requirements are met"
    input_params = [(id, manager) for id, manager in enumerate(MANAGERS)]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    evm_script = deactivate_node_operators_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    scripts = []
    for input_param in input_params:
        scripts.append(
            (
                node_operators_registry.address,
                node_operators_registry.deactivateNodeOperator.encode_input(input_param[0]),
            )
        )
        scripts.append(
            (
                acl.address,
                acl.revokePermission.encode_input(
                    input_param[1],
                    node_operators_registry,
                    web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                ),
            )
        )
    expected_evm_script = encode_call_script(scripts)

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(node_operators_registry, deactivate_node_operators_factory):
    "Must decode EVMScript call data correctly"
    input_params = [(id, manager) for id, manager in enumerate(MANAGERS)]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert deactivate_node_operators_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
