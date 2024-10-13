import pytest
from eth_abi import encode
from brownie import reverts, web3, interface

from utils.test_helpers import set_account_balance

table = [
    {
        "address": "0x000000000000000000000000000000000000{:04}".format(i),
        "manager": "0x000000000000000000000000000000000000{:04}".format(i),
        "name": "Table " + str(i),
    }
    for i in range(1, 5)
]

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

no1 = 0
no2 = 1
no3 = 2
no4 = 3

name1 = table[no1]["name"]
name2 = table[no2]["name"]
name3 = table[no3]["name"]
name4 = table[no4]["name"]

manager1 = table[no1]["manager"]
manager2 = table[no2]["manager"]
manager3 = table[no3]["manager"]
manager4 = table[no4]["manager"]

address1 = table[no1]["address"]
address2 = table[no2]["address"]
address3 = table[no3]["address"]
address4 = table[no4]["address"]


@pytest.fixture(scope="module")
def simple_dvt(
    node_operators_registry,
    kernel,
    voting,
    locator,
    staking_router,
    agent,
    acl,
):
    nor_proxy = interface.AragonAppProxy(node_operators_registry)
    module_name = "simple-dvt-registry"
    name = web3.keccak(text=module_name).hex()
    simple_DVT_tx = kernel.newAppInstance(name, nor_proxy.implementation(), {"from": voting})

    simple_dvt_contract = interface.NodeOperatorsRegistry(simple_DVT_tx.new_contracts[0])

    simple_dvt_contract.initialize(locator, "0x01", 0, {"from": voting})

    staking_router.grantRole(web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex(), agent, {"from": agent})

    staking_router.addStakingModule("Simple DVT", simple_dvt_contract, 10_000, 500, 500, {"from": agent})

    acl.createPermission(
        agent,
        simple_dvt_contract,
        web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex(),
        agent,
        {"from": voting},
    )

    return simple_dvt_contract


def prepare_add_node_operator_calldata(count, name, address, manager):
    return (
        "0x"
        + encode(
            ["uint256", "(string,address,address)[]"],
            [count, [(name, address, manager)]],
        ).hex()
    )


def prepare_deactivate_node_operator_calldata(operator, manager):
    return "0x" + encode(["(uint256,address)[]"], [[(operator, manager)]]).hex()


def prepare_activate_node_operator_calldata(operator, manager):
    return "0x" + encode(["(uint256,address)[]"], [[(operator, manager)]]).hex()


def prepare_change_node_operator_manager_calldata(operator, old_manager, new_manager):
    return (
        "0x"
        + encode(
            ["(uint256,address,address)[]"],
            [[(operator, old_manager, new_manager)]],
        ).hex()
    )


def prepare_set_node_operator_name_calldata(operator, name):
    return "0x" + encode(["(uint256,string)[]"], [[(operator, name)]]).hex()


def prepare_set_node_operator_reward_address_calldata(operator, address):
    return "0x" + encode(["(uint256,address)[]"], [[(operator, address)]]).hex()


def prepare_update_target_validator_limits_calldata(id_operator, limit_mode, target_limits):
    return "0x" + encode(["(uint256,uint256,uint256)[]"], [[(id_operator, limit_mode, target_limits)]]).hex()


def prepare_set_vetted_validators_limit_calldata(id_operator, vetted_limit):
    return "0x" + encode(["(uint256,uint256)[]"], [[(id_operator, vetted_limit)]]).hex()


def prepare_increase_vetted_validators_limit_calldata(id_operator, vetted_limit):
    return "0x" + encode(["(uint256,uint256)"], [(id_operator, vetted_limit)]).hex()


def test_simple_dvt_scenario(
    simple_dvt,
    voting,
    commitee_multisig,
    et_contracts,
    acl,
    agent,
    easytrack_executor,
    easytrack_pair_executor_with_collision,
    add_node_operators_factory,
    activate_node_operators_factory,
    deactivate_node_operators_factory,
    set_node_operator_name_factory,
    set_node_operator_reward_address_factory,
    set_vetted_validators_limit_factory,
    change_node_operator_manager_factory,
    increase_vetted_validators_limit_factory,
):
    # Grant roles
    acl.grantPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.MANAGE_NODE_OPERATOR_ROLE(),
        {"from": agent},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.SET_NODE_OPERATOR_LIMIT_ROLE(),
        agent,
        {"from": voting},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.MANAGE_SIGNING_KEYS(),
        et_contracts.evm_script_executor,
        {"from": voting},
    )
    acl.createPermission(
        et_contracts.evm_script_executor,
        simple_dvt,
        simple_dvt.STAKING_ROUTER_ROLE(),
        agent,
        {"from": voting},
    )

    # 1) AddNodeOperators - AddNodeOperators -> NODE_OPERATORS_COUNT_MISMATCH
    # Add no1 address1 manager1 name1 v
    # Add no1 address1 manager1 name1 x
    add_node_operator_calldata = prepare_add_node_operator_calldata(0, name1, address1, manager1)

    easytrack_pair_executor_with_collision(
        reverts("NODE_OPERATORS_COUNT_MISMATCH"),
        [
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
        ],
    )

    # -) deactivate no1
    deactivate_node_operator_calldata = prepare_deactivate_node_operator_calldata(no1, manager1)

    easytrack_executor(
        commitee_multisig,
        deactivate_node_operators_factory,
        deactivate_node_operator_calldata,
    )

    # 2) ActivateNodeOperators - AddNodeOperators -> MANAGER_ALREADY_HAS_ROLE
    # Activate no1 address1 manager1 name1 v
    # Add      no2 address2 manager1 name2 x
    activate_node_operators_calldata = prepare_activate_node_operator_calldata(no1, manager1)
    add_node_operator_calldata = prepare_add_node_operator_calldata(1, name2, address2, manager1)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
        ],
    )

    # 3) ChangeNodeOperatorManagers - AddNodeOperators -> MANAGER_ALREADY_HAS_ROLE
    # change no1 address1 manager1->2 name1 v
    # add    no2 address2 manager2    name2 x
    change_node_operator_manager_calldata = prepare_change_node_operator_manager_calldata(no1, manager1, manager2)
    add_node_operator_calldata = prepare_add_node_operator_calldata(1, name2, address2, manager2)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
        ],
    )

    # 4) DeactivateNodeOperators - DeactivateNodeOperators
    # deactivate no1 address1 manager2 name1 v
    # deactivate no1 address1 manager2 name1 x
    deactivate_node_operator_calldata = prepare_deactivate_node_operator_calldata(no1, manager2)
    easytrack_pair_executor_with_collision(
        reverts("WRONG_OPERATOR_ACTIVE_STATE"),
        [
            (commitee_multisig, deactivate_node_operators_factory, deactivate_node_operator_calldata),
            (commitee_multisig, deactivate_node_operators_factory, deactivate_node_operator_calldata),
        ],
    )

    # 5) DeactivateNodeOperators - DeactivateNodeOperators -> WRONG_OPERATOR_ACTIVE_STATE
    # add      no2 address2 manager2 name2 v
    # activate no1 address1 manager2 name1 x
    add_node_operator_calldata = prepare_add_node_operator_calldata(1, name2, address2, manager2)
    activate_node_operators_calldata = prepare_activate_node_operator_calldata(no1, manager2)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
        ],
    )

    # 6) ActivateNodeOperators - ActivateNodeOperators -> WRONG_OPERATOR_ACTIVE_STATE
    # activate no1 address1 manager1 name1
    # activate no1 address1 manager1 name1
    activate_node_operators_calldata = prepare_activate_node_operator_calldata(no1, manager1)

    easytrack_pair_executor_with_collision(
        reverts("WRONG_OPERATOR_ACTIVE_STATE"),
        [
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
        ],
    )

    # -) deactivate no2
    deactivate_node_operator_calldata = prepare_deactivate_node_operator_calldata(no2, manager2)

    easytrack_executor(
        commitee_multisig,
        deactivate_node_operators_factory,
        deactivate_node_operator_calldata,
    )

    # 7) ChangeNodeOperatorManagers - ActivateNodeOperators -> MANAGER_ALREADY_HAS_ROLE
    # change   no1 address1 manager1->2 name1 v
    # activate no2 address2 manager2    name2 x
    change_node_operator_manager_calldata = prepare_change_node_operator_manager_calldata(no1, manager1, manager2)
    activate_node_operators_calldata = prepare_activate_node_operator_calldata(no2, manager2)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
        ],
    )

    # 8) SetNodeOperatorNames - SetNodeOperatorNames -> SAME_NAME
    # set no1 address1 manager2 name1->3 v
    # set no1 address1 manager2 name1->3 x
    set_node_operator_name_calldata = prepare_set_node_operator_name_calldata(no1, name3)

    easytrack_pair_executor_with_collision(
        reverts("SAME_NAME"),
        [
            (commitee_multisig, set_node_operator_name_factory, set_node_operator_name_calldata),
            (commitee_multisig, set_node_operator_name_factory, set_node_operator_name_calldata),
        ],
    )

    # 9) SetNodeOperatorRewardAddresses- SetNodeOperatorRewardAddresses -> SAME_REWARD_ADDRESS
    # set no1 address1->3 manager2 name3 v
    # set no1 address1->3 manager2 name3 x
    set_node_operator_reward_address_calldata = prepare_set_node_operator_reward_address_calldata(no1, address3)

    easytrack_pair_executor_with_collision(
        reverts("SAME_REWARD_ADDRESS"),
        [
            (commitee_multisig, set_node_operator_reward_address_factory, set_node_operator_reward_address_calldata),
            (commitee_multisig, set_node_operator_reward_address_factory, set_node_operator_reward_address_calldata),
        ],
    )

    # 10) AddNodeOperators - ChangeNodeOperatorManagers -> MANAGER_ALREADY_HAS_ROLE
    # add    no3 address1 manager3    name1 v
    # change no1 address3 manager2->3 name3 x
    add_node_operator_calldata = prepare_add_node_operator_calldata(2, name1, address1, manager3)
    change_node_operator_manager_calldata = prepare_change_node_operator_manager_calldata(no1, manager2, manager3)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, add_node_operators_factory, add_node_operator_calldata),
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
        ],
    )

    # 11) ActivateNodeOperators - ChangeNodeOperatorManagers -> MANAGER_ALREADY_HAS_ROLE
    # activate no2 address2 manager1    name2 v
    # change   no1 address3 manager2->1 name3 x
    activate_node_operators_calldata = prepare_activate_node_operator_calldata(no2, manager1)
    change_node_operator_manager_calldata = prepare_change_node_operator_manager_calldata(no1, manager2, manager1)

    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, activate_node_operators_factory, activate_node_operators_calldata),
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
        ],
    )

    # 12) ChangeNodeOperatorManagers - ChangeNodeOperatorManagers -> OLD_MANAGER_HAS_NO_ROLE
    # change no1 address3 manager2->4 name3 v
    # change no1 address3 manager2->4 name3 x
    change_node_operator_manager_calldata = prepare_change_node_operator_manager_calldata(no1, manager2, manager4)
    easytrack_pair_executor_with_collision(
        reverts("OLD_MANAGER_HAS_NO_ROLE"),
        [
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata),
        ],
    )

    # 13) ChangeNodeOperatorManagers - ChangeNodeOperatorManagers -> MANAGER_ALREADY_HAS_ROLE
    # change no1 address3 manager4->2 name3 v
    # change no2 address2 manager1->2 name2 x
    change_node_operator_manager_calldata1 = prepare_change_node_operator_manager_calldata(no1, manager4, manager2)
    change_node_operator_manager_calldata2 = prepare_change_node_operator_manager_calldata(no2, manager1, manager2)
    easytrack_pair_executor_with_collision(
        reverts("MANAGER_ALREADY_HAS_ROLE"),
        [
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata1),
            (commitee_multisig, change_node_operator_manager_factory, change_node_operator_manager_calldata2),
        ],
    )

    # addSigningKeysOperatorBH no1 address3 manager4 name3
    set_account_balance(manager2)
    simple_dvt.addSigningKeysOperatorBH(
        no1,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": manager2},
    )

    # 14) DeactivateNodeOperators - IncreaseVettedValidatorsLimit -> STAKING_LIMIT_TOO_LOW
    # set vetted      no1 address3 manager2 name3 vl->1 v
    # increase vetted no1 address3 manager2 name3 vt->1 x
    set_vetted_validators_limit_calldata = prepare_set_vetted_validators_limit_calldata(no1, 1)
    increase_vetted_validators_limit_calldata = prepare_increase_vetted_validators_limit_calldata(no1, 1)

    easytrack_pair_executor_with_collision(
        reverts("STAKING_LIMIT_TOO_LOW"),
        [
            (commitee_multisig, set_vetted_validators_limit_factory, set_vetted_validators_limit_calldata),
            (manager2, increase_vetted_validators_limit_factory, increase_vetted_validators_limit_calldata),
        ],
    )

    # 15) IncreaseVettedValidatorsLimit - IncreaseVettedValidatorsLimit -> STAKING_LIMIT_TOO_LOW
    # increase vetted no1 address3 manager2 name3 vl->2 v
    # increase vetted no1 address3 manager2 name3 vt->2 x
    increase_vetted_validators_limit_calldata1 = prepare_increase_vetted_validators_limit_calldata(no1, 2)
    increase_vetted_validators_limit_calldata2 = prepare_increase_vetted_validators_limit_calldata(no1, 2)

    easytrack_pair_executor_with_collision(
        reverts("STAKING_LIMIT_TOO_LOW"),
        [
            (manager2, increase_vetted_validators_limit_factory, increase_vetted_validators_limit_calldata1),
            (manager2, increase_vetted_validators_limit_factory, increase_vetted_validators_limit_calldata2),
        ],
    )

    # 16) DeactivateNodeOperators - IncreaseVettedValidatorsLimit -> CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER
    # deactivate      no1 address3 manager2 name3       v
    # increase vetted no1 address3 manager2 name3 vt->3 x
    deactivate_node_operator_calldata = prepare_deactivate_node_operator_calldata(no1, manager2)
    increase_vetted_validators_limit_calldata = prepare_increase_vetted_validators_limit_calldata(no1, 3)

    easytrack_pair_executor_with_collision(
        reverts("CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER"),
        [
            (commitee_multisig, deactivate_node_operators_factory, deactivate_node_operator_calldata),
            (manager2, increase_vetted_validators_limit_factory, increase_vetted_validators_limit_calldata),
        ],
    )
