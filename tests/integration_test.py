from brownie.network import Chain
from brownie import (
    LegoEasyTrack,
    EasyTracksRegistry,
    TopUpRewardProgramEasyTrack,
    AddRewardProgramEasyTrack,
    RemoveRewardProgramEasyTrack,
    MotionsRegistry,
    NodeOperatorsEasyTrack,
    accounts,
    ZERO_ADDRESS,
)

from utils.evm_script import encode_call_script
import constants


def test_node_operators_easy_track(
    owner,
    voting,
    agent,
    token_manager,
    ldo_holders,
    node_operators_registry,
    ldo_token,
):
    chain = Chain()

    # deploy easy tracks registry
    easy_tracks_registry = owner.deploy(EasyTracksRegistry)

    # deploy motions registry
    motions_registry = owner.deploy(
        MotionsRegistry, easy_tracks_registry, ldo_token, agent
    )

    # transfer ownership to agent
    easy_tracks_registry.transferOwnership(agent, {"from": owner})
    motions_registry.transferOwnership(agent, {"from": owner})

    node_operators_easy_track = owner.deploy(
        NodeOperatorsEasyTrack,
        motions_registry,
        node_operators_registry,
    )

    # create voting to add permistions to motions_registry to forward to agent
    add_forward_permissions_evm_script = add_agent_forwarding_permission_call_script(
        motions_registry.address
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(add_forward_permissions_evm_script),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_forward_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permistions to motions_registry to forward to agent
    voting.vote(
        add_forward_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_forward_permissions_voting_id)
    voting.executeVote(add_forward_permissions_voting_id, {"from": accounts[0]})

    # create voting to add permissions to agent to set staking limit

    add_set_staking_limit_permissions_evm_script = (
        add_to_agent_permission_set_node_operators_stakin_limit_call_script()
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(
                        add_set_staking_limit_permissions_evm_script
                    ),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_set_staking_limit_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permissions to agent to set staking limit

    voting.vote(
        add_set_staking_limit_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_set_staking_limit_permissions_voting_id)
    voting.executeVote(
        add_set_staking_limit_permissions_voting_id, {"from": accounts[0]}
    )

    # add node_operators_easy_track to registry
    add_easy_track_calldata = easy_tracks_registry.addEasyTrack.encode_input(
        node_operators_easy_track
    )

    agent.execute(
        easy_tracks_registry,
        0,
        add_easy_track_calldata,
        {"from": accounts.at(constants.VOTING, force=True)},
    )
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 1
    assert easy_tracks[0] == node_operators_easy_track

    # create vote to add test node operator
    node_operator = {"name": "test_node_operator", "address": accounts[3]}
    add_node_operator_calldata = node_operators_registry.addNodeOperator.encode_input(
        node_operator["name"], node_operator["address"], 0
    )
    add_node_operator_evm_script = encode_call_script(
        [(node_operators_registry.address, add_node_operator_calldata)]
    )

    add_node_operators_voting_tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.newVote.encode_input(
                        add_node_operator_evm_script, "Add node operator to registry"
                    ),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_node_operators_voting_id = add_node_operators_voting_tx.events["StartVote"][
        "voteId"
    ]

    # execute vote
    voting.vote(
        add_node_operators_voting_id, True, False, {"from": constants.LDO_WHALE_HOLDER}
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_node_operators_voting_id)
    voting.executeVote(add_node_operators_voting_id, {"from": accounts[0]})

    # validate new node operator id
    new_node_operator_id = node_operators_registry.getActiveNodeOperatorsCount() - 1
    new_node_operator = node_operators_registry.getNodeOperator(
        new_node_operator_id, True
    )
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
    new_node_operator = node_operators_registry.getNodeOperator(
        new_node_operator_id, True
    )
    assert new_node_operator[5] == len(signing_keys["pubkeys"])  # totalSigningKeys
    assert new_node_operator[6] == 0  # usedSigningKeys

    # create new motion to increase staking limit
    node_operators_easy_track.createMotion(
        new_node_operator_id, 3, {"from": node_operator["address"]}
    )
    motions = motions_registry.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    node_operators_easy_track.enactMotion(motions[0][0])

    # validate that motion was executed correctly
    motions = motions_registry.getMotions()
    assert len(motions) == 0
    new_node_operator = node_operators_registry.getNodeOperator(
        new_node_operator_id, True
    )
    assert new_node_operator[3] == 3  # stakingLimit


def test_reward_programs_easy_track(
    owner,
    agent,
    voting,
    finance,
    ldo_token,
    ldo_holders,
    token_manager,
):
    chain = Chain()

    # deploy easy tracks registry
    easy_tracks_registry = owner.deploy(EasyTracksRegistry)

    # deploy motions registry
    motions_registry = owner.deploy(
        MotionsRegistry, easy_tracks_registry, ldo_token, agent
    )

    # transfer ownership to agent
    easy_tracks_registry.transferOwnership(agent, {"from": owner})
    motions_registry.transferOwnership(agent, {"from": owner})

    trusted_address = accounts[7]

    # deploy reward program easy tracks
    top_up_reward_program_easy_track = owner.deploy(
        TopUpRewardProgramEasyTrack,
        motions_registry,
        trusted_address,
        finance,
        ldo_token,
    )

    add_reward_program_easy_track = owner.deploy(
        AddRewardProgramEasyTrack,
        motions_registry,
        trusted_address,
        top_up_reward_program_easy_track,
    )

    remove_reward_program_easy_track = owner.deploy(
        RemoveRewardProgramEasyTrack,
        motions_registry,
        trusted_address,
        top_up_reward_program_easy_track,
    )

    top_up_reward_program_easy_track.initialize(
        add_reward_program_easy_track,
        remove_reward_program_easy_track,
    )

    # create voting to add permistions to motions_registry to forward to agent
    add_forward_permissions_evm_script = add_agent_forwarding_permission_call_script(
        motions_registry.address
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(add_forward_permissions_evm_script),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_forward_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permistions to motions_registry to forward to agent
    voting.vote(
        add_forward_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_forward_permissions_voting_id)
    voting.executeVote(add_forward_permissions_voting_id, {"from": accounts[0]})

    # create voting to add permissions to agent to create new payments
    add_create_payments_permissions_evm_script = (
        add_to_agent_permission_create_new_payments_call_script()
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(
                        add_create_payments_permissions_evm_script
                    ),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_create_payments_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permissions to agent to create payments
    voting.vote(
        add_create_payments_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_create_payments_permissions_voting_id)
    voting.executeVote(add_create_payments_permissions_voting_id, {"from": accounts[0]})

    # add top_up_reward_program_easy_track to registry
    add_easy_track_calldata = easy_tracks_registry.addEasyTrack.encode_input(
        top_up_reward_program_easy_track
    )

    agent.execute(
        easy_tracks_registry,
        0,
        add_easy_track_calldata,
        {"from": accounts.at(constants.VOTING, force=True)},
    )
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 1
    assert easy_tracks[0] == top_up_reward_program_easy_track

    # add add_reward_program_easy_track to registry
    add_easy_track_calldata = easy_tracks_registry.addEasyTrack.encode_input(
        add_reward_program_easy_track
    )

    agent.execute(
        easy_tracks_registry,
        0,
        add_easy_track_calldata,
        {"from": accounts.at(constants.VOTING, force=True)},
    )
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 2
    assert easy_tracks[1] == add_reward_program_easy_track

    # add remove_reward_program_easy_track to registry
    add_easy_track_calldata = easy_tracks_registry.addEasyTrack.encode_input(
        remove_reward_program_easy_track
    )

    agent.execute(
        easy_tracks_registry,
        0,
        add_easy_track_calldata,
        {"from": accounts.at(constants.VOTING, force=True)},
    )
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 3
    assert easy_tracks[2] == remove_reward_program_easy_track

    reward_program = accounts[5]

    # create new motion to add reward program
    add_reward_program_easy_track.createMotion(
        reward_program, {"from": trusted_address}
    )

    motions = motions_registry.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    add_reward_program_easy_track.enactMotion(motions[0][0])
    assert len(motions_registry.getMotions()) == 0

    reward_programs = top_up_reward_program_easy_track.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program

    # create new motion to top up reward program
    top_up_reward_program_easy_track.createMotion(
        [reward_program.address], [int(5e18)], {"from": trusted_address}
    )
    motions = motions_registry.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    assert ldo_token.balanceOf(reward_program) == 0

    top_up_reward_program_easy_track.enactMotion(motions[0][0])

    assert len(motions_registry.getMotions()) == 0
    assert ldo_token.balanceOf(reward_program) == 5e18

    # create new motion to remove reward program
    remove_reward_program_easy_track.createMotion(
        reward_program, {"from": trusted_address}
    )

    motions = motions_registry.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    remove_reward_program_easy_track.enactMotion(motions[0][0])
    assert len(motions_registry.getMotions()) == 0
    assert len(top_up_reward_program_easy_track.getRewardPrograms()) == 0


def test_lego_easy_track_executor(
    owner,
    agent,
    finance,
    ldo_token,
    steth_token,
    lego_program,
    token_manager,
    voting,
    ldo_holders,
):
    chain = Chain()

    # deploy easy tracks registry
    easy_tracks_registry = owner.deploy(EasyTracksRegistry)

    # deploy motions registry
    motions_registry = owner.deploy(
        MotionsRegistry, easy_tracks_registry, ldo_token, agent
    )

    # transfer ownership to agent
    easy_tracks_registry.transferOwnership(agent, {"from": owner})
    motions_registry.transferOwnership(agent, {"from": owner})

    trusted_address = accounts[7]

    # deploy reward program easy tracks
    lego_easy_track = owner.deploy(
        LegoEasyTrack, motions_registry, trusted_address, finance, lego_program
    )

    # create voting to add permistions to motions_registry to forward to agent
    add_forward_permissions_evm_script = add_agent_forwarding_permission_call_script(
        motions_registry.address
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(add_forward_permissions_evm_script),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_forward_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permistions to motions_registry to forward to agent
    voting.vote(
        add_forward_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_forward_permissions_voting_id)
    voting.executeVote(add_forward_permissions_voting_id, {"from": accounts[0]})

    # create voting to add permissions to agent to create new payments
    add_create_payments_permissions_evm_script = (
        add_to_agent_permission_create_new_payments_call_script()
    )

    tx = token_manager.forward(
        encode_call_script(
            [
                (
                    voting.address,
                    voting.forward.encode_input(
                        add_create_payments_permissions_evm_script
                    ),
                )
            ]
        ),
        {"from": ldo_holders[0]},
    )
    add_create_payments_permissions_voting_id = tx.events["StartVote"]["voteId"]

    # execute voting to add permissions to agent to create new payments
    voting.vote(
        add_create_payments_permissions_voting_id,
        True,
        False,
        {"from": constants.LDO_WHALE_HOLDER},
    )
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()
    assert voting.canExecute(add_create_payments_permissions_voting_id)
    voting.executeVote(add_create_payments_permissions_voting_id, {"from": accounts[0]})

    # add lego_easy_track to registry
    add_easy_track_calldata = easy_tracks_registry.addEasyTrack.encode_input(
        lego_easy_track
    )

    agent.execute(
        easy_tracks_registry,
        0,
        add_easy_track_calldata,
        {"from": accounts.at(constants.VOTING, force=True)},
    )
    easy_tracks = easy_tracks_registry.getEasyTracks()
    assert len(easy_tracks) == 1
    assert easy_tracks[0] == lego_easy_track

    # create new motion to make transfers to lego programs

    ldo_amount, steth_amount, eth_amount = 10 ** 18, 2 * 10 ** 18, 3 * 10 ** 18

    lego_easy_track.createMotion(
        [ldo_token, steth_token, ZERO_ADDRESS],
        [ldo_amount, steth_amount, eth_amount],
        {"from": trusted_address},
    )

    motions = motions_registry.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    # top up agent balances
    ldo_token.approve(agent, ldo_amount, {"from": constants.LDO_WHALE_HOLDER})
    agent.deposit(ldo_token, ldo_amount, {"from": constants.LDO_WHALE_HOLDER})

    steth_token.submit(ZERO_ADDRESS, {"from": owner, "value": "2.1 ether"})
    steth_token.approve(agent, "2.1 ether", {"from": owner})
    agent.deposit(steth_token, steth_amount, {"from": owner})

    agent.deposit(ZERO_ADDRESS, eth_amount, {"from": owner, "value": eth_amount})

    # validate agent app has enough tokens
    assert agent.balance(ldo_token) >= ldo_amount
    assert agent.balance(steth_token) >= steth_amount
    assert agent.balance(ZERO_ADDRESS) >= eth_amount

    assert ldo_token.balanceOf(lego_program) == 0
    assert steth_token.balanceOf(lego_program) == 0
    assert lego_program.balance() == 100 * 10 ** 18

    lego_easy_track.enactMotion(motions[0][0])

    assert len(motions_registry.getMotions()) == 0
    assert ldo_token.balanceOf(lego_program) == ldo_amount
    assert abs(steth_token.balanceOf(lego_program) - steth_amount) <= 10
    assert lego_program.balance() == 103 * 10 ** 18


def add_agent_forwarding_permission_call_script(forwarder_address):
    spec_id = "00000001"
    to_address = constants.ACL[2:]
    forward_agent_role_data = "0000000000000000000000004333218072d5d7008546737786663c38b4d561a4b421f7ad7646747f3051c50c0b8e2377839296cd4973e27f63821d73e390338f"
    calldata_length = "00000064"
    method_id = "0a8ed3db"
    return (
        spec_id
        + to_address
        + calldata_length
        + method_id
        + forwarder_address[2:].zfill(64)
        + forward_agent_role_data
    )


def add_to_agent_permission_set_node_operators_stakin_limit_call_script():
    spec_id = "00000001"
    to_address = constants.ACL[2:]
    set_staking_limit_role_data = "0000000000000000000000009d4af1ee19dad8857db3a45b0374c81c8a1c632007b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"
    calldata_length = "00000064"
    method_id = "0a8ed3db"
    return (
        spec_id
        + to_address
        + calldata_length
        + method_id
        + constants.ARAGON_AGENT[2:].zfill(64)
        + set_staking_limit_role_data
    )


def add_to_agent_permission_create_new_payments_call_script():
    spec_id = "00000001"
    to_address = constants.ACL[2:]
    create_payments_role_data = "00000000000000000000000075c7b1d23f1cad7fb4d60281d7069e46440bc1795de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc"
    calldata_length = "00000064"
    method_id = "0a8ed3db"
    return (
        spec_id
        + to_address
        + calldata_length
        + method_id
        + constants.ARAGON_AGENT[2:].zfill(64)
        + create_payments_role_data
    )