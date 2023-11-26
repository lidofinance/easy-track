import pytest
from eth_abi import encode_single
from brownie import reverts, ChangeNodeOperatorManagers, web3, convert, ZERO_ADDRESS

from utils.evm_script import encode_call_script

MANAGERS = [
    "0x0000000000000000000000000000000000000001",
    "0x0000000000000000000000000000000000000002",
]

NEW_MANAGERS = [
    "0x0000000000000000000000000000000000000003",
    "0x0000000000000000000000000000000000000004",
]


@pytest.fixture(scope="module")
def change_node_operator_managers_factory(owner, node_operators_registry, acl, voting):
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
            [convert.to_uint((0 << 248) + (1 << 240) + id, "uint256")],
            {"from": voting},
        )

    return ChangeNodeOperatorManagers.deploy(
        owner, node_operators_registry, acl, {"from": owner}
    )


def test_deploy(node_operators_registry, owner, change_node_operator_managers_factory):
    "Must deploy contract with correct data"
    assert change_node_operator_managers_factory.trustedCaller() == owner
    assert (
        change_node_operator_managers_factory.nodeOperatorsRegistry()
        == node_operators_registry
    )


def test_create_evm_script_called_by_stranger(
    stranger, change_node_operator_managers_factory
):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALL_DATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        change_node_operator_managers_factory.createEVMScript(
            stranger, EVM_SCRIPT_CALL_DATA
        )


def test_empty_calldata(owner, change_node_operator_managers_factory):
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = (
            "0x"
            + encode_single(
                "((uint256,address,address)[])",
                [[]],
            ).hex()
        )
        change_node_operator_managers_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_non_sorted_calldata(owner, change_node_operator_managers_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address,address)[])",
                [
                    [
                        (1, MANAGERS[1], NEW_MANAGERS[1]),
                        (0, MANAGERS[0], NEW_MANAGERS[0]),
                    ]
                ],
            ).hex()
        )
        change_node_operator_managers_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address,address)[])",
                [
                    [
                        (0, MANAGERS[0], NEW_MANAGERS[0]),
                        (0, MANAGERS[0], NEW_MANAGERS[1]),
                    ]
                ],
            ).hex()
        )
        change_node_operator_managers_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )


def test_operator_id_out_of_range(
    owner, change_node_operator_managers_factory, node_operators_registry
):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address,address)[])",
                [[(node_operators_count, MANAGERS[0], NEW_MANAGERS[0])]],
            ).hex()
        )
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_duplicate_manager(owner, change_node_operator_managers_factory):
    "Must revert with message 'MANAGER_ADDRESSES_HAS_DUPLICATE' when new maanger has duplicates"

    with reverts("MANAGER_ADDRESSES_HAS_DUPLICATE"):
        CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,address,address)[])",
                [
                    [
                        (0, MANAGERS[1], NEW_MANAGERS[1]),
                        (1, MANAGERS[0], NEW_MANAGERS[1]),
                    ]
                ],
            ).hex()
        )
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_manager_has_no_role(owner, change_node_operator_managers_factory):
    "Must revert with message 'OLD_MANAGER_HAS_NO_ROLE' when manager has no MANAGE_SIGNING_KEYS role"

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(2, MANAGERS[0], NEW_MANAGERS[0])]]
        ).hex()
    )
    with reverts("OLD_MANAGER_HAS_NO_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_manager_has_another_role_operator(
    owner, change_node_operator_managers_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'OLD_MANAGER_HAS_NO_ROLE' when manager has MANAGE_SIGNING_KEYS role with wrong param operator"

    manager = "0x0000000000000000000000000000000000000001"
    new_manager = "0x0000000000000000000000000000000000000005"
    operator = 2

    acl.grantPermissionP(
        manager,
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        [convert.to_uint((0 << 248) + (2 << 240) + operator, "uint256")],
        {"from": voting},
    )

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(operator, manager, new_manager)]]
        ).hex()
    )
    with reverts("OLD_MANAGER_HAS_NO_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_manager_has_role_for_another_operator(
    owner, change_node_operator_managers_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'OLD_MANAGER_HAS_NO_ROLE' when manager has MANAGE_SIGNING_KEYS role with wrong param operator"

    manager = "0x0000000000000000000000000000000000000001"
    new_manager = "0x0000000000000000000000000000000000000005"
    operator = 2

    acl.grantPermissionP(
        manager,
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        [convert.to_uint((0 << 248) + (1 << 240) + operator + 1, "uint256")],
        {"from": voting},
    )

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(operator, manager, new_manager)]]
        ).hex()
    )
    with reverts("OLD_MANAGER_HAS_NO_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_old_manager_has_general_permission(
    owner, change_node_operator_managers_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'OLD_MANAGER_HAS_NO_ROLE' when manager has general MANAGE_SIGNING_KEYS role"

    manager = "0x0000000000000000000000000000000000000001"
    new_manager = "0x0000000000000000000000000000000000000005"
    operator = 2

    acl.grantPermission(
        manager,
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        {"from": voting},
    )

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(operator, manager, new_manager)]]
        ).hex()
    )
    with reverts("OLD_MANAGER_HAS_NO_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_zero_manager(owner, change_node_operator_managers_factory):
    "Must revert with message 'ZERO_MANAGER_ADDRESS' when manager is zero address"

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(0, MANAGERS[0], ZERO_ADDRESS)]]
        ).hex()
    )
    with reverts("ZERO_MANAGER_ADDRESS"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_new_manager_has_permission(owner, change_node_operator_managers_factory):
    "Must revert with message 'MANAGER_ALREADY_HAS_ROLE' when new manager already has permission"

    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(0, MANAGERS[0], MANAGERS[1])]]
        ).hex()
    )
    with reverts("MANAGER_ALREADY_HAS_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_new_manager_has_general_permission(
    owner, change_node_operator_managers_factory, acl, voting, node_operators_registry
):
    "Must revert with message 'MANAGER_ALREADY_HAS_ROLE' when new manager already has general permission"
    acl.grantPermission(
        NEW_MANAGERS[0],
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        {"from": voting},
    )
    CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,address,address)[])", [[(0, MANAGERS[0], NEW_MANAGERS[0])]]
        ).hex()
    )
    with reverts("MANAGER_ALREADY_HAS_ROLE"):
        change_node_operator_managers_factory.createEVMScript(owner, CALL_DATA)


def test_create_evm_script(
    owner,
    change_node_operator_managers_factory,
    node_operators_registry,
    acl,
):
    "Must create correct EVMScript if all requirements are met"

    input_params = [
        (0, MANAGERS[0], NEW_MANAGERS[0]),
        (1, MANAGERS[1], NEW_MANAGERS[1]),
    ]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,address,address)[])", [input_params]).hex()
    )
    evm_script = change_node_operator_managers_factory.createEVMScript(
        owner, EVM_SCRIPT_CALL_DATA
    )

    scripts = []
    for input_param in input_params:
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
        scripts.append(
            (
                acl.address,
                acl.grantPermissionP.encode_input(
                    input_param[2],
                    node_operators_registry,
                    web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                    [
                        convert.to_uint(
                            (0 << 248) + (1 << 240) + input_param[0], "uint256"
                        )
                    ],
                ),
            )
        )
    expected_evm_script = encode_call_script(scripts)
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(
    node_operators_registry, change_node_operator_managers_factory
):
    "Must decode EVMScript call data correctly"
    input_params = [
        (0, MANAGERS[0], NEW_MANAGERS[0]),
        (1, MANAGERS[1], NEW_MANAGERS[1]),
    ]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,address,address)[])", [input_params]).hex()
    )
    assert (
        change_node_operator_managers_factory.decodeEVMScriptCallData(
            EVM_SCRIPT_CALL_DATA
        )
        == input_params
    )
