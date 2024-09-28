import pytest
from eth_abi import encode
from brownie import web3, interface
from utils.permission_parameters import Op, Param, encode_permission_params
from utils.evm_script import encode_call_script

clusters = [
    {
        "address": "0x000000000000000000000000000000000000{:04}".format(i),
        "manager": "0x000000000000000000000000000000000000{:04}".format(i),
        "name": "Cluster " + str(i),
    }
    for i in range(1, 8)
]


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


@pytest.fixture(scope="module")
def grant_roles(acl, et_contracts, agent, voting, simple_dvt):
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


def test_simple_make_action(
    simple_dvt,
    commitee_multisig,
    et_contracts,
    acl,
    agent,
    easytrack_executor,
    add_node_operators_factory,
    grant_roles,
    lido_contracts,
    stranger,
    change_node_operator_manager_factory,
):
    # Add clusters
    add_node_operators_calldata = (
        "0x"
        + encode(
            ["uint256", "(string,address,address)[]"],
            [
                0,
                [(cluster["name"], cluster["address"], cluster["manager"]) for cluster in clusters],
            ],
        ).hex()
    )

    easytrack_executor(commitee_multisig, add_node_operators_factory, add_node_operators_calldata)

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

    # Renounce MANAGE_SIGNING_KEYS role manager

    vote_script_calldata = encode_call_script(
        [
            (
                et_contracts.evm_script_executor.address,
                et_contracts.evm_script_executor.setEasyTrack.encode_input(agent),
            ),
            encode_agent_forward(
                agent,
                [
                    encode_execute_evm_script(
                        et_contracts.evm_script_executor,
                        (
                            acl.address,
                            acl.setPermissionManager.encode_input(
                                agent,
                                simple_dvt,
                                web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                            ),
                        ),
                    ),
                    (
                        acl.address,
                        acl.grantPermission.encode_input(
                            agent.address,
                            simple_dvt,
                            simple_dvt.MANAGE_SIGNING_KEYS(),
                        ),
                    ),
                    (
                        acl.address,
                        acl.setPermissionManager.encode_input(
                            et_contracts.evm_script_executor,
                            simple_dvt,
                            web3.keccak(text="MANAGE_SIGNING_KEYS").hex(),
                        ),
                    ),
                ],
            ),
            (
                et_contracts.evm_script_executor.address,
                et_contracts.evm_script_executor.setEasyTrack.encode_input(et_contracts.easy_track),
            ),
        ]
    )

    voting_id, _ = lido_contracts.create_voting(
        evm_script=vote_script_calldata,
        description="Update MANAGE_SIGNING_KEYS roles manager.",
        tx_params={"from": lido_contracts.aragon.agent},
    )

    lido_contracts.execute_voting(voting_id)

    assert acl.getPermissionManager(simple_dvt, simple_dvt.MANAGE_SIGNING_KEYS()) == et_contracts.evm_script_executor

    assert acl.hasPermission(agent, simple_dvt, simple_dvt.MANAGE_SIGNING_KEYS()) == True

    assert et_contracts.evm_script_executor.easyTrack() == et_contracts.easy_track

    # Transfer cluster manager

    # add signing keys to node operator
    no_5_id = 5
    no_5 = simple_dvt.getNodeOperator(no_5_id, False)
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


def encode_agent_forward(agent, scripts):
    return (agent.address, agent.forward.encode_input(encode_call_script(scripts)))


def encode_execute_evm_script(evm_script_executor, script):
    return (
        evm_script_executor.address,
        evm_script_executor.executeEVMScript.encode_input(encode_call_script([script])),
    )
