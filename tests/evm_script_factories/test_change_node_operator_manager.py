import pytest
from eth_abi import encode_single
from brownie import reverts, ChangeNodeOperatorManagers

from utils.evm_script import encode_call_script


@pytest.fixture(scope="module")
def update_target_validator_limits_factory(owner, node_operators_registry):
    return ChangeNodeOperatorManagers.deploy(
        owner, node_operators_registry, {"from": owner}
    )


def test_deploy(node_operators_registry, owner, update_target_validator_limits_factory):
    "Must deploy contract with correct data"
    assert update_target_validator_limits_factory.trustedCaller() == owner
    assert (
        update_target_validator_limits_factory.nodeOperatorsRegistry()
        == node_operators_registry
    )


def test_create_evm_script_called_by_stranger(
    stranger, update_target_validator_limits_factory
):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALL_DATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        update_target_validator_limits_factory.createEVMScript(
            stranger, EVM_SCRIPT_CALL_DATA
        )


def test_non_sorted_calldata(owner, update_target_validator_limits_factory):
    "Must revert with message 'NODE_OPERATORS_IS_NOT_SORTED' when operator ids isn't sorted"

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,bool,uint256)[])", [[(1, True, 1), (0, False, 2)]]
            ).hex()
        )
        update_target_validator_limits_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )

    with reverts("NODE_OPERATORS_IS_NOT_SORTED"):
        NON_SORTED_CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,bool,uint256)[])", [[(0, True, 1), (0, True, 2)]]
            ).hex()
        )
        update_target_validator_limits_factory.createEVMScript(
            owner, NON_SORTED_CALL_DATA
        )


def test_operator_id_out_of_range(
    owner, update_target_validator_limits_factory, node_operators_registry
):
    "Must revert with message 'NODE_OPERATOR_INDEX_OUT_OF_RANGE' when operator id gt operators count"

    with reverts("NODE_OPERATOR_INDEX_OUT_OF_RANGE"):
        node_operators_count = node_operators_registry.getNodeOperatorsCount()
        CALL_DATA = (
            "0x"
            + encode_single(
                "((uint256,bool,uint256)[])",
                [[(node_operators_count, True, 1)]],
            ).hex()
        )
        update_target_validator_limits_factory.createEVMScript(owner, CALL_DATA)


def test_create_evm_script(
    owner,
    update_target_validator_limits_factory,
    node_operators_registry,
):
    "Must create correct EVMScript if all requirements are met"

    input_params = [(0, True, 1), (1, True, 1)]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,bool,uint256)[])", [input_params]).hex()
    )
    evm_script = update_target_validator_limits_factory.createEVMScript(
        owner, EVM_SCRIPT_CALL_DATA
    )
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.updateTargetValidatorsLimits.encode_input(
                    input_param[0], input_param[1], input_param[2]
                ),
            )
            for input_param in input_params
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(
    node_operators_registry, update_target_validator_limits_factory
):
    "Must decode EVMScript call data correctly"
    input_params = [(0, True, 1), (1, True, 1)]

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,bool,uint256)[])", [input_params]).hex()
    )
    assert (
        update_target_validator_limits_factory.decodeEVMScriptCallData(
            EVM_SCRIPT_CALL_DATA
        )
        == input_params
    )
