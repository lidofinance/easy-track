import pytest
from eth_abi import encode_single
from brownie import reverts, web3, interface, convert
from utils.evm_script import encode_call_script

table = [
    {
        "address": "0x000000000000000000000000000000000000{:04}".format(i),
        "manager": "0x000000000000000000000000000000000000{:04}".format(i),
        "name": "Table " + str(i),
    }
    for i in range(1, 5)
]

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
    simple_DVT_tx = kernel.newAppInstance(
        name, nor_proxy.implementation(), {"from": voting}
    )

    simple_dvt_contract = interface.NodeOperatorsRegistry(
        simple_DVT_tx.new_contracts[0]
    )

    simple_dvt_contract.initialize(locator, "0x01", 0, {"from": voting})

    staking_router.grantRole(
        web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex(), agent, {"from": agent}
    )

    staking_router.addStakingModule(
        "Simple DVT", simple_dvt_contract, 10_000, 500, 500, {"from": agent}
    )

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
        + encode_single(
            "(uint256,(string,address,address)[])",
            [count, [(name, address, manager)]],
        ).hex()
    )


def prepare_deactivate_node_operator_calldata(operator, manager):
    return (
        "0x"
        + encode_single(
            "((uint256,address)[])",
            [[(operator, manager)]]
        ).hex()
    )


def prepare_activate_node_operator_calldata(operator, manager):
    return (
        "0x"
        + encode_single(
            "((uint256,address)[])",
            [[(operator, manager)]]
        ).hex()
    )


def prepare_change_node_operator_manager_calldata(operator, old_manager, new_manager):
    return (
        "0x"
        + encode_single(
            "((uint256,address,address)[])",
            [[(operator, old_manager, new_manager)]],
        ).hex()
    )


def prepare_set_node_operator_name_calldata(operator, name):
    return (
        "0x"
        + encode_single(
            "((uint256,string)[])",
            [[(operator, name)]]
        ).hex()
    )


def prepare_set_node_operator_reward_address_calldata(operator, address):
    return (
        "0x"
        + encode_single(
            "((uint256,address)[])",
            [[(operator, address)]]
        ).hex()
    )


# def prepare_update_tareget_validator_limits_calldata(id_operator, is_active,  limit):
#     return (
#         "0x"
#         + encode_single(
#             "((uint256,bool,uint256)[])",
#             [
#                 [(id_operator, is_active, limit)]
#             ]
#         ).hex()
#     )


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
        update_tareget_validator_limits_factory,
        stranger,
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
        ]
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
        ]
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

        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    )

    # # 14) UpdateTargetValidatorLimits - SetVettedValidatorsLimits
    # # update no1 address3 manager4 name3 tl->true v
    # # set    no1 address3 manager4 name3 vl->9    x
    # update_tareget_validator_limits_calldata = prepare_update_tareget_validator_limits_calldata(no1, True, 8)
    # set_vetted_validators_limit_calldata = prepare_change_node_operator_manager_calldata(no1, no2, no3)
    #
    # easytrack_pair_executor_with_collision(
    #     reverts("case14"),
    #     [
    #         (commitee_multisig, update_tareget_validator_limits_factory, update_tareget_validator_limits_calldata),
    #         (commitee_multisig, set_vetted_validators_limit_factory, set_vetted_validators_limit_calldata),
    #     ]
    # )
