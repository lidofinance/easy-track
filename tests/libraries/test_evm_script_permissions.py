import pytest
import brownie
from eth_abi import encode_single
from utils.evm_script import encode_call_script


@pytest.fixture(scope="module")
def valid_permissions():
    return brownie.ZERO_ADDRESS + "aabbccdd"


def test_can_execute_evm_script_zero_length_permissions(evm_script_permissions_wrapper):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(b"", b"")


def test_can_execute_evm_script_wrong_permissions_length(
    evm_script_permissions_wrapper,
):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(b"0011223344", b"")


def test_can_execute_evm_script_evm_script_too_short(
    evm_script_permissions_wrapper, valid_permissions
):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(
        valid_permissions, b""
    )


def test_can_execute_evm_script(
    accounts, evm_script_permissions_wrapper, node_operators_registry_stub
):
    permissions, evm_scripts_calldata = create_permissions_with_evm_scripts_calldata(
        accounts, node_operators_registry_stub
    )
    all_permissions = permissions[1] + permissions[0][2:] + permissions[2][2:]

    # many permissions many evm script
    assert evm_script_permissions_wrapper.canExecuteEVMScript(
        all_permissions,
        encode_call_script(evm_scripts_calldata[:2]),
    )

    # many permissions one evm script
    assert evm_script_permissions_wrapper.canExecuteEVMScript(
        all_permissions,
        encode_call_script([evm_scripts_calldata[2]]),
    )

    # one permission one many evm scripts
    assert evm_script_permissions_wrapper.canExecuteEVMScript(
        permissions[1],
        encode_call_script([evm_scripts_calldata[1], evm_scripts_calldata[1]]),
    )

    # has no one permission
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(
        permissions[1] + permissions[2][2:], encode_call_script(evm_scripts_calldata)
    )


def test_is_valid_permissions(evm_script_permissions_wrapper, valid_permissions):
    # empty permissions
    assert not evm_script_permissions_wrapper.isValidPermissions(b"")

    # wrong permissions length
    assert not evm_script_permissions_wrapper.isValidPermissions(
        b"11223344556677889911"
    )

    # correct permissions
    assert evm_script_permissions_wrapper.isValidPermissions(valid_permissions)


def create_permissions_with_evm_scripts_calldata(
    accounts, node_operators_registry_stub
):
    permissions = [
        node_operators_registry_stub.address
        + node_operators_registry_stub.setNodeOperatorStakingLimit.signature[2:],
        node_operators_registry_stub.address
        + node_operators_registry_stub.getNodeOperator.signature[2:],
        node_operators_registry_stub.address
        + node_operators_registry_stub.setRewardAddress.signature[2:],
    ]

    evm_scripts_calldata = [
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
    return (permissions, evm_scripts_calldata)
