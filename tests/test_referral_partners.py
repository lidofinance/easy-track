import pytest
import constants

from brownie.network import chain
from brownie import (
    EasyTrack,
    EVMScriptExecutor,
    accounts,
    ZERO_ADDRESS,
    reverts,
    history,
)

from eth_abi import encode_single
from utils.evm_script import encode_call_script

from utils.config import (
    network_name
)

from utils.lido import create_voting, execute_voting

def encode_calldata(signature, values):
    return "0x" + encode_single(signature, values).hex()

def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]

@pytest.mark.skip_coverage
def test_referral_partners_easy_track(
    stranger,
    agent,
    voting,
    finance,
    ldo,
    calls_script,
    acl,
    ReferralPartnersRegistry,
    TopUpReferralPartners,
    AddReferralPartner,
    RemoveReferralPartner,
):
    deployer = accounts[0]
    referral_partner = accounts[5]
    referral_partner_title = "Our Referral Partner"
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

    # deploy ReferralPartnersRegistry
    referral_partners_registry = deployer.deploy(
        ReferralPartnersRegistry,
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
    )

    # deploy TopUpReferralPartners EVM script factory
    top_up_referral_partners = deployer.deploy(
        TopUpReferralPartners,
        trusted_address,
        referral_partners_registry,
        finance,
        ldo,
    )

    # add TopUpReferralPartner EVM script factory to easy track
    new_immediate_payment_permission = create_permission(
        finance,
        "newImmediatePayment"
    )

    easy_track.addEVMScriptFactory(
        top_up_referral_partners, new_immediate_payment_permission, {"from": deployer}
    )

    # deploy AddReferralPartner EVM script factory
    add_referral_partner = deployer.deploy(
        AddReferralPartner, trusted_address, referral_partners_registry
    )

    # add AddReferralPartner EVM script factory to easy track
    add_referral_partner_permission = create_permission(
        referral_partners_registry,
        "addReferralPartner"
    )

    print(add_referral_partner_permission)

    easy_track.addEVMScriptFactory(
        add_referral_partner, add_referral_partner_permission, {"from": deployer}
    )

    # deploy RemoveReferralPartner EVM script factory
    remove_referral_partner = deployer.deploy(
        RemoveReferralPartner, trusted_address, referral_partners_registry
    )

    # add RemoveReferralPartner EVM script factory to easy track
    remove_referral_partner_permission = create_permission(
        referral_partners_registry,
        "removeReferralPartner"
    )
    easy_track.addEVMScriptFactory(
        remove_referral_partner, remove_referral_partner_permission, {"from": deployer}
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

    add_ref_partner_calldata = encode_calldata(
            "(address,string)", [
                referral_partner.address,
                referral_partner_title
            ]
    )
    # create new motion to add referral partner
    expected_evm_script = add_referral_partner.createEVMScript(
        trusted_address,
        add_ref_partner_calldata
    )

    tx = easy_track.createMotion(
        add_referral_partner,
        add_ref_partner_calldata,
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

    referral_partners = referral_partners_registry.getReferralPartners()
    assert len(referral_partners) == 1
    assert referral_partners[0] == referral_partner

    # create new motion to top up reward program
    tx = easy_track.createMotion(
        top_up_referral_partners,
        encode_single("(address[],uint256[])", [[referral_partner.address], [int(5e18)]]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    chain.sleep(48 * 60 * 60 + 100)

    assert ldo.balanceOf(referral_partner) == 0

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(referral_partner) == 5e18

    # create new motion to remove referral partner
    tx = easy_track.createMotion(
        remove_referral_partner,
        encode_single("(address)", [referral_partner.address]),
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
    assert len(referral_partners_registry.getReferralPartners()) == 0
