import constants

from brownie.network import chain
from brownie import (
    EasyTrack,
    EVMScriptExecutor,
    accounts,
    reverts
)

from eth_abi import encode_single
from utils.evm_script import encode_call_script

from utils.config import (
    network_name
)

from utils.lido import create_voting, execute_voting, addresses

def encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]

def test_limited_programs_easy_track(
    stranger,
    agent,
    voting,
    finance,
    ldo,
    calls_script,
    acl,
    LimitedProgramsRegistry,
    TopUpLimitedPrograms,
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

    # deploy LimitedProgramsRegistry
    limited_programs_registry = deployer.deploy(
        LimitedProgramsRegistry,
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        easy_track
    )

    # deploy TopUpLimitedPrograms EVM script factory
    top_up_limited_programs = deployer.deploy(
        TopUpLimitedPrograms,
        trusted_address,
        limited_programs_registry,
        finance,
        ldo
    )


    # add TopUpRewardPrograms EVM script factory to easy track
    new_immediate_payment_permission = create_permission(
        finance,
        "newImmediatePayment"
    )

    update_limit_permission = create_permission(
        top_up_limited_programs,
        "_checkAndUpdateLimits"
    )

    permissions = new_immediate_payment_permission  + update_limit_permission[2:]

    easy_track.addEVMScriptFactory(
        top_up_limited_programs, permissions, {"from": deployer}
    )

    # deploy AddRewardProgram EVM script factory
    add_reward_program = deployer.deploy(
        AddRewardProgram, trusted_address, limited_programs_registry
    )

    # add AddRewardProgram EVM script factory to easy track
    add_reward_program_permission = create_permission(
        limited_programs_registry,
        "addRewardProgram"
    )

    easy_track.addEVMScriptFactory(
        add_reward_program, add_reward_program_permission, {"from": deployer}
    )

    # deploy RemoveRewardProgram EVM script factory
    remove_reward_program = deployer.deploy(
        RemoveRewardProgram, trusted_address, limited_programs_registry
    )

    # add RemoveRewardProgram EVM script factory to easy track
    remove_reward_program_permission = create_permission(
        limited_programs_registry,
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

    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

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
        network=netname,
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(add_create_payments_permissions_voting_id, netname)

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

    reward_programs = limited_programs_registry.getRewardPrograms()
    assert len(reward_programs) == 1
    assert reward_programs[0] == reward_program

    Jan1 = 1640995200 # Sat Jan 01 2022 00:00:00 GMT+0000
    Jun1 = 1654041600 # Wed Jun 01 2022 00:00:00 GMT+0000
    Jul1 = 1656633600 # Fri Jul 01 2022 00:00:00 GMT+0000;
    Aug1 = 1659312000 # Mon Aug 01 2022 00:00:00 GMT+0000
    Sep1 = 1661990400 # Thu Sep 01 2022 00:00:00 GMT+0000
    Okt1 = 1664582400 # Sat Oct 01 2022 00:00:00 GMT+0000
    Now = 1659948942 # Mon Aug 08 2022 08:55:42 GMT+0000

    '''
    _evmScriptCallData = encode_single("(uint256,address[],address[],uint256[])",
            [Jul1,
            [addresses().ldo, addresses().ldo],
            [reward_program.address,reward_program.address],
            [int(5e18), int(7e18)]])
    '''

    #set limit parameters
    limit = 20e18
    spent = 0
    periodDurationMonth = 3 #month
    periodStart = Jul1
    periodEnd = Okt1
    limited_programs_registry.setLimitParameters(limit, periodDurationMonth)
    assert limited_programs_registry.getLimitParameters()[0] == limit
    assert limited_programs_registry.getLimitParameters()[1] == periodDurationMonth
    currentPeriodState = limited_programs_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    # create new motion to top up reward program
    _evmScriptCallData1 = encode_single("(address[],uint256[])",
            [[reward_program.address,reward_program.address],
            [int(5e18), int(7e18)]])
    tx1 = easy_track.createMotion(
        top_up_limited_programs,
        _evmScriptCallData1,
        {"from": trusted_address},
    )
    assert len(easy_track.getMotions()) == 1

    chain.sleep(60)

    _evmScriptCallData2 = encode_single("(address[],uint256[])",
            [[reward_program.address,reward_program.address],
            [int(5e18), int(7e18)]])
    tx2 = easy_track.createMotion(
        top_up_limited_programs,
        _evmScriptCallData2,
        {"from": trusted_address},
    )
    assert len(easy_track.getMotions()) == 2

    chain.sleep(48 * 60 * 60 + 1)

    currentPeriodState = limited_programs_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    assert ldo.balanceOf(reward_program) == 0
    motions = easy_track.getMotions()
    easy_track.enactMotion(
        motions[0][0],
        tx1.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    spent += 5e18 + 7e18

    currentPeriodState = limited_programs_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    assert len(easy_track.getMotions()) == 1
    assert ldo.balanceOf(reward_program) == spent

    chain.sleep(60)

    motions = easy_track.getMotions()
    assert len(motions) == 1
    with reverts("SUM_EXCEEDS_LIMIT"):
        easy_track.enactMotion(
            motions[0][0],
            tx2.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

    currentPeriodState = limited_programs_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd
    assert len(easy_track.getMotions()) == 1
    assert ldo.balanceOf(reward_program) == spent

    #spent =  5e18 + 7e18
    easy_track.cancelMotion(
        motions[0][0],
        {"from": trusted_address}
    )

    currentPeriodState = limited_programs_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd
    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(reward_program) == spent


'''

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
    assert len(limited_programs_registry.getRewardPrograms()) == 0
'''
