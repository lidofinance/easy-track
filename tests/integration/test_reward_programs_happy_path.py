import pytest
import brownie
import constants

from utils import evm_script, lido


@pytest.mark.skip_coverage
def test_reward_programs_easy_track(
    stranger,
    agent,
    voting,
    finance,
    ldo,
    calls_script,
    acl,
    EasyTrack,
    EVMScriptExecutor,
    RewardProgramsRegistry,
    TopUpRewardPrograms,
    AddRewardProgram,
    RemoveRewardProgram,
    lido_contracts,
    deployer,
    accounts,
):
    reward_program = accounts[5]
    reward_program_title = "New Reward Program"
    trusted_address = accounts[7]

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

    # deploy RewardProgramsRegistry
    reward_programs_registry = deployer.deploy(
        RewardProgramsRegistry,
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
    )

    # deploy TopUpRewardProgram EVM script factory
    top_up_reward_programs = deployer.deploy(
        TopUpRewardPrograms,
        trusted_address,
        reward_programs_registry,
        finance,
        ldo,
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
    easy_track.grantRole(easy_track.DEFAULT_ADMIN_ROLE(), voting, {"from": deployer})
    assert easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), voting)
    easy_track.revokeRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, {"from": deployer})
    assert not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer)

    # create voting to grant permissions to EVM script executor to create new payments
    add_create_payments_permissions_voting_id, _ = lido_contracts.create_voting(
        evm_script=evm_script.encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(
                        evm_script_executor,
                        finance,
                        finance.CREATE_PAYMENTS_ROLE(),
                    ),
                ),
            ]
        ),
        description="Grant permissions to EVMScriptExecutor to make payments",
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    lido_contracts.execute_voting(add_create_payments_permissions_voting_id)

    # create new motion to add reward program
    tx = easy_track.createMotion(
        add_reward_program,
        evm_script.encode_calldata(
            "(address,string)", [reward_program.address, reward_program_title]
        ),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(48 * 60 * 60 + 100)

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
        evm_script.encode_calldata(
            "(address[],uint256[])", [[reward_program.address], [int(5e18)]]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(48 * 60 * 60 + 100)

    assert ldo.balanceOf(reward_program) == 0

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(reward_program) == 5e18

    # create new motion to remove reward program
    tx = easy_track.createMotion(
        remove_reward_program,
        evm_script.encode_calldata("(address)", [reward_program.address]),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(48 * 60 * 60 + 100)

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0
    assert len(reward_programs_registry.getRewardPrograms()) == 0
