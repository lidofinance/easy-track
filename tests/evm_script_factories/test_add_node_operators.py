import pytest
from eth_abi import encode
from brownie import reverts, AddNodeOperators, web3, ZERO_ADDRESS

from utils.evm_script import encode_call_script
from utils.permission_parameters import Op, Param, encode_permission_params

OPERATOR_NAMES = [
    "Name 1",
    "Name 2",
]

REWARD_ADDRESSES = [
    "0x0000000000000000000000000000000000000001",
    "0x0000000000000000000000000000000000000002",
]

MANAGERS = [
    "0x0000000000000000000000000000000000000003",
    "0x0000000000000000000000000000000000000004",
]


def create_calldata(data):
    return (
        "0x"
        + encode(
            ["uint256", "(string,address,address)[]"],
            data,
        ).hex()
    )


@pytest.fixture(scope="module")
def add_node_operators_factory(owner, node_operators_registry, acl, steth):
    return AddNodeOperators.deploy(owner, node_operators_registry, acl, steth, {"from": owner})


def test_deploy(node_operators_registry, owner, acl, add_node_operators_factory):
    "Must deploy contract with correct data"
    assert add_node_operators_factory.trustedCaller() == owner
    assert add_node_operators_factory.nodeOperatorsRegistry() == node_operators_registry
    assert add_node_operators_factory.acl() == acl


def test_create_evm_script_called_by_stranger(stranger, add_node_operators_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        add_node_operators_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_node_operators_count(owner, add_node_operators_factory):
    "Must revert with message 'NODE_OPERATORS_COUNT_MISMATCH' when node operators registry operators count passed wrong"

    with reverts("NODE_OPERATORS_COUNT_MISMATCH"):
        CALLDATA = create_calldata(
            [0, [(OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0])]],
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_empty_calldata(owner, add_node_operators_factory, node_operators_registry):
    no_count = node_operators_registry.getNodeOperatorsCount()
    with reverts("EMPTY_CALLDATA"):
        EMPTY_CALLDATA = create_calldata([0, []])
        add_node_operators_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_manager_has_duplicate(owner, add_node_operators_factory, node_operators_registry):
    "Must revert with message 'MANAGER_ADDRESSES_HAS_DUPLICATE' when menager address has duplicate"
    no_count = node_operators_registry.getNodeOperatorsCount()
    with reverts("MANAGER_ADDRESSES_HAS_DUPLICATE"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
                    (OPERATOR_NAMES[1], REWARD_ADDRESSES[1], MANAGERS[0]),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_manager_already_has_permission(owner, add_node_operators_factory, node_operators_registry, acl, voting):
    "Must revert with message 'MANAGER_ALREADY_HAS_ROLE' when manager has MANAGE_SIGNING_KEYS role"
    no_count = node_operators_registry.getNodeOperatorsCount()

    acl.grantPermission(
        MANAGERS[0],
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        {"from": voting},
    )

    with reverts("MANAGER_ALREADY_HAS_ROLE"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_manager_already_has_permission_for_node_operator(
    owner, add_node_operators_factory, node_operators_registry, acl, voting
):
    "Must revert with message 'MANAGER_ALREADY_HAS_ROLE' when manager has MANAGE_SIGNING_KEYS role with parameter"
    no_count = node_operators_registry.getNodeOperatorsCount()

    acl.grantPermissionP(
        MANAGERS[0],
        node_operators_registry,
        web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
        encode_permission_params([Param(0, Op.EQ, 0)]),
        {"from": voting},
    )
    with reverts("MANAGER_ALREADY_HAS_ROLE"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_zero_manager(owner, add_node_operators_factory, node_operators_registry):
    "Must revert with message 'ZERO_MANAGER_ADDRESS' when manager is zero address"
    no_count = node_operators_registry.getNodeOperatorsCount()

    with reverts("ZERO_MANAGER_ADDRESS"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], ZERO_ADDRESS),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_zero_reward_address(owner, add_node_operators_factory, node_operators_registry):
    "Must revert with message 'ZERO_REWARD_ADDRESS' when reward address is zero address"
    no_count = node_operators_registry.getNodeOperatorsCount()

    with reverts("ZERO_REWARD_ADDRESS"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], ZERO_ADDRESS, MANAGERS[0]),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_lido_reward_address(owner, add_node_operators_factory, node_operators_registry, steth):
    "Must revert with message 'LIDO_REWARD_ADDRESS' when reward address is lido address"
    no_count = node_operators_registry.getNodeOperatorsCount()

    with reverts("LIDO_REWARD_ADDRESS"):
        CALLDATA = create_calldata(
            [
                no_count,
                [
                    (OPERATOR_NAMES[0], steth.address, MANAGERS[0]),
                ],
            ]
        )
        add_node_operators_factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, add_node_operators_factory, node_operators_registry, acl):
    "Must create correct EVMScript if all requirements are met"

    input_params = [
        (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
        (OPERATOR_NAMES[1], REWARD_ADDRESSES[1], MANAGERS[1]),
    ]

    no_count = node_operators_registry.getNodeOperatorsCount()
    CALLDATA = create_calldata(
        [
            no_count,
            input_params,
        ]
    )
    evm_script = add_node_operators_factory.createEVMScript(owner, CALLDATA)

    no_count = node_operators_registry.getNodeOperatorsCount()

    scripts = []
    for id, input_param in enumerate(input_params):
        scripts.append(
            (
                node_operators_registry.address,
                node_operators_registry.addNodeOperator.encode_input(input_param[0], input_param[1]),
            )
        )
        scripts.append(
            (
                acl.address,
                acl.grantPermissionP.encode_input(
                    input_param[2],
                    node_operators_registry,
                    web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                    encode_permission_params([Param(0, Op.EQ, no_count + id)]),
                ),
            )
        )
    expected_evm_script = encode_call_script(scripts)

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(node_operators_registry, add_node_operators_factory):
    "Must decode EVMScript call data correctly"
    no_count = node_operators_registry.getNodeOperatorsCount()
    input_params = [
        no_count,
        [
            (OPERATOR_NAMES[0], REWARD_ADDRESSES[0], MANAGERS[0]),
            (OPERATOR_NAMES[1], REWARD_ADDRESSES[1], MANAGERS[1]),
        ],
    ]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert add_node_operators_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
