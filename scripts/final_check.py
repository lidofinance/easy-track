from brownie import (
    Wei,
    chain,
    accounts,
    network,
    EasyTrack,
    EVMScriptExecutor,
    IncreaseNodeOperatorStakingLimit,
    TopUpLegoProgram,
    RewardProgramsRegistry,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    web3,
    ZERO_ADDRESS,
)
from utils import lido, constants, log, mainnet_fork, evm_script
from eth_abi import encode_single
from scripts.grant_executor_permissions import grant_executor_permissions
from brownie.network.account import PublicKeyAccount


def main():
    deployer = "0x2a61d3ba5030Ef471C74f612962c7367ECa3a62d"
    lego_committee_multisig = "0x12a43b049A7D330cB8aEAB5113032D18AE9a9030"
    reward_programs_multisig = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
    pause_address = "0x73b047fe6337183A454c5217241D780a932777bD"

    lido_contracts = lido.contracts(network="mainnet")

    easy_track = EasyTrack.at("0xF0211b7660680B49De1A7E9f25C65660F0a13Fea")
    evm_script_executor = EVMScriptExecutor.at(
        "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
    )
    increase_node_operators_staking_limit = IncreaseNodeOperatorStakingLimit.at(
        "0xFeBd8FAC16De88206d4b18764e826AF38546AfE0"
    )
    top_up_lego_program = TopUpLegoProgram.at(
        "0x648C8Be548F43eca4e482C0801Ebccccfb944931"
    )
    reward_programs_registry = RewardProgramsRegistry.at(
        "0x3129c041b372ee93a5a8756dc4ec6f154d85bc9a"
    )
    add_reward_program = AddRewardProgram.at(
        "0x9D15032b91d01d5c1D940eb919461426AB0dD4e3"
    )
    remove_reward_program = RemoveRewardProgram.at(
        "0xc21e5e72Ffc223f02fC410aAedE3084a63963932"
    )
    top_up_reward_programs = TopUpRewardPrograms.at(
        "0x77781A93C4824d2299a38AC8bBB11eb3cd6Bc3B7"
    )

    log.ok("LEGO Program Multisig", lego_committee_multisig)
    log.ok("Reward Programs Multisig", reward_programs_multisig)
    log.ok("Easy Track Pause Multisig", pause_address)

    print()

    validate_easy_track_setup(
        easy_track=easy_track,
        evm_script_executor=evm_script_executor,
        lido_contracts=lido_contracts,
        pause_address=pause_address,
        deployer=deployer,
    )
    validate_evm_script_executor_setup(
        evm_script_executor=evm_script_executor,
        easy_track=easy_track,
        lido_contracts=lido_contracts,
    )
    validate_increase_node_operator_staking_limit_setup(
        increase_node_operators_staking_limit=increase_node_operators_staking_limit,
        lido_contracts=lido_contracts,
    )
    validate_top_up_lego_program_setup(
        lido_contracts=lido_contracts,
        top_up_lego_program=top_up_lego_program,
        lego_committee_multisig=lego_committee_multisig,
    )
    validate_reward_programs_registry_setup(
        deployer=deployer,
        lido_contracts=lido_contracts,
        evm_script_executor=evm_script_executor,
        reward_programs_registry=reward_programs_registry,
    )
    validate_add_reward_program_setup(
        add_reward_program=add_reward_program,
        reward_programs_multisig=reward_programs_multisig,
        reward_programs_registry=reward_programs_registry,
    )
    validate_remove_reward_program(
        remove_reward_program=remove_reward_program,
        reward_programs_multisig=reward_programs_multisig,
        reward_programs_registry=reward_programs_registry,
    )
    validate_top_up_reward_programs(
        lido_contracts=lido_contracts,
        top_up_reward_programs=top_up_reward_programs,
        reward_programs_multisig=reward_programs_multisig,
        reward_programs_registry=reward_programs_registry,
    )

    if network.show_active() != "development":
        print("Running on a live network, cannot run further checks.")
        print("Run on a mainnet fork to do this.")
        return

    print()

    with mainnet_fork.chain_snapshot():
        print()
        reward_program_address = accounts[0].address
        simulate_reward_program_addition(
            expected_motion_id=1,
            easy_track=easy_track,
            add_reward_program=add_reward_program,
            reward_program_address=reward_program_address,
            reward_programs_multisig=reward_programs_multisig,
            reward_programs_registry=reward_programs_registry,
        )
        # grant permissions to evm script executor roles to make payments
        # and increase node operators staking limit
        grant_aragon_permissions(
            lido_contracts=lido_contracts, evm_script_executor=evm_script_executor
        )
        simulate_reward_program_top_up(
            easy_track=easy_track,
            expected_motion_id=2,
            lido_contracts=lido_contracts,
            top_up_reward_programs=top_up_reward_programs,
            reward_program_address=reward_program_address,
            reward_programs_multisig=reward_programs_multisig,
        )
        simulate_reward_program_removing(
            easy_track=easy_track,
            expected_motion_id=3,
            remove_reward_program=remove_reward_program,
            reward_program_address=reward_program_address,
            reward_programs_multisig=reward_programs_multisig,
            reward_programs_registry=reward_programs_registry,
        )
        simulate_lego_program_top_up(
            lido_contracts=lido_contracts,
            easy_track=easy_track,
            expected_motion_id=4,
            top_up_lego_program=top_up_lego_program,
            lego_committee_multisig=lego_committee_multisig,
        )
        simulate_node_operator_increases_staking_limit(
            easy_track=easy_track,
            lido_contracts=lido_contracts,
            increase_node_operator_staking_limit=increase_node_operators_staking_limit,
            expected_motion_id=5,
        )
        simulate_pause_by_multisig(easy_track=easy_track, pause_multisig=pause_address)
        simulate_unpause_by_voting(
            easy_track=easy_track,
            pause_multisig=pause_address,
            lido_contracts=lido_contracts,
        )


def validate_easy_track_setup(
    easy_track, evm_script_executor, lido_contracts, pause_address, deployer
):
    log.nb("EasyTrack", easy_track)
    assert_equals(
        "  governanceToken:", easy_track.governanceToken(), lido_contracts.ldo
    )
    assert_equals(
        "  evmScriptExecutor", easy_track.evmScriptExecutor(), evm_script_executor
    )
    assert_equals(
        "  motionDuration",
        easy_track.motionDuration(),
        constants.INITIAL_MOTION_DURATION,
    )
    assert_equals(
        "  motionsCountLimit",
        easy_track.motionsCountLimit(),
        constants.INITIAL_MOTIONS_COUNT_LIMIT,
    )
    assert_equals(
        "  objectionsThreshold",
        easy_track.objectionsThreshold(),
        constants.INITIAL_OBJECTIONS_THRESHOLD,
    )
    assert_equals(
        "  voting has DEFAULT_ADMIN role",
        easy_track.hasRole(
            easy_track.DEFAULT_ADMIN_ROLE(), lido_contracts.aragon.voting
        ),
        True,
    )
    assert_equals(
        "  voting has PAUSE role",
        easy_track.hasRole(easy_track.PAUSE_ROLE(), lido_contracts.aragon.voting),
        True,
    )
    assert_equals(
        "  voting has UNPAUSE role",
        easy_track.hasRole(easy_track.UNPAUSE_ROLE(), lido_contracts.aragon.voting),
        True,
    )
    assert_equals(
        "  voting has CANCEL role",
        easy_track.hasRole(easy_track.CANCEL_ROLE(), lido_contracts.aragon.voting),
        True,
    )
    assert_equals(
        "  pause multisig has PAUSE role",
        easy_track.hasRole(easy_track.PAUSE_ROLE(), pause_address),
        True,
    )
    assert_equals(
        "  deployer has DEFAULT_ADMIN role",
        easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer),
        False,
    )
    print()


def validate_evm_script_executor_setup(evm_script_executor, easy_track, lido_contracts):
    log.nb("EVMScriptExecutor", evm_script_executor)
    assert_equals(
        "  callsScript",
        evm_script_executor.callsScript(),
        lido_contracts.aragon.calls_script,
    )
    assert_equals("  easyTrack", evm_script_executor.easyTrack(), easy_track)
    assert_equals("  owner", evm_script_executor.owner(), lido_contracts.aragon.voting)
    print()


def validate_increase_node_operator_staking_limit_setup(
    increase_node_operators_staking_limit, lido_contracts
):
    log.nb("IncreaseNodeOperatorsStakingLimit", increase_node_operators_staking_limit)
    assert_equals(
        "  nodeOperatorsRegistry:",
        increase_node_operators_staking_limit.nodeOperatorsRegistry(),
        lido_contracts.node_operators_registry,
    )
    print()


def validate_top_up_lego_program_setup(
    top_up_lego_program, lido_contracts, lego_committee_multisig
):
    log.nb("TopUpLegoProgram", top_up_lego_program)
    assert_equals(
        "  finance", top_up_lego_program.finance(), lido_contracts.aragon.finance
    )
    assert_equals(
        "  legoProgram", top_up_lego_program.legoProgram(), lego_committee_multisig
    )
    assert_equals(
        "  trustedCaller",
        top_up_lego_program.trustedCaller(),
        lego_committee_multisig,
    )
    print()


def validate_reward_programs_registry_setup(
    reward_programs_registry, deployer, evm_script_executor, lido_contracts
):
    log.nb("RewardProgramsRegistry", reward_programs_registry)
    assert_equals(
        "  Voting has DEFAULT_ADMIN_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.DEFAULT_ADMIN_ROLE(), lido_contracts.aragon.voting
        ),
        True,
    )
    assert_equals(
        "  Deployer has DEFAULT_ADMIN_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.DEFAULT_ADMIN_ROLE(), deployer
        ),
        False,
    )
    assert_equals(
        "  Voting has ADD_REWARD_PROGRAM_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.ADD_REWARD_PROGRAM_ROLE(),
            lido_contracts.aragon.voting,
        ),
        True,
    )
    assert_equals(
        "  Voting has REMOVE_REWARD_PROGRAM_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE(),
            lido_contracts.aragon.voting,
        ),
        True,
    )
    assert_equals(
        "  EVMScriptExecutor has ADD_REWARD_PROGRAM_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.ADD_REWARD_PROGRAM_ROLE(),
            evm_script_executor,
        ),
        True,
    )
    assert_equals(
        "  EVMScriptExecutor has REMOVE_REWARD_PROGRAM_ROLE",
        reward_programs_registry.hasRole(
            reward_programs_registry.REMOVE_REWARD_PROGRAM_ROLE(),
            evm_script_executor,
        ),
        True,
    )
    print()


def validate_add_reward_program_setup(
    add_reward_program, reward_programs_multisig, reward_programs_registry
):
    log.nb("AddRewardProgram", add_reward_program)
    assert_equals(
        "  trustedCaller",
        add_reward_program.trustedCaller(),
        reward_programs_multisig,
    )
    assert_equals(
        "  rewardProgramsRegistry",
        add_reward_program.rewardProgramsRegistry(),
        reward_programs_registry,
    )
    print()


def validate_remove_reward_program(
    remove_reward_program, reward_programs_multisig, reward_programs_registry
):
    log.nb("RemoveRewardProgram", remove_reward_program)
    assert_equals(
        "  trustedCaller",
        remove_reward_program.trustedCaller(),
        reward_programs_multisig,
    )
    assert_equals(
        "  rewardProgramsRegistry",
        remove_reward_program.rewardProgramsRegistry(),
        reward_programs_registry,
    )
    print()


def validate_top_up_reward_programs(
    top_up_reward_programs,
    reward_programs_multisig,
    lido_contracts,
    reward_programs_registry,
):
    log.nb("TopUpRewardPrograms", top_up_reward_programs)
    assert_equals(
        "  trustedCaller",
        top_up_reward_programs.trustedCaller(),
        reward_programs_multisig,
    )
    assert_equals(
        "  finance", top_up_reward_programs.finance(), lido_contracts.aragon.finance
    )
    assert_equals(
        "  rewardToken", top_up_reward_programs.rewardToken(), lido_contracts.ldo
    )
    assert_equals(
        "  rewardProgramsRegistry",
        top_up_reward_programs.rewardProgramsRegistry(),
        reward_programs_registry,
    )


def grant_aragon_permissions(lido_contracts, evm_script_executor):
    lido_permissions = lido.permissions(contracts=lido_contracts)
    permissions_to_grant = [
        lido_permissions.finance.CREATE_PAYMENTS_ROLE,
        lido_permissions.node_operators_registry.SET_NODE_OPERATOR_LIMIT_ROLE,
    ]
    log.nb("")
    log.nb(
        "Start voting to grant CREATE_PAYMENTS_ROLE and SET_NODE_OPERATOR_LIMIT_ROLE to EVMScriptExecutor",
    )
    log.nb("")
    voting_id = grant_executor_permissions(
        acl=lido_contracts.aragon.acl,
        evm_script_executor=evm_script_executor,
        permissions_to_grant=permissions_to_grant,
        tx_params={"from": lido_contracts.aragon.agent},
    )
    log.ok("  Voting was started. Voting id", voting_id)
    lido.execute_voting(voting_id=voting_id)
    log.ok(f"  Voting {voting_id} successfully passed")
    assert_equals(
        "  EVMScriptExecutor has role CREATE_PAYMENTS_ROLE",
        lido_contracts.aragon.acl.hasPermission(
            evm_script_executor,
            permissions_to_grant[0].app,
            permissions_to_grant[0].role,
        ),
        True,
    )
    assert_equals(
        "  EVMScriptExecutor has role SET_NODE_OPERATOR_LIMIT_ROLE",
        lido_contracts.aragon.acl.hasPermission(
            evm_script_executor,
            permissions_to_grant[1].app,
            permissions_to_grant[1].role,
        ),
        True,
    )
    print()


def simulate_reward_program_addition(
    easy_track,
    reward_program_address,
    add_reward_program,
    reward_programs_multisig,
    reward_programs_registry,
    expected_motion_id,
):
    log.nb("")
    log.nb("Simulate reward program addition via EasyTrack")
    log.nb("")
    add_reward_program_calldata = encode_calldata(
        "(address,string)", [reward_program_address, "Mock Reward Program"]
    )
    log.ok("  Address of new reward program", reward_program_address)
    tx, motion = create_motion(
        easy_track=easy_track,
        evm_script_factory=add_reward_program,
        calldata=add_reward_program_calldata,
        creator=reward_programs_multisig,
    )
    expected_evm_script = add_reward_program.createEVMScript(
        reward_programs_multisig, add_reward_program_calldata
    )
    assert_motion_created_event(
        tx=tx,
        creator=reward_programs_multisig,
        evm_script_factory=add_reward_program,
        evm_script_calldata=add_reward_program_calldata,
        evm_script=expected_evm_script,
    )
    assert_motion(
        motion,
        id=expected_motion_id,
        evm_script_factory=add_reward_program,
        creator=reward_programs_multisig,
        start_date=chain[-1].timestamp,
        snapshot_block=chain[-1].number,
        evm_script=expected_evm_script,
    )
    wait_before_enact(motion)
    enact_motion(
        easy_track=easy_track,
        motion_id=motion[0],
        motion_calldata=add_reward_program_calldata,
    )
    assert_equals(
        "  Reward program was added to RewardProgramsRegistry",
        reward_programs_registry.isRewardProgram(reward_program_address),
        True,
    )
    print()


def simulate_reward_program_top_up(
    easy_track,
    lido_contracts,
    reward_program_address,
    top_up_reward_programs,
    reward_programs_multisig,
    expected_motion_id,
):
    log.nb("")
    log.nb("Simulate reward program top up via EasyTrack")
    log.nb("")
    top_up_amount = Wei(200_000 * 10 ** 18)
    top_up_reward_program_calldata = encode_calldata(
        "(address[],uint256[])",
        [[reward_program_address], [top_up_amount]],
    )
    log.ok("  Address of reward program to top up", reward_program_address)
    log.ok("  Top up amount", top_up_amount)
    assert_equals(
        "  Reward program balance before top up",
        lido_contracts.ldo.balanceOf(reward_program_address),
        0,
    )
    tx, motion = create_motion(
        easy_track=easy_track,
        evm_script_factory=top_up_reward_programs,
        calldata=top_up_reward_program_calldata,
        creator=reward_programs_multisig,
    )
    expected_evm_script = top_up_reward_programs.createEVMScript(
        reward_programs_multisig, top_up_reward_program_calldata
    )
    assert_motion_created_event(
        tx=tx,
        creator=reward_programs_multisig,
        evm_script_factory=top_up_reward_programs,
        evm_script_calldata=top_up_reward_program_calldata,
        evm_script=expected_evm_script,
    )
    assert_motion(
        motion,
        id=expected_motion_id,
        evm_script_factory=top_up_reward_programs,
        creator=reward_programs_multisig,
        start_date=chain[-1].timestamp,
        snapshot_block=chain[-1].number,
        evm_script=expected_evm_script,
    )
    wait_before_enact(motion)
    enact_motion(
        easy_track=easy_track,
        motion_id=motion[0],
        motion_calldata=top_up_reward_program_calldata,
    )
    assert_equals(
        "  Reward program balance after top up",
        lido_contracts.ldo.balanceOf(reward_program_address),
        top_up_amount,
    )
    print()


def simulate_reward_program_removing(
    easy_track,
    reward_program_address,
    remove_reward_program,
    reward_programs_multisig,
    reward_programs_registry,
    expected_motion_id,
):
    log.nb("")
    log.nb("Simulate reward program removing via EasyTrack")
    log.nb("")
    remove_reward_program_calldata = encode_calldata(
        "(address)", [reward_program_address]
    )
    log.ok("  Address of reward program to remove", reward_program_address)
    assert_equals(
        "  Reward program listed in reward programs registry",
        reward_programs_registry.isRewardProgram(reward_program_address),
        True,
    )
    tx, motion = create_motion(
        easy_track=easy_track,
        evm_script_factory=remove_reward_program,
        calldata=remove_reward_program_calldata,
        creator=reward_programs_multisig,
    )
    expected_evm_script = remove_reward_program.createEVMScript(
        reward_programs_multisig, remove_reward_program_calldata
    )
    assert_motion_created_event(
        tx=tx,
        creator=reward_programs_multisig,
        evm_script_factory=remove_reward_program,
        evm_script_calldata=remove_reward_program_calldata,
        evm_script=expected_evm_script,
    )
    assert_motion(
        motion,
        id=expected_motion_id,
        evm_script_factory=remove_reward_program,
        creator=reward_programs_multisig,
        start_date=chain[-1].timestamp,
        snapshot_block=chain[-1].number,
        evm_script=expected_evm_script,
    )
    wait_before_enact(motion)
    enact_motion(
        easy_track=easy_track,
        motion_id=motion[0],
        motion_calldata=remove_reward_program_calldata,
    )
    assert_equals(
        "  Reward program was removed from reward programs registry",
        not reward_programs_registry.isRewardProgram(reward_program_address),
        True,
    )
    print()


def simulate_lego_program_top_up(
    easy_track,
    lido_contracts,
    expected_motion_id,
    top_up_lego_program,
    lego_committee_multisig,
):
    log.nb("")
    log.nb("Simulate LEGO program top up via EasyTrack")
    log.nb("")
    reward_tokens = [
        ZERO_ADDRESS,
        lido_contracts.ldo.address,
        lido_contracts.steth.address,
    ]
    reward_amounts = [Wei(100 * 10 ** 18), Wei(200_000 * 10 ** 18), Wei(50 * 10 ** 18)]
    top_up_lego_program_calldata = encode_calldata(
        "(address[],uint256[])", [reward_tokens, reward_amounts]
    )
    log.ok("  Address of LEGO program", lego_committee_multisig)
    log.ok("  Tokens to transfer", reward_tokens)
    log.ok("  Amount of tokens to transfer", reward_amounts)
    ldo_balance_before = lido_contracts.ldo.balanceOf(lego_committee_multisig)
    eth_balance_before = PublicKeyAccount(lego_committee_multisig).balance()
    steth_balance_before = lido_contracts.steth.balanceOf(lego_committee_multisig)

    log.ok("  LEGO program ETH balance before top up", eth_balance_before)
    log.ok("  LEGO program LDO balance before top up", ldo_balance_before)
    log.ok("  LEGO program stETH balance before top up", steth_balance_before)
    tx, motion = create_motion(
        easy_track=easy_track,
        evm_script_factory=top_up_lego_program,
        calldata=top_up_lego_program_calldata,
        creator=lego_committee_multisig,
    )
    expected_evm_script = top_up_lego_program.createEVMScript(
        lego_committee_multisig, top_up_lego_program_calldata
    )
    assert_motion_created_event(
        tx=tx,
        creator=lego_committee_multisig,
        evm_script_factory=top_up_lego_program,
        evm_script_calldata=top_up_lego_program_calldata,
        evm_script=expected_evm_script,
    )
    assert_motion(
        motion,
        id=expected_motion_id,
        evm_script_factory=top_up_lego_program,
        creator=lego_committee_multisig,
        start_date=chain[-1].timestamp,
        snapshot_block=chain[-1].number,
        evm_script=expected_evm_script,
    )
    wait_before_enact(motion)
    enact_motion(
        easy_track=easy_track,
        motion_id=motion[0],
        motion_calldata=top_up_lego_program_calldata,
    )
    ldo_balance_after = lido_contracts.ldo.balanceOf(lego_committee_multisig)
    eth_balance_after = accounts.at(lego_committee_multisig).balance()
    steth_balance_after = lido_contracts.steth.balanceOf(lego_committee_multisig)
    assert_equals(
        "  LEGO program ETH balance after top up",
        eth_balance_after,
        eth_balance_before + reward_amounts[0],
    )
    assert_equals(
        "  LEGO program LDO balance after top",
        ldo_balance_after,
        ldo_balance_before + reward_amounts[1],
    )
    assert_equals(
        f"  LEGO program stETH balance after top up equal to {steth_balance_after} to within 1 wei",
        is_almost_equal(steth_balance_after, steth_balance_before + reward_amounts[2]),
        True,
    )
    print()


def simulate_node_operator_increases_staking_limit(
    easy_track, lido_contracts, increase_node_operator_staking_limit, expected_motion_id
):
    (
        node_operator_id,
        staking_limit,
        total_signing_keys,
        node_operator_address,
    ) = add_new_node_operator(lido_contracts)
    log.nb("")
    log.nb("Simulate node operator staking limit increasing via EasyTrack")
    log.nb("")
    log.ok("Node operator id", node_operator_id)
    log.ok("Node operator staking limit before", staking_limit)
    log.ok("Node operator total signing keys", total_signing_keys)
    log.ok("New node operator staking limit to set", total_signing_keys)

    increase_staking_limit_calldata = encode_calldata(
        "(uint256,uint256)", [node_operator_id, total_signing_keys]
    )
    tx, motion = create_motion(
        easy_track=easy_track,
        evm_script_factory=increase_node_operator_staking_limit,
        calldata=increase_staking_limit_calldata,
        creator=node_operator_address,
    )
    expected_evm_script = increase_node_operator_staking_limit.createEVMScript(
        node_operator_address, increase_staking_limit_calldata
    )
    assert_motion_created_event(
        tx=tx,
        creator=node_operator_address,
        evm_script_factory=increase_node_operator_staking_limit,
        evm_script_calldata=increase_staking_limit_calldata,
        evm_script=expected_evm_script,
    )
    assert_motion(
        motion,
        id=expected_motion_id,
        evm_script_factory=increase_node_operator_staking_limit,
        creator=node_operator_address,
        start_date=chain[-1].timestamp,
        snapshot_block=chain[-1].number,
        evm_script=expected_evm_script,
    )
    wait_before_enact(motion)
    enact_motion(
        easy_track=easy_track,
        motion_id=motion[0],
        motion_calldata=increase_staking_limit_calldata,
    )
    node_operator = lido_contracts.node_operators_registry.getNodeOperator(
        node_operator_id, True
    )
    assert_equals("  New node operator staking limit after", node_operator[3], 3)
    print()


def simulate_pause_by_multisig(easy_track, pause_multisig):
    log.nb("")
    log.nb("Simulate pausing via easy track pause multisig")
    log.nb("")
    assert_equals("  EasyTrack is paused", easy_track.paused(), False)
    easy_track.pause({"from": pause_multisig})
    assert_equals("  EasyTrack is paused", easy_track.paused(), True)
    print()


def simulate_unpause_by_voting(easy_track, pause_multisig, lido_contracts):
    log.nb("")
    log.nb("Simulate unpausing via Aragon voting")
    log.nb("")
    assert_equals("  EasyTrack is still paused", easy_track.paused(), True)
    unpause_evm_scirpt = evm_script.encode_call_script(
        [(easy_track.address, easy_track.unpause.encode_input())]
    )
    voting_id, _ = lido.create_voting(
        unpause_evm_scirpt,
        "Unpause EasyTracks",
        {"from": lido_contracts.aragon.agent},
    )
    log.ok("  Voting was started. Voting id", voting_id)
    lido.execute_voting(voting_id)
    log.ok("  Voting was executed")
    assert_equals("  EasyTrack is paused", easy_track.paused(), False)
    print()


def add_new_node_operator(lido_contracts):
    log.nb("")
    log.nb("Start voting to add new node operator to node operators registry to test staking limit increasing via EasyTrack")
    log.nb("")
    node_operators_registry = lido_contracts.node_operators_registry
    # create vote to add test node operator
    node_operator = {"name": "test_node_operator", "address": accounts[3]}
    add_node_operator_calldata = node_operators_registry.addNodeOperator.encode_input(
        node_operator["name"], node_operator["address"]
    )
    add_node_operator_evm_script = evm_script.encode_call_script(
        [(node_operators_registry.address, add_node_operator_calldata)]
    )
    voting_id, _ = lido.create_voting(
        add_node_operator_evm_script,
        "Add node operator to registry",
        {"from": lido_contracts.aragon.agent},
    )
    log.ok("  Voting was started. Voting id", voting_id)
    # execute vote to add test node operator
    lido.execute_voting(voting_id)

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
    log.ok("  Add signing keys to new node operator")
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
    return (
        new_node_operator_id,
        new_node_operator[3],
        new_node_operator[5],
        node_operator["address"],
    )


def wait_before_enact(motion):
    duration, start_date = motion[3], motion[4]
    chain.sleep(duration + 1)
    chain.mine()
    assert_equals(
        "  Motion can be enacted",
        chain[-1].timestamp >= start_date + duration,
        True,
    )


def assert_motion_created_event(
    tx, creator, evm_script_factory, evm_script_calldata, evm_script
):
    assert_equals("  MotionCreated Event Fired", "MotionCreated" in tx.events, True)
    assert_equals(
        "    MotionCreated._creator", tx.events["MotionCreated"]["_creator"], creator
    )
    assert_equals(
        "    MotionCreated._evmScriptFactory",
        tx.events["MotionCreated"]["_evmScriptFactory"],
        evm_script_factory,
    )
    assert_equals(
        "    MotionCreated._evmScriptCallData is correct",
        tx.events["MotionCreated"]["_evmScriptCallData"] == evm_script_calldata,
        True,
    )
    assert_equals(
        "    MotionCreated._evmScript is correct",
        tx.events["MotionCreated"]["_evmScript"] == evm_script,
        True,
    )


def assert_motion(
    motion,
    id,
    evm_script_factory,
    creator,
    start_date,
    snapshot_block,
    evm_script,
    objections_amount=0,
    duration=constants.INITIAL_MOTION_DURATION,
    objections_threshold=constants.INITIAL_OBJECTIONS_THRESHOLD,
):
    log.ok("  Validate new motion")
    assert_equals("    id", motion[0], id)
    assert_equals("    evmScriptFactory", motion[1], evm_script_factory)
    assert_equals("    creator", motion[2], creator)
    assert_equals("    duration", motion[3], duration)
    assert_equals("    startDate", motion[4], start_date)
    assert_equals("    snapshotBlock", motion[5], snapshot_block)
    assert_equals("    objectionsThreshold", motion[6], objections_threshold)
    assert_equals("    objectionsAmount", motion[7], objections_amount)
    assert_equals(
        "    evmScriptHash",
        motion[8],
        web3.keccak(hexstr=str(evm_script)).hex(),
    )


def is_almost_equal(actual, expected, epsilon=1):
    return abs(actual - expected) <= epsilon


def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def create_motion(easy_track, evm_script_factory, calldata, creator):
    count_of_motions_before = len(easy_track.getMotions())
    log.ok("  Sending createMotion transaction...")
    tx = easy_track.createMotion(evm_script_factory, calldata, {"from": creator})
    motions = easy_track.getMotions()
    assert_equals(
        "  New motion was created", len(motions) == count_of_motions_before + 1, True
    )
    return tx, motions[0]


def enact_motion(easy_track, motion_id, motion_calldata):
    log.ok("  Sending enactMotion transaction...")
    easy_track.enactMotion(motion_id, motion_calldata, {"from": accounts[2]})
    assert_equals("  Motion was enacted", len(easy_track.getMotions()) == 0, True)


def encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()
