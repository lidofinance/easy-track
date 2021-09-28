import pytest
from brownie import ZERO_ADDRESS
from brownie.convert import to_bytes
from utils.evm_script import encode_call_script


@pytest.fixture(scope="session", params=range(5))
def valid_permissions(request):
    """Returns a valid permissions value."""
    zero_permission = to_bytes(ZERO_ADDRESS + "aabbccdd", "bytes")
    deadbeef_permission = b"\xde\xad\xbe\xef" * 6
    feedface_permission = bytes.fromhex("feedface") * 5 + bytes.fromhex(
        "baddcafe"
    )  # different bytes for the selector

    assert len(deadbeef_permission) == 24

    permissions_list = [
        zero_permission,
        zero_permission * 3,  # Duplicates allowed
        deadbeef_permission,
        zero_permission + deadbeef_permission,
        zero_permission + deadbeef_permission + feedface_permission,
    ]
    return permissions_list[request.param]


@pytest.fixture(scope="session", params=range(5))
def invalid_permissions(request):
    base_val = to_bytes(ZERO_ADDRESS + "aabbccdd", "bytes")  # valid
    permissions_list = [
        b"",  # Empty permissions
        "0x11223344556677889911",  # Permissions length too short
        base_val[:-1],  # Permissions length 1 byte too short
        base_val + b"\xee",  # Permissions length too long for 1 permission
        (base_val * 3)[:-1],  # Permissions length too short 3 permissions
    ]
    return permissions_list[request.param]


@pytest.fixture(scope="session")
def create_permission():
    def method(contract, method):
        return contract.address + getattr(contract, method).signature[2:]

    return method


@pytest.fixture(scope="module")
def node_operators_registry_stub_permissions(
    create_permission, node_operators_registry_stub
):
    def method(method_names):
        permissions = {
            "setNodeOperatorStakingLimit": create_permission(
                node_operators_registry_stub, "setNodeOperatorStakingLimit"
            ),
            "getNodeOperator": create_permission(
                node_operators_registry_stub, "getNodeOperator"
            ),
            "setRewardAddress": create_permission(
                node_operators_registry_stub, "setRewardAddress"
            ),
        }
        result = "0x"
        for method_name in method_names:
            result += permissions[method_name][2:]
        return result

    return method


@pytest.fixture(scope="module")
def node_operators_registry_stub_calldata(accounts, node_operators_registry_stub):
    def method(method_names):
        calldata = {
            "setNodeOperatorStakingLimit": (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setNodeOperatorStakingLimit.encode_input(
                    1, 200
                ),
            ),
            "getNodeOperator": (
                node_operators_registry_stub.address,
                node_operators_registry_stub.getNodeOperator.encode_input(1, False),
            ),
            "setRewardAddress": (
                node_operators_registry_stub.address,
                node_operators_registry_stub.setRewardAddress.encode_input(accounts[1]),
            ),
        }
        evm_script_calls = []
        for method_name in method_names:
            evm_script_calls.append(calldata[method_name])
        return encode_call_script(evm_script_calls)

    return method


@pytest.fixture(scope="module", params=range(3))
def permissions_with_not_allowed_calldata(
    request,
    node_operators_registry_stub_permissions,
    node_operators_registry_stub_calldata,
):
    has_all_except_one_permission = (
        node_operators_registry_stub_permissions(
            ["getNodeOperator", "setRewardAddress"]
        ),
        node_operators_registry_stub_calldata(
            ["setNodeOperatorStakingLimit", "getNodeOperator", "getNodeOperator"]
        ),
    )
    has_no_required_permission_one_call = (
        node_operators_registry_stub_permissions(
            ["getNodeOperator", "setRewardAddress"]
        ),
        node_operators_registry_stub_calldata(["setNodeOperatorStakingLimit"]),
    )
    has_no_required_permission_many_calls = (
        node_operators_registry_stub_permissions(["getNodeOperator"]),
        node_operators_registry_stub_calldata(
            ["setRewardAddress", "setNodeOperatorStakingLimit"]
        ),
    )
    test_cases = [
        has_all_except_one_permission,
        has_no_required_permission_one_call,
        has_no_required_permission_many_calls,
    ]
    return test_cases[request.param]


@pytest.fixture(scope="module", params=range(4))
def permissions_with_allowed_calldata(
    request,
    node_operators_registry_stub_permissions,
    node_operators_registry_stub_calldata,
):
    all_permissions = node_operators_registry_stub_permissions(
        ["setNodeOperatorStakingLimit", "getNodeOperator", "setRewardAddress"]
    )
    many_permissions_many_evm_scripts = (
        all_permissions,
        node_operators_registry_stub_calldata(
            ["setNodeOperatorStakingLimit", "setRewardAddress"]
        ),
    )
    many_permissions_one_evm_script = (
        all_permissions,
        node_operators_registry_stub_calldata(["getNodeOperator"]),
    )
    one_permission_many_evm_scripts = (
        node_operators_registry_stub_permissions(["getNodeOperator"]),
        node_operators_registry_stub_calldata(["getNodeOperator", "getNodeOperator"]),
    )
    one_permission_one_evm_script = (
        node_operators_registry_stub_permissions(["setRewardAddress"]),
        node_operators_registry_stub_calldata(["setRewardAddress"]),
    )
    data = [
        many_permissions_many_evm_scripts,
        many_permissions_one_evm_script,
        one_permission_many_evm_scripts,
        one_permission_one_evm_script,
    ]
    return data[request.param]


def test_can_execute_evm_script_zero_length_permissions(evm_script_permissions_wrapper):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(b"", b"")


def test_can_execute_evm_script_wrong_permissions_length(
    evm_script_permissions_wrapper,
):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript("0x0011223344", b"")


def test_can_execute_evm_script_evm_script_too_short(
    evm_script_permissions_wrapper, valid_permissions
):
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(
        valid_permissions, b""
    )


def test_can_execute_evm_script_has_permissions(
    evm_script_permissions_wrapper, permissions_with_allowed_calldata
):
    permission, calldata = permissions_with_allowed_calldata
    assert evm_script_permissions_wrapper.canExecuteEVMScript(permission, calldata)


def test_can_execute_evm_script_has_no_permissions(
    evm_script_permissions_wrapper, permissions_with_not_allowed_calldata
):
    permission, calldata = permissions_with_not_allowed_calldata
    assert not evm_script_permissions_wrapper.canExecuteEVMScript(permission, calldata)


def test_is_valid_permissions_valid(evm_script_permissions_wrapper, valid_permissions):
    assert evm_script_permissions_wrapper.isValidPermissions(valid_permissions)


def test_is_valid_permissions_invalid(
    evm_script_permissions_wrapper, invalid_permissions
):
    assert not evm_script_permissions_wrapper.isValidPermissions(invalid_permissions)
