import pytest
import constants

from brownie.network import chain
from brownie import (
    EasyTrack,
    EVMScriptExecutor,
    accounts
)

from eth_abi import encode_single
from utils.evm_script import encode_call_script

from utils.config import get_network_name

from utils.lido import create_voting, execute_voting

def encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]

def test_reward_programs_easy_track(
    stranger,
    agent,
    voting,
    finance,
    ldo,
    calls_script,
    acl,
    RewardProgramsRegistry,
    TopUpRewardPrograms,
    AddRewardProgram,
    RemoveRewardProgram,
):
    deployer = accounts[0]
    reward_program = accounts[5]
    reward_program_title = "Our Reward Program"
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

    # deploy TopUpRewardPrograms EVM script factory
    top_up_reward_programs = deployer.deploy(
        TopUpRewardPrograms,
        trusted_address,
        reward_programs_registry,
        finance,
        ldo,
    )

    # add TopUpRewardPrograms EVM script factory to easy track
    new_immediate_payment_permission = create_permission(
        finance,
        "newImmediatePayment"
    )

    easy_track.addEVMScriptFactory(
        top_up_reward_programs, new_immediate_payment_permission, {"from": deployer}
    )

    # deploy AddRewardProgram EVM script factory
    add_reward_program = deployer.deploy(
        AddRewardProgram, trusted_address, reward_programs_registry
    )

    # add AddRewardProgram EVM script factory to easy track
    add_reward_program_permission = create_permission(
        reward_programs_registry,
        "addRewardProgram"
    )

    easy_track.addEVMScriptFactory(
        add_reward_program, add_reward_program_permission, {"from": deployer}
    )

    # deploy RemoveRewardProgram EVM script factory
    remove_reward_program = deployer.deploy(
        RemoveRewardProgram, trusted_address, reward_programs_registry
    )

    # add RemoveRewardProgram EVM script factory to easy track
    remove_reward_program_permission = create_permission(
        reward_programs_registry,
        "removeRewardProgram"
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
    add_create_payments_permissions_voting_id, _ = create_voting(
        evm_script=encode_call_script(
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
        network=get_network_name(),
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(add_create_payments_permissions_voting_id, get_network_name())

    add_reward_program_calldata = encode_calldata(
            "(address,string)", [
                reward_program.address,
                reward_program_title
            ]
    )
    # create new motion to add a reward program
    expected_evm_script = add_reward_program.createEVMScript(
        trusted_address,
        add_reward_program_calldata
    )

    tx = easy_track.createMotion(
        add_reward_program,
        add_reward_program_calldata,
        {"from": trusted_address}
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

    assert ldo.balanceOf(reward_program) == 0

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(reward_program) == 5e18

    # create new motion to remove a reward program
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
