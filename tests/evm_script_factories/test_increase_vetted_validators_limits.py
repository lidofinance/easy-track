import pytest
from eth_abi import encode_single
from brownie import reverts, IncreaseVettedValidatorsLimit, convert

from utils.evm_script import encode_call_script


signing_keys = {
    "pubkeys": [
        "8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7",
        "884b147305bcd9fce3a1cc12e8f893c6356c1780688286277656e1ba724a3fde49262c98503141c0925b344a8ccea9ca",
        "952ff22cf4a5f9708d536acb2170f83c137301515df5829adc28c265373487937cc45e8f91743caba0b9ebd02b3b664f",
    ],
    "signatures": [
        "ad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660",
        "9794e7871dc766c2139f9476234bc29784e13b51e859445044d2a5a9df8bc072d9c51c51ee69490ce37bdfc7cf899af2166b0710d620a87398d5ec7da06c9f7eb27f1d729973efd60052dbd4cb7f43ff6b141af4d0a0a980b60f663f39bf7844",
        "90111fb6944ff8b56eb0858c1deb91f41c8c631573f4c821663d7079e5e78903d67fa1c4a4ed358378f16a2b7ec524c5196b1a1eae35b01dca1df74535f45d6bd1960164a41425b2a289d4bb5c837049acf5871a0ed23598df42f6234276f6e2",
    ],
}


@pytest.fixture(scope="module")
def increase_vetted_validators_limit_factory(owner, node_operators_registry):
    return IncreaseVettedValidatorsLimit.deploy(
        node_operators_registry, {"from": owner}
    )


def test_deploy(node_operators_registry, increase_vetted_validators_limit_factory):
    "Must deploy contract with correct data"
    assert (
        increase_vetted_validators_limit_factory.nodeOperatorsRegistry()
        == node_operators_registry
    )


def test_create_evm_script_called_by_stranger(
    stranger, increase_vetted_validators_limit_factory
):
    "Must revert with message 'CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER' if creator isn't node operators reward address or manager"
    EVM_SCRIPT_CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,uint256))",
            [(0, 1)],
        ).hex()
    )
    with reverts("CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER"):
        increase_vetted_validators_limit_factory.createEVMScript(
            stranger, EVM_SCRIPT_CALL_DATA
        )


def test_create_evm_script_called_when_operator_disabled(
    increase_vetted_validators_limit_factory, agent, node_operators_registry
):
    "Must revert with message 'NODE_OPERATOR_DISABLED' if called when operator disabled"
    
    node_operators_registry.deactivateNodeOperator(0, {"from": agent})
    no = node_operators_registry.getNodeOperator(0, True)

    EVM_SCRIPT_CALL_DATA = (
        "0x"
        + encode_single(
            "((uint256,uint256))",
            [(0, 1)],
        ).hex()
    )
    with reverts("NODE_OPERATOR_DISABLED"):
        increase_vetted_validators_limit_factory.createEVMScript(
            no["rewardAddress"], EVM_SCRIPT_CALL_DATA
        )


def test_revert_on_not_enough_signing_keys(
    increase_vetted_validators_limit_factory, node_operators_registry
):
    "Must revert with message 'NOT_ENOUGH_SIGNING_KEYS' when node operator has not enough keys"
    no = node_operators_registry.getNodeOperator(0, True)

    with reverts("NOT_ENOUGH_SIGNING_KEYS"):
        CALL_DATA = "0x" + encode_single("((uint256,uint256))", [(0, 100000)]).hex()
        increase_vetted_validators_limit_factory.createEVMScript(
            no["rewardAddress"], CALL_DATA
        )


def test_revert_on_new_value_is_too_low(
    increase_vetted_validators_limit_factory, node_operators_registry
):
    "Must revert with message 'STAKING_LIMIT_TOO_LOW' when new value is too low"
    no = node_operators_registry.getNodeOperator(0, True)

    with reverts("STAKING_LIMIT_TOO_LOW"):
        CALL_DATA = "0x" + encode_single("((uint256,uint256))", [(0, 0)]).hex()
        increase_vetted_validators_limit_factory.createEVMScript(
            no["rewardAddress"], CALL_DATA
        )


def test_create_evm_script_from_reward_address(
    increase_vetted_validators_limit_factory,
    node_operators_registry,
):
    "Must create correct EVMScript if all requirements are met"

    no = node_operators_registry.getNodeOperator(0, True)
    node_operators_registry.addSigningKeysOperatorBH(
        0,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": no["rewardAddress"]},
    )
    input_params = (0, no["totalVettedValidators"] + len(signing_keys["pubkeys"]))

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,uint256))", [input_params]).hex()
    )
    evm_script = increase_vetted_validators_limit_factory.createEVMScript(
        no["rewardAddress"], EVM_SCRIPT_CALL_DATA
    )
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.setNodeOperatorStakingLimit.encode_input(
                    input_params[0], input_params[1]
                ),
            )
        ]
    )
    assert evm_script == expected_evm_script


def test_create_evm_script_from_manager(
    increase_vetted_validators_limit_factory,
    node_operators_registry,
    acl,
    voting
):
    "Must create correct EVMScript if all requirements are met"
    no_manager = "0x1f9090aae28b8a3dceadf281b0f12828e676c327"

    no = node_operators_registry.getNodeOperator(0, True)
    # permission parameter
    id8 = 0  # first arg
    op8 = 1  # EQ
    value240 = 0
    permission_param = convert.to_uint(
        (id8 << 248) + (op8 << 240) + value240, "uint256"
    )

    acl.grantPermissionP(no_manager, node_operators_registry, node_operators_registry.MANAGE_SIGNING_KEYS(), [permission_param], {"from": voting})

    node_operators_registry.addSigningKeysOperatorBH(
        0,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": no_manager},
    )
    input_params = (0, no["totalVettedValidators"] + len(signing_keys["pubkeys"]))

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,uint256))", [input_params]).hex()
    )
    evm_script = increase_vetted_validators_limit_factory.createEVMScript(
        no_manager, EVM_SCRIPT_CALL_DATA
    )
    expected_evm_script = encode_call_script(
        [
            (
                node_operators_registry.address,
                node_operators_registry.setNodeOperatorStakingLimit.encode_input(
                    input_params[0], input_params[1]
                ),
            )
        ]
    )
    assert evm_script == expected_evm_script



def test_decode_evm_script_call_data(
    node_operators_registry, increase_vetted_validators_limit_factory
):
    "Must decode EVMScript call data correctly"
    input_params = (0, 1)

    EVM_SCRIPT_CALL_DATA = (
        "0x" + encode_single("((uint256,uint256))", [input_params]).hex()
    )
    assert (
        increase_vetted_validators_limit_factory.decodeEVMScriptCallData(
            EVM_SCRIPT_CALL_DATA
        )
        == input_params
    )
