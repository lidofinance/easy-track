import pytest
from eth_abi import encode
from brownie import web3, interface
from utils.evm_script import encode_call_script
from utils.permission_parameters import Op, Param, encode_permission_params
from utils.test_helpers import set_account_balance

clusters = [
    {
        "address": "0x000000000000000000000000000000000000{:04}".format(i),
        "manager": "0x000000000000000000000000000000000000{:04}".format(i),
        "name": "Cluster " + str(i),
    }
    for i in range(1, 37)
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
        "Simple DVT", simple_dvt_contract, 10_000, 10_000, 500, 500, 150, 25, {"from": agent}
    )

    acl.createPermission(
        agent,
        simple_dvt_contract,
        web3.keccak(text="MANAGE_NODE_OPERATOR_ROLE").hex(),
        agent,
        {"from": voting},
    )

    return simple_dvt_contract


def test_simple_dvt_scenario(
    simple_dvt,
    voting,
    commitee_multisig,
    et_contracts,
    acl,
    agent,
    easytrack_executor,
    add_node_operators_factory,
    activate_node_operators_factory,
    deactivate_node_operators_factory,
    set_node_operator_name_factory,
    set_node_operator_reward_address_factory,
    set_vetted_validators_limit_factory,
    change_node_operator_manager_factory,
    update_target_validator_limits_factory,
    increase_vetted_validators_limit_factory,
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

    # Add clusters
    add_node_operators_calldata = (
        "0x"
        + encode(
            ["uint256", "(string,address,address)[]"],
            [
                0,
                [
                    (cluster["name"], cluster["address"], cluster["manager"])
                    for cluster in clusters
                ],
            ],
        ).hex()
    )

    easytrack_executor(
        commitee_multisig, add_node_operators_factory, add_node_operators_calldata
    )

    for cluster_index in range(len(clusters)):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == True
        assert cluster["name"] == clusters[cluster_index]["name"]
        assert cluster["rewardAddress"] == clusters[cluster_index]["address"]
        assert cluster["totalVettedValidators"] == 0
        assert cluster["totalExitedValidators"] == 0
        assert cluster["totalAddedValidators"] == 0
        assert cluster["totalDepositedValidators"] == 0

        assert (
            simple_dvt.canPerform(
                clusters[cluster_index]["manager"],
                simple_dvt.MANAGE_SIGNING_KEYS(),
                encode_permission_params([Param(0, Op.EQ, cluster_index)]),
            )
            == True
        )

    # Deactivate node operators with ids 2,3,4

    deactivate_node_operators_data = []

    for cluster_index in range(2, 5):
        deactivate_node_operators_data.append(
            (cluster_index, clusters[cluster_index]["manager"])
        )

    deactivate_node_operators_calldata = (
        "0x" + encode(["(uint256,address)[]"], [deactivate_node_operators_data]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        deactivate_node_operators_factory,
        deactivate_node_operators_calldata,
    )

    for cluster_index in range(2, 5):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == False

        assert (
            simple_dvt.canPerform(
                clusters[cluster_index]["manager"],
                simple_dvt.MANAGE_SIGNING_KEYS(),
                encode_permission_params([Param(0, Op.EQ, cluster_index)]),
            )
            == False
        )

    # Activate node operators with ids 2,3,4

    activate_node_operators_data = []

    for cluster_index in range(2, 5):
        activate_node_operators_data.append(
            (cluster_index, clusters[cluster_index]["manager"])
        )

    activate_node_operators_calldata = (
        "0x" + encode(["(uint256,address)[]"], [activate_node_operators_data]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        activate_node_operators_factory,
        activate_node_operators_calldata,
    )

    for cluster_index in range(2, 5):
        cluster = simple_dvt.getNodeOperator(cluster_index, True)
        assert cluster["active"] == True

        assert (
            simple_dvt.canPerform(
                clusters[cluster_index]["manager"],
                simple_dvt.MANAGE_SIGNING_KEYS(),
                encode_permission_params([Param(0, Op.EQ, cluster_index)]),
            )
            == True
        )

    # Set name of node operator

    set_node_operator_name_calldata = (
        "0x" + encode(["(uint256,string)[]"], [[(6, "New Name")]]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        set_node_operator_name_factory,
        set_node_operator_name_calldata,
    )

    cluster = simple_dvt.getNodeOperator(6, True)
    assert cluster["name"] == "New Name"

    # Set reward address of node operator
    new_reward_address = "0x000000000000000000000000000000000000dEaD"
    set_node_operator_reward_address_calldata = (
        "0x" + encode(["(uint256,address)[]"], [[(6, new_reward_address)]]).hex()
    )

    easytrack_executor(
        commitee_multisig,
        set_node_operator_reward_address_factory,
        set_node_operator_reward_address_calldata,
    )

    cluster = simple_dvt.getNodeOperator(6, True)
    assert cluster["rewardAddress"] == new_reward_address

    # add signing keys to node operator
    no_5_id = 5
    no_5 = simple_dvt.getNodeOperator(no_5_id, False)
    set_account_balance(clusters[5]["manager"])

    simple_dvt.addSigningKeysOperatorBH(
        no_5_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": clusters[5]["manager"]},
    )

    assert cluster["totalVettedValidators"] == 0

    # Increase staking limit with commitee
    simple_dvt.addSigningKeysOperatorBH(
        no_5_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": clusters[5]["manager"]},
    )

    no_6_id = 6
    no_6 = simple_dvt.getNodeOperator(no_6_id, False)
    set_account_balance(clusters[6]["manager"])

    simple_dvt.addSigningKeysOperatorBH(
        no_6_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": clusters[6]["manager"]},
    )

    set_vetted_validators_limit_calldata = (
        "0x" + encode(["(uint256,uint256)[]"], [[(no_5_id, 4), (no_6_id, 3)]]).hex()
    )
    easytrack_executor(
        commitee_multisig,
        set_vetted_validators_limit_factory,
        set_vetted_validators_limit_calldata,
    )

    cluster_5 = simple_dvt.getNodeOperator(no_5_id, False)
    assert cluster_5["totalVettedValidators"] == 4
    cluster_6 = simple_dvt.getNodeOperator(no_6_id, False)
    assert cluster_6["totalVettedValidators"] == 3

    # Increase staking limit with cluster
    simple_dvt.addSigningKeysOperatorBH(
        no_5_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": clusters[5]["manager"]},
    )

    increase_vetted_validators_limit_calldata = (
        "0x" + encode(["(uint256,uint256)"], [(no_5_id, 6)]).hex()
    )
    easytrack_executor(
        clusters[5]["manager"],
        increase_vetted_validators_limit_factory,
        increase_vetted_validators_limit_calldata,
    )

    cluster_5 = simple_dvt.getNodeOperator(no_5_id, False)
    assert cluster_5["totalVettedValidators"] == 6

    # Update target validators limits

    update_target_validator_limits_calldata = (
        "0x"
        + encode(
            ["(uint256,uint256,uint256)[]"], [[(no_5_id, 2, 1), (no_6_id, 1, 10)]]
        ).hex()
    )
    easytrack_executor(
        commitee_multisig,
        update_target_validator_limits_factory,
        update_target_validator_limits_calldata,
    )

    no_5_summary = simple_dvt.getNodeOperatorSummary(no_5_id)
    no_6_summary = simple_dvt.getNodeOperatorSummary(no_6_id)

    assert no_5_summary["targetLimitMode"] == 2
    assert no_6_summary["targetLimitMode"] == 1
    assert no_5_summary["targetValidatorsCount"] == 1
    assert no_6_summary["targetValidatorsCount"] == 10

    # Transfer cluster manager
    change_node_operator_manager_calldata = (
        "0x"
        + encode(
            ["(uint256,address,address)[]"],
            [[(no_5_id, clusters[no_5_id]["manager"], stranger.address)]],
        ).hex()
    )

    easytrack_executor(
        commitee_multisig,
        change_node_operator_manager_factory,
        change_node_operator_manager_calldata,
    )

    assert not simple_dvt.canPerform(
        clusters[no_5_id]["manager"],
        simple_dvt.MANAGE_SIGNING_KEYS(),
        encode_permission_params([Param(0, Op.EQ, no_5_id)]),
    )
    assert simple_dvt.canPerform(
        stranger,
        simple_dvt.MANAGE_SIGNING_KEYS(),
        encode_permission_params([Param(0, Op.EQ, no_5_id)]),
    )

    # Renounce MANAGE_SIGNING_KEYS role manager

    set_permission_manager_calldata = acl.setPermissionManager.encode_input(
        agent, simple_dvt, web3.keccak(text="MANAGE_SIGNING_KEYS").hex()
    )

    set_permission_manager_calldata = (
        et_contracts.evm_script_executor.executeEVMScript.encode_input(
            encode_call_script(
                [
                    (
                        acl.address,
                        acl.setPermissionManager.encode_input(
                            agent,
                            simple_dvt,
                            web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                        ),
                    )
                ]
            ),
        )
    )

    et_contracts.evm_script_executor.setEasyTrack(agent, {"from": voting})
    agent.execute(
        et_contracts.evm_script_executor,
        0,
        set_permission_manager_calldata,
        {"from": voting},
    )
    et_contracts.evm_script_executor.setEasyTrack(
        et_contracts.easy_track, {"from": voting}
    )

    assert (
        acl.getPermissionManager(simple_dvt, simple_dvt.MANAGE_SIGNING_KEYS()) == agent
    )
