import pytest
import brownie

import constants
from utils import evm_script


@pytest.mark.skip_coverage
def test_node_operators_easy_track_happy_path(
    IncreaseNodeOperatorStakingLimit,
    EVMScriptExecutor,
    EasyTrack,
    accounts,
    voting,
    agent,
    node_operators_registry,
    ldo,
    calls_script,
    acl,
    lido_contracts,
    deployer,
    stranger,
):
    deployer = accounts[0]

    # deploy easy track
    easy_track = deployer.deploy(
        EasyTrack,
        ldo,
        deployer,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )

    # deploy evm script executor
    evm_script_executor = deployer.deploy(EVMScriptExecutor, calls_script, easy_track)
    evm_script_executor.transferOwnership(voting, {"from": deployer})
    assert evm_script_executor.owner() == voting

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy IncreaseNodeOperatorStakingLimit EVM script factory
    increase_node_operator_staking_limit = deployer.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry)

    # add IncreaseNodeOperatorStakingLimit to registry
    permissions = node_operators_registry.address + node_operators_registry.setNodeOperatorStakingLimit.signature[2:]
    easy_track.addEVMScriptFactory(increase_node_operator_staking_limit, permissions, {"from": deployer})
    evm_script_factories = easy_track.getEVMScriptFactories()
    assert len(evm_script_factories) == 1
    assert evm_script_factories[0] == increase_node_operator_staking_limit

    # transfer admin role to voting
    easy_track.grantRole(easy_track.DEFAULT_ADMIN_ROLE(), voting, {"from": deployer})
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), voting)
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, {"from": deployer})
    assert not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer)

    # create voting to grant permissions to EVM script executor to set staking limit

    add_set_staking_limit_permissions_voting_id, _ = lido_contracts.create_voting(
        evm_script=evm_script.encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(
                        evm_script_executor,
                        node_operators_registry,
                        node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE(),
                    ),
                ),
            ]
        ),
        description="Grant permissions to EVMScriptExecutor to set staking limits",
        tx_params={"from": agent},
    )

    lido_contracts.execute_voting(add_set_staking_limit_permissions_voting_id)

    # create vote to add test node operator
    node_operator = {"name": "test_node_operator", "address": accounts[3]}
    add_node_operator_calldata = node_operators_registry.addNodeOperator.encode_input(
        node_operator["name"], node_operator["address"]
    )
    add_node_operator_evm_script = evm_script.encode_call_script(
        [
            (
                acl.address,
                acl.grantPermission.encode_input(
                    voting, node_operators_registry, node_operators_registry.MANAGE_NODE_OPERATOR_ROLE()
                ),
            ),
            (
                node_operators_registry.address,
                add_node_operator_calldata,
            ),
        ]
    )

    add_node_operators_voting_id, _ = lido_contracts.create_voting(
        evm_script=add_node_operator_evm_script,
        description="Add node operator to registry",
        tx_params={"from": agent},
    )

    # execute vote to add test node operator
    lido_contracts.execute_voting(add_node_operators_voting_id)

    # validate new node operator id
    new_node_operator_id = node_operators_registry.getNodeOperatorsCount() - 1
    new_node_operator = node_operators_registry.getNodeOperator(new_node_operator_id, True)
    assert new_node_operator[0]  # active
    assert new_node_operator[1] == node_operator["name"]  # name
    assert new_node_operator[2] == node_operator["address"]  # rewardAddress
    assert new_node_operator[3] == 0  # stakingLimit

    # add signing keys to new node operator
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

    node_operators_registry.addSigningKeysOperatorBH(
        new_node_operator_id,
        len(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["pubkeys"]),
        "0x" + "".join(signing_keys["signatures"]),
        {"from": node_operator["address"]},
    )

    # validate that signing keys have been added
    new_node_operator = node_operators_registry.getNodeOperator(new_node_operator_id, True)
    assert new_node_operator[5] == len(signing_keys["pubkeys"])  # totalSigningKeys
    assert new_node_operator[6] == 0  # usedSigningKeys

    # create new motion to increase staking limit
    tx = easy_track.createMotion(
        increase_node_operator_staking_limit,
        evm_script.encode_calldata(["uint256", "uint256"], [new_node_operator_id, 3]),
        {"from": node_operator["address"]},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(easy_track.motionDuration() + 100)

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # validate that motion was executed correctly
    motions = easy_track.getMotions()
    assert len(motions) == 0
    new_node_operator = node_operators_registry.getNodeOperator(new_node_operator_id, True)
    assert new_node_operator[3] == 3  # stakingLimit
