from brownie import accounts, reverts
from eth_abi import encode_single
from utils.evm_script import encode_call_script


def test_validate_permissions_empty_payload(evm_script_permissions):
    with reverts("EMPTY_PERMISSIONS"):
        evm_script_permissions.validatePermissions(b"")


def test_validate_permissions_invalid_length(evm_script_permissions):
    with reverts("INVALID_PERMISSIONS_LEGNTH"):
        evm_script_permissions.validatePermissions("0xaaffccee001122")


def test_validate_permissions(evm_script_permissions):
    method_id = "11223344"
    evm_script_permissions.validatePermissions(accounts[1].address + method_id)


def test_can_execute_empty_permissions(evm_script_permissions):
    with reverts("EMPTY_PERMISSIONS"):
        evm_script_permissions.canExecuteEVMScript(b"", b"")


def test_can_execute_invalid_permissions_length(evm_script_permissions):
    with reverts("INVALID_PERMISSIONS_LEGNTH"):
        evm_script_permissions.canExecuteEVMScript("0xffee", b"")


def test_can_execute_empty_evm_script(
    evm_script_permissions, node_operators_registry_stub
):
    permissions = (
        node_operators_registry_stub.address
        + node_operators_registry_stub.setNodeOperatorStakingLimit.signature[2:]
    )
    with reverts("EMPTY_EVM_SCRIPT"):
        evm_script_permissions.canExecuteEVMScript(permissions, b"")


def test_can_execute_evm_script(
    evm_script_permissions, node_operators_registry_stub, bytes_utils
):
    permissions = (
        node_operators_registry_stub.address
        + node_operators_registry_stub.setNodeOperatorStakingLimit.signature[2:]
        + node_operators_registry_stub.address[2:]
        + node_operators_registry_stub.getNodeOperator.signature[2:]
    )

    evm_script_calls = [
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                1, 200
            ),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.getNodeOperator.encode_input(1, False),
        ),
        (
            node_operators_registry_stub.address,
            node_operators_registry_stub.setRewardAddress.encode_input(accounts[1]),
        ),
    ]

    evm_script = encode_call_script([evm_script_calls[0]])
    invalid_evm_script = "0x1122334455"

    assert not evm_script_permissions.canExecuteEVMScript(
        permissions, invalid_evm_script
    )
    # apply first permission in the list
    assert evm_script_permissions.canExecuteEVMScript(
        permissions, encode_call_script([evm_script_calls[0]])
    )
    # apply second permission in the list
    assert evm_script_permissions.canExecuteEVMScript(
        permissions, encode_call_script([evm_script_calls[1]])
    )

    # apply both permissions in the list in reverse order
    assert evm_script_permissions.canExecuteEVMScript(
        permissions, encode_call_script([evm_script_calls[1], evm_script_calls[0]])
    )

    # has no rights to run one method
    assert not evm_script_permissions.canExecuteEVMScript(
        permissions,
        encode_call_script(
            [evm_script_calls[1], evm_script_calls[0], evm_script_calls[2]]
        ),
    )

    # has no rights only one method
    assert not evm_script_permissions.canExecuteEVMScript(
        permissions, encode_call_script([evm_script_calls[2]])
    )


def encode_set_node_operator_staking_limit_calldata(node_operator_id, staking_limit):
    return (
        "0x"
        + encode_single("(uint256,uint256)", [node_operator_id, staking_limit]).hex()
    )
