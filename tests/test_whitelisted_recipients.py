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
    WhitelistedRecipientsRegistry,
    TopUpWhitelistedRecipients,
    AddWhitelistedRecipient,
    RemoveWhitelistedRecipient,
):
    deployer = accounts[0]
    whitelisted_recipient = accounts[5]
    whitelisted_recipient_title = "New Whitelisted Recipient"
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

    # deploy WhitelistedRecipientsRegistry
    whitelisted_recipients_registry = deployer.deploy(
        WhitelistedRecipientsRegistry,
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        easy_track
    )

    # deploy TopUpWhitelistedRecipients EVM script factory
    top_up_whitelisted_recipients = deployer.deploy(
        TopUpWhitelistedRecipients,
        trusted_address,
        whitelisted_recipients_registry,
        finance,
        ldo
    )

    # add TopUpWhitelistedRecipients EVM script factory to easy track
    new_immediate_payment_permission = create_permission(
        finance,
        "newImmediatePayment"
    )

    update_limit_permission = create_permission(
        whitelisted_recipients_registry,
        "checkAndUpdateLimits"
    )

    permissions = new_immediate_payment_permission  + update_limit_permission[2:]

    easy_track.addEVMScriptFactory(
        top_up_whitelisted_recipients, permissions, {"from": deployer}
    )

    # deploy AddWhitelistedRecipient EVM script factory
    add_whitelisted_recipient = deployer.deploy(
        AddWhitelistedRecipient, trusted_address, whitelisted_recipients_registry
    )

    # add AddWhitelistedRecipient EVM script factory to easy track
    add_whitelisted_recipient_permission = create_permission(
        whitelisted_recipients_registry,
        "addWhitelistedRecipient"
    )

    easy_track.addEVMScriptFactory(
        add_whitelisted_recipient, add_whitelisted_recipient_permission, {"from": deployer}
    )

    # deploy RemoveWhitelistedRecipient EVM script factory
    remove_whitelisted_recipient = deployer.deploy(
        RemoveWhitelistedRecipient, trusted_address, whitelisted_recipients_registry
    )

    # add RemoveWhitelistedRecipient EVM script factory to easy track
    remove_whitelisted_recipient_permission = create_permission(
        whitelisted_recipients_registry,
        "removeWhitelistedRecipient"
    )
    easy_track.addEVMScriptFactory(
        remove_whitelisted_recipient, remove_whitelisted_recipient_permission, {"from": deployer}
    )

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

    add_whitelisted_recipient_calldata = encode_calldata(
            "(address,string)", [
                whitelisted_recipient.address,
                whitelisted_recipient_title
            ]
    )

    # create new motion to add a whitelisted recipient
    expected_evm_script = add_whitelisted_recipient.createEVMScript(
        trusted_address,
        add_whitelisted_recipient_calldata
    )

    tx = easy_track.createMotion(
        add_whitelisted_recipient,
        add_whitelisted_recipient_calldata,
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

    whitelisted_recipients = whitelisted_recipients_registry.getWhitelistedRecipients()
    assert len(whitelisted_recipients) == 1
    assert whitelisted_recipients[0] == whitelisted_recipient

    Jul1 = 1656633600 # Fri Jul 01 2022 00:00:00 GMT+0000
    Aug1 = 1659312000 # Mon Aug 01 2022 00:00:00 GMT+0000
    Sep1 = 1661990400 # Thu Sep 01 2022 00:00:00 GMT+0000
    Okt1 = 1664582400 # Sat Oct 01 2022 00:00:00 GMT+0000

    #set limit parameters
    limit = 20e18
    spent = 0
    periodDurationMonth = 3 #month
    periodStart = Jul1
    periodEnd = Okt1

    # create voting to set limit parameters
    netname = "goerli" if network_name().split('-')[0] == "goerli" else "mainnet"

    set_limit_parameters_voting_id, _ = create_voting(
        evm_script=encode_call_script(
            [
                (
                    whitelisted_recipients_registry.address,
                    whitelisted_recipients_registry.setLimitParameters.encode_input(
                        limit,
                        periodDurationMonth,
                    ),
                ),
            ]
        ),
        description = "Set limit parameters",
        network = netname,
        tx_params = {"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(set_limit_parameters_voting_id, netname)

    assert whitelisted_recipients_registry.getLimitParameters()[0] == limit
    assert whitelisted_recipients_registry.getLimitParameters()[1] == periodDurationMonth

    currentPeriodState = whitelisted_recipients_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    # create new motion to top up whitelisted address
    _evmScriptCallData1 = encode_single("(address[],uint256[])",
            [[whitelisted_recipient.address,whitelisted_recipient.address],
            [int(5e18), int(7e18)]])
    tx1 = easy_track.createMotion(
        top_up_whitelisted_recipients,
        _evmScriptCallData1,
        {"from": trusted_address},
    )
    assert len(easy_track.getMotions()) == 1

    chain.sleep(60)

    _evmScriptCallData2 = encode_single("(address[],uint256[])",
            [[whitelisted_recipient.address,whitelisted_recipient.address],
            [int(5e18), int(7e18)]])
    tx2 = easy_track.createMotion(
        top_up_whitelisted_recipients,
        _evmScriptCallData2,
        {"from": trusted_address},
    )
    assert len(easy_track.getMotions()) == 2

    chain.sleep(48 * 60 * 60 + 1)

    currentPeriodState = whitelisted_recipients_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    assert ldo.balanceOf(whitelisted_recipient) == 0
    motions = easy_track.getMotions()
    easy_track.enactMotion(
        motions[0][0],
        tx1.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    spent += 5e18 + 7e18

    currentPeriodState = whitelisted_recipients_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd

    assert len(easy_track.getMotions()) == 1
    assert ldo.balanceOf(whitelisted_recipient) == spent

    chain.sleep(60)

    motions = easy_track.getMotions()
    assert len(motions) == 1
    with reverts("SUM_EXCEEDS_LIMIT"):
        easy_track.enactMotion(
            motions[0][0],
            tx2.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

    currentPeriodState = whitelisted_recipients_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd
    assert len(easy_track.getMotions()) == 1
    assert ldo.balanceOf(whitelisted_recipient) == spent

    easy_track.cancelMotion(
        motions[0][0],
        {"from": trusted_address}
    )

    currentPeriodState = whitelisted_recipients_registry.getCurrentPeriodState()
    assert currentPeriodState[0] == spent
    assert currentPeriodState[1] == limit - spent
    assert currentPeriodState[2] == periodStart
    assert currentPeriodState[3] == periodEnd
    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(whitelisted_recipient) == spent


    # create new motion to remove a whitelisted recipient
    tx = easy_track.createMotion(
        remove_whitelisted_recipient,
        encode_single("(address)", [whitelisted_recipient.address]),
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
    assert len(whitelisted_recipients_registry.getWhitelistedRecipients()) == 0
