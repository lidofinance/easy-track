from brownie.network import Chain
from brownie import (
    Contract,
    ContractProxy,
    TopUpLegoProgram,
    EasyTrack,
    EVMScriptExecutor,
    TopUpRewardPrograms,
    AddRewardProgram,
    RemoveRewardProgram,
    RewardProgramsRegistry,
    IncreaseNodeOperatorStakingLimit,
    accounts,
    ZERO_ADDRESS,
    reverts,
    history,
)
from eth_abi import encode_single
from utils.evm_script import encode_call_script
import constants


def test_node_operators_easy_track(
    stranger,
    voting,
    agent,
    token_manager,
    ldo_holders,
    node_operators_registry,
    ldo_token,
):
    chain = Chain()
    deployer = accounts[0]
    voting_helper = VotingHelper(chain, token_manager, voting)

    # deploy easy track
    easy_track_logic = deployer.deploy(EasyTrack)

    # init easy track and grant admin permissions to deployer
    easy_track_proxy = deployer.deploy(
        ContractProxy,
        easy_track_logic,
        easy_track_logic.__EasyTrackStorage_init.encode_input(ldo_token, deployer),
    )
    easy_track = Contract.from_abi("EasyTrackProxied", easy_track_proxy, EasyTrack.abi)

    # deploy evm script executor
    evm_script_executor = deployer.deploy(
        EVMScriptExecutor, constants.CALLS_SCRIPT, easy_track, constants.VOTING
    )

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy IncreaseNodeOperatorStakingLimit EVM script factory
    increase_node_operator_staking_limit = deployer.deploy(
        IncreaseNodeOperatorStakingLimit, node_operators_registry
    )

    # add IncreaseNodeOperatorStakingLimit to registry
    permissions = (
        node_operators_registry.address
        + node_operators_registry.setNodeOperatorStakingLimit.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        increase_node_operator_staking_limit, permissions, {"from": deployer}
    )
    evm_script_factories = easy_track.getEVMScriptFactories()
    assert len(evm_script_factories) == 1
    assert evm_script_factories[0] == increase_node_operator_staking_limit

    # transfer admin role to voting
    easy_track.grantRole(
        easy_track.DEFAULT_ADMIN_ROLE(), constants.VOTING, {"from": deployer}
    )
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), constants.VOTING)
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, {"from": deployer})
    assert not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer)

    # create voting to grant permissions to EVM script executor to set staking limit

    add_set_staking_limit_permissions_voting_id = voting_helper.create_voting(
        add_permission_set_node_operators_stakin_limit_call_script(evm_script_executor),
        "Grant permissions to EVMScriptExecutor to set staking limits",
    )

    # execute voting to add permissions to easy track to set staking limit
    voting_helper.execute_voting(add_set_staking_limit_permissions_voting_id)

    # create vote to add test node operator
    node_operator = {"name": "test_node_operator", "address": accounts[3]}
    add_node_operator_calldata = node_operators_registry.addNodeOperator.encode_input(
        node_operator["name"], node_operator["address"], 0
    )
    add_node_operator_evm_script = encode_call_script(
        [(node_operators_registry.address, add_node_operator_calldata)]
    )

    add_node_operators_voting_id = voting_helper.create_voting(
        add_node_operator_evm_script, "Add node operator to registry"
    )

    # execute vote to add test node operator
    voting_helper.execute_voting(add_node_operators_voting_id)

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
    tx = easy_track.createMotion(
        increase_node_operator_staking_limit,
        "0x" + encode_single("(uint256,uint256)", [new_node_operator_id, 3]).hex(),
        {"from": node_operator["address"]},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    # validate that motion was executed correctly
    motions = easy_track.getMotions()
    assert len(motions) == 0
    new_node_operator = node_operators_registry.getNodeOperator(
        new_node_operator_id, True
    )
    assert new_node_operator[3] == 3  # stakingLimit


def test_reward_programs_easy_track(
    stranger,
    agent,
    voting,
    finance,
    ldo_token,
    ldo_holders,
    token_manager,
):
    chain = Chain()
    deployer = accounts[0]
    reward_program = accounts[5]
    trusted_address = accounts[7]
    voting_helper = VotingHelper(chain, token_manager, voting)

    # deploy easy track
    easy_track_logic = deployer.deploy(EasyTrack)

    # init easy track and grant admin permissions to deployer
    easy_track_proxy = deployer.deploy(
        ContractProxy,
        easy_track_logic,
        easy_track_logic.__EasyTrackStorage_init.encode_input(ldo_token, deployer),
    )
    easy_track = Contract.from_abi("EasyTrackProxied", easy_track_proxy, EasyTrack.abi)

    # deploy evm script executor
    evm_script_executor = deployer.deploy(
        EVMScriptExecutor, constants.CALLS_SCRIPT, easy_track, constants.VOTING
    )

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy RewardProgramsRegistry
    reward_programs_registry = deployer.deploy(
        RewardProgramsRegistry, evm_script_executor
    )

    # deploy TopUpRewardProgram EVM script factory
    top_up_reward_programs = deployer.deploy(
        TopUpRewardPrograms,
        trusted_address,
        reward_programs_registry,
        finance,
        ldo_token,
    )

    # add TopUpRewardProgram EVM script factory to easy track
    new_immediate_payment_permission = (
        finance.address + finance.newImmediatePayment.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        top_up_reward_programs, new_immediate_payment_permission, {"from": deployer}
    )

    # deploy AddRewardProgram EVM script factory
    add_reward_program = deployer.deploy(
        AddRewardProgram, trusted_address, reward_programs_registry
    )

    # add AddRewardProgram EVM script factory to easy track
    add_reward_program_permission = (
        reward_programs_registry.address
        + reward_programs_registry.addRewardProgram.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        add_reward_program, add_reward_program_permission, {"from": deployer}
    )

    # deploy RemoveRewardProgram EVM script factory
    remove_reward_program = deployer.deploy(
        RemoveRewardProgram, trusted_address, reward_programs_registry
    )

    # add RemoveRewardProgram EVM script factory to easy track
    remove_reward_program_permission = (
        reward_programs_registry.address
        + reward_programs_registry.removeRewardProgram.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        remove_reward_program, remove_reward_program_permission, {"from": deployer}
    )

    # transfer admin role to voting
    easy_track.grantRole(
        easy_track.DEFAULT_ADMIN_ROLE(), constants.VOTING, {"from": deployer}
    )
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), constants.VOTING)
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, {"from": deployer})
    assert not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer)

    # create voting to grant permissions to EVM script executor to create new payments
    add_create_payments_permissions_voting_id = voting_helper.create_voting(
        add_permission_create_new_payments_call_script(evm_script_executor),
        "Grant permissions to EVMScriptExecutor to make payments",
    )

    # execute voting to add permissions to EVM script executor to create payments
    voting_helper.execute_voting(add_create_payments_permissions_voting_id)

    # create new motion to add reward program
    tx = easy_track.createMotion(
        add_reward_program,
        encode_single("(address)", [reward_program.address]),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0

    reward_programs = reward_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program

    # create new motion to top up reward program
    tx = easy_track.createMotion(
        top_up_reward_programs,
        encode_single("(address[],uint256[])", [[reward_program.address], [int(5e18)]]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    assert ldo_token.balanceOf(reward_program) == 0

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo_token.balanceOf(reward_program) == 5e18

    # create new motion to remove reward program
    tx = easy_track.createMotion(
        remove_reward_program,
        encode_single("(address)", [reward_program.address]),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0
    assert len(reward_programs_registry.getRewardPrograms()) == 0


def test_lego_easy_track(
    stranger,
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
    deployer = accounts[0]
    trusted_address = accounts[7]
    voting_helper = VotingHelper(chain, token_manager, voting)

    # deploy easy track
    easy_track_logic = deployer.deploy(EasyTrack)

    # init easy track and grant admin permissions to deployer
    easy_track_proxy = deployer.deploy(
        ContractProxy,
        easy_track_logic,
        easy_track_logic.__EasyTrackStorage_init.encode_input(ldo_token, deployer),
    )
    easy_track = Contract.from_abi("EasyTrackProxied", easy_track_proxy, EasyTrack.abi)

    # deploy evm script executor
    evm_script_executor = deployer.deploy(
        EVMScriptExecutor, constants.CALLS_SCRIPT, easy_track, constants.VOTING
    )

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy TopUpLegoProgram EVM script factory
    top_up_lego_program = deployer.deploy(
        TopUpLegoProgram, trusted_address, finance, lego_program
    )

    # add TopUpLegoProgram evm script to registry
    new_immediate_payment_permission = (
        finance.address + finance.newImmediatePayment.signature[2:]
    )
    easy_track.addEVMScriptFactory(
        top_up_lego_program, new_immediate_payment_permission, {"from": deployer}
    )
    evm_script_factories = easy_track.getEVMScriptFactories()
    assert len(evm_script_factories) == 1
    assert evm_script_factories[0] == top_up_lego_program

    # create voting to grant permissions to EVM script executor to create new payments
    add_create_payments_permissions_voting_id = voting_helper.create_voting(
        add_permission_create_new_payments_call_script(evm_script_executor),
        "Grant permissions to EVMScriptExecutor to make payments",
    )

    # execute voting to add permissions to EVM script executor to create payments
    voting_helper.execute_voting(add_create_payments_permissions_voting_id)

    # create new motion to make transfers to lego programs
    ldo_amount, steth_amount, eth_amount = 10 ** 18, 2 * 10 ** 18, 3 * 10 ** 18

    tx = easy_track.createMotion(
        top_up_lego_program,
        encode_single(
            "(address[],uint256[])",
            [
                [ldo_token.address, steth_token.address, ZERO_ADDRESS],
                [ldo_amount, steth_amount, eth_amount],
            ],
        ),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    # top up agent balances
    ldo_token.approve(agent, ldo_amount, {"from": constants.LDO_WHALE_HOLDER})
    agent.deposit(ldo_token, ldo_amount, {"from": constants.LDO_WHALE_HOLDER})

    steth_token.submit(ZERO_ADDRESS, {"from": deployer, "value": "2.1 ether"})
    steth_token.approve(agent, "2.1 ether", {"from": deployer})
    agent.deposit(steth_token, steth_amount, {"from": deployer})

    agent.deposit(ZERO_ADDRESS, eth_amount, {"from": deployer, "value": eth_amount})

    # validate agent app has enough tokens
    assert agent.balance(ldo_token) >= ldo_amount
    assert agent.balance(steth_token) >= steth_amount
    assert agent.balance(ZERO_ADDRESS) >= eth_amount

    assert ldo_token.balanceOf(lego_program) == 0
    assert steth_token.balanceOf(lego_program) == 0
    assert lego_program.balance() == 100 * 10 ** 18

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo_token.balanceOf(lego_program) == ldo_amount
    assert abs(steth_token.balanceOf(lego_program) - steth_amount) <= 10
    assert lego_program.balance() == 103 * 10 ** 18


class VotingHelper:
    def __init__(self, chain, token_manager, voting):
        self.chain = chain
        self.token_manager = token_manager
        self.voting = voting

    def create_voting(self, evm_script, description):
        add_node_operators_voting_tx = self.token_manager.forward(
            encode_call_script(
                [
                    (
                        self.voting.address,
                        self.voting.newVote.encode_input(evm_script, description),
                    )
                ]
            ),
            {"from": constants.LDO_WHALE_HOLDER},
        )
        return add_node_operators_voting_tx.events["StartVote"]["voteId"]

    def execute_voting(self, voting_id):
        self.voting.vote(voting_id, True, False, {"from": constants.LDO_WHALE_HOLDER})
        self.chain.sleep(3 * 60 * 60 * 24)
        self.chain.mine()
        assert self.voting.canExecute(voting_id)
        self.voting.executeVote(voting_id, {"from": accounts[0]})


def add_permission_create_new_payments_call_script(entity):
    spec_id = "00000001"
    to_address = constants.ACL[2:]
    app = constants.FINANCE[2:].zfill(64)
    role = "5de467a460382d13defdc02aacddc9c7d6605d6d4e0b8bd2f70732cae8ea17bc"  # create new payments role
    calldata_length = "00000064"
    method_id = "0a8ed3db"
    return (
        spec_id
        + to_address
        + calldata_length
        + method_id
        + entity.address[2:].zfill(64)
        + app
        + role
    )


def add_permission_set_node_operators_stakin_limit_call_script(
    entity,
):
    spec_id = "00000001"
    to_address = constants.ACL[2:]

    app = constants.NODE_OPERATORS_REGISTRY[2:].zfill(64)
    role = "07b39e0faf2521001ae4e58cb9ffd3840a63e205d288dc9c93c3774f0d794754"  # set staking limit role
    calldata_length = "00000064"
    method_id = "0a8ed3db"
    return (
        spec_id
        + to_address
        + calldata_length
        + method_id
        + entity.address[2:].zfill(64)
        + app
        + role
    )
