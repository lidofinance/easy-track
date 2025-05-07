import pytest
import brownie
import json

import constants
import math
from utils import lido, deployment, deployed_date_time, evm_script, log
from utils.config import get_network_name
from dataclasses import dataclass

#####
# CONSTANTS
#####

MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60
STETH_ERROR_MARGIN_WEI = 2

#####
# ACCOUNTS
#####


@pytest.fixture(scope="module")
def deployer(accounts):
    """Default deployer of the contracts"""
    return accounts[0]


@pytest.fixture(scope="module")
def trusted_caller(accounts):
    """EOA used as default trusted caller in the EVM script factories"""
    return accounts[1]


@pytest.fixture(scope="module")
def stranger(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def recipients(accounts):
    @dataclass
    class Recipient:
        address: str
        title: str

    return [
        Recipient(address=accounts[7].address, title="recipient#1"),
        Recipient(address=accounts[8].address, title="recipient#2"),
        Recipient(address=accounts[9].address, title="recipient#3"),
    ]


@pytest.fixture(scope="session")
def deployed_artifact():
    network_name = get_network_name()
    file_name = f"deployed-{network_name}.json"

    try:
        f = open(file_name)
        return json.load(f)
    except:
        pass


#####
# CONTRACTS
#####


@pytest.fixture(scope="module")
def deployed_contracts():
    """
    To run tests on deployed contracts, set their address below
    """
    return {
        "EasyTrack": "",
        "AllowedRecipientsFactory": "",
        "AllowedRecipientsBuilder": "",
        "AllowedRecipientsRegistry": "",
        "AddAllowedRecipient": "",
        "RemoveAllowedRecipient": "",
        "TopUpAllowedRecipients": "",
    }


@pytest.fixture(scope="module")
def load_deployed_contract(deployed_contracts):
    def _load_deployed_contract(contract_name):
        Contract = getattr(brownie, contract_name)

        if Contract is None:
            raise Exception(f"Contract '{contract_name}' not found")

        if contract_name in deployed_contracts and deployed_contracts[contract_name] != "":
            loaded_contract = Contract.at(deployed_contracts[contract_name])
            log.ok(f"Loaded contract: {contract_name}('{loaded_contract.address}')")
            return loaded_contract

    return _load_deployed_contract


@pytest.fixture(scope="module")
def easy_track(
    EasyTrack,
    EVMScriptExecutor,
    lido_contracts,
    deployer,
    load_deployed_contract,
):

    loaded_easy_track = load_deployed_contract("EasyTrack")

    if loaded_easy_track:
        lido_contracts.aragon.acl.grantPermission(
            loaded_easy_track.evmScriptExecutor(),
            lido_contracts.permissions.finance.CREATE_PAYMENTS_ROLE.app,
            lido_contracts.permissions.finance.CREATE_PAYMENTS_ROLE.role,
            {"from": lido_contracts.aragon.voting},
        )

    if not loaded_easy_track is None:
        return loaded_easy_track

    deployed_easy_track = EasyTrack.deploy(
        lido_contracts.ldo,
        lido_contracts.aragon.voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
        {"from": deployer},
    )

    evm_script_executor = EVMScriptExecutor.deploy(
        lido_contracts.aragon.calls_script, deployed_easy_track, {"from": deployer}
    )

    deployed_easy_track.setEVMScriptExecutor(evm_script_executor, {"from": lido_contracts.aragon.voting})
    evm_script_executor.transferOwnership(lido_contracts.aragon.voting, {"from": deployer})

    assert evm_script_executor.owner() == lido_contracts.aragon.voting

    create_payments_permission = lido_contracts.permissions.finance.CREATE_PAYMENTS_ROLE

    if not lido_contracts.aragon.acl.hasPermission(
        evm_script_executor,
        create_payments_permission.app,
        create_payments_permission.role,
    ):
        lido_contracts.aragon.acl.grantPermission(
            evm_script_executor,
            create_payments_permission.app,
            create_payments_permission.role,
            {"from": lido_contracts.aragon.voting},
        )

    return deployed_easy_track


@pytest.fixture(scope="module")
def enact_motion_by_creation_tx(easy_track, stranger):
    def _enact_motion_by_creation_tx(creation_tx):
        motion_id = creation_tx.events["MotionCreated"]["_motionId"]
        motion_calldata = creation_tx.events["MotionCreated"]["_evmScriptCallData"]

        return easy_track.enactMotion(motion_id, motion_calldata, {"from": stranger})

    return _enact_motion_by_creation_tx


####
# EVM SCRIPT FACTORIES
####


@pytest.fixture(scope="module")
def add_allowed_recipient_evm_script_factory(
    AddAllowedRecipient,
    easy_track,
    lido_contracts,
    trusted_caller,
    load_deployed_contract,
    allowed_recipients_builder,
    allowed_recipients_registry,
    deployer,
):

    evm_script_factory = load_deployed_contract("AddAllowedRecipient")

    if evm_script_factory is None:
        tx = allowed_recipients_builder.deployAddAllowedRecipient(
            trusted_caller, allowed_recipients_registry, {"from": deployer}
        )
        evm_script_factory = AddAllowedRecipient.at(tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"])

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            deployment.create_permission(allowed_recipients_registry, "addRecipient"),
            {"from": lido_contracts.aragon.voting},
        )
        log.ok(f"EVM Script Factory AddAllowedRecipient({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


@pytest.fixture(scope="module")
def remove_allowed_recipient_evm_script_factory(
    RemoveAllowedRecipient,
    easy_track,
    lido_contracts,
    load_deployed_contract,
    allowed_recipients_builder,
    allowed_recipients_registry,
    deployer,
    trusted_caller,
):
    evm_script_factory = load_deployed_contract("RemoveAllowedRecipient")

    if evm_script_factory is None:
        tx = allowed_recipients_builder.deployRemoveAllowedRecipient(
            trusted_caller, allowed_recipients_registry, {"from": deployer}
        )

        evm_script_factory = RemoveAllowedRecipient.at(
            tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]
        )

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            deployment.create_permission(allowed_recipients_registry, "removeRecipient"),
            {"from": lido_contracts.aragon.voting},
        )
        log.ok(f"EVM Script Factory RemoveAllowedRecipient({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


@pytest.fixture(scope="module")
def add_allowed_recipient_by_motion(AllowedRecipientsRegistry, easy_track, stranger):
    def _add_allowed_recipient_via_motion(add_allowed_recipient_evm_script_factory, recipient_address, recipient_title):
        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            add_allowed_recipient_evm_script_factory.allowedRecipientsRegistry()
        )

        tx = easy_track.createMotion(
            add_allowed_recipient_evm_script_factory,
            evm_script.encode_calldata(["address", "string"], [recipient_address, recipient_title]),
            {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
        )

        brownie.chain.sleep(easy_track.motionDuration() + 100)

        tx = easy_track.enactMotion(
            tx.events["MotionCreated"]["_motionId"],
            tx.events["MotionCreated"]["_evmScriptCallData"],
            {"from": stranger},
        )

        assert allowed_recipients_registry.isRecipientAllowed(recipient_address)
        return tx

    return _add_allowed_recipient_via_motion


@pytest.fixture(scope="module")
def remove_allowed_recipient_by_motion(AllowedRecipientsRegistry, easy_track, stranger):
    def _remove_recipient_by_motion(remove_allowed_recipient_evm_script_factory, recipient_address):

        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            remove_allowed_recipient_evm_script_factory.allowedRecipientsRegistry()
        )
        call_data = evm_script.encode_calldata(["address"], [recipient_address])

        tx = easy_track.createMotion(
            remove_allowed_recipient_evm_script_factory,
            call_data,
            {"from": remove_allowed_recipient_evm_script_factory.trustedCaller()},
        )

        brownie.chain.sleep(easy_track.motionDuration() + 100)

        tx = easy_track.enactMotion(
            tx.events["MotionCreated"]["_motionId"],
            call_data,
            {"from": stranger},
        )
        assert not allowed_recipients_registry.isRecipientAllowed(recipient_address)
        return tx

    return _remove_recipient_by_motion


@pytest.fixture(scope="module")
def top_up_allowed_recipients_evm_script_factory(
    TopUpAllowedRecipients,
    easy_track,
    lido_contracts,
    load_deployed_contract,
    allowed_recipients_builder,
    allowed_recipients_registry,
    trusted_caller,
    deployer,
):

    evm_script_factory = load_deployed_contract("TopUpAllowedRecipients")

    if evm_script_factory is None:
        tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
            trusted_caller,
            allowed_recipients_registry,
            lido_contracts.ldo,
            {"from": deployer},
        )

        evm_script_factory = TopUpAllowedRecipients.at(
            tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
        )

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            deployment.create_permission(lido_contracts.aragon.finance, "newImmediatePayment")
            + deployment.create_permission(allowed_recipients_registry, "updateSpentAmount")[2:],
            {"from": lido_contracts.aragon.voting},
        )
        log.ok(f"EVM Script Factory TopUpAllowedRecipients({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


@pytest.fixture(scope="module")
def rmc_factories_multisig():
    network_name = get_network_name()
    if network_name == "hardhat":
        return "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"
    else:
        return "0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A"  # QA multisig


@pytest.fixture(scope="module")
def add_mev_boost_relays_evm_script_factory(
    AddMEVBoostRelays,
    rmc_factories_multisig,
    deployed_artifact,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
):
    evm_script_factory = (
        AddMEVBoostRelays.at(deployed_artifact["AddMEVBoostRelays"]["address"])
        if "AddMEVBoostRelays" in deployed_artifact
        else None
    )

    trusted_caller = rmc_factories_multisig
    if evm_script_factory is None:
        evm_script_factory = deployer.deploy(AddMEVBoostRelays, rmc_factories_multisig, mev_boost_relay_allowed_list)

    assert evm_script_factory.trustedCaller() == rmc_factories_multisig
    assert evm_script_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        num_factories_before = len(easy_track.getEVMScriptFactories())
        permission = mev_boost_relay_allowed_list.address + mev_boost_relay_allowed_list.add_relay.signature[2:]

        easy_track.addEVMScriptFactory(
            evm_script_factory,
            permission,
            {"from": lido_contracts.aragon.voting},
        )
        evm_script_factories = easy_track.getEVMScriptFactories()

        # Check that the factory is added to the EasyTrack
        assert len(evm_script_factories) == num_factories_before + 1
        assert evm_script_factory in evm_script_factories

        log.ok(f"EVM Script Factory AddMEVBoostRelays({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


@pytest.fixture(scope="module")
def remove_mev_boost_relays_evm_script_factory(
    RemoveMEVBoostRelays,
    rmc_factories_multisig,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
):
    evm_script_factory = (
        RemoveMEVBoostRelays.at(deployed_artifact["RemoveMEVBoostRelays"]["address"])
        if "RemoveMEVBoostRelays" in deployed_artifact
        else None
    )

    if evm_script_factory is None:
        evm_script_factory = deployer.deploy(RemoveMEVBoostRelays, rmc_factories_multisig, mev_boost_relay_allowed_list)

    assert evm_script_factory.trustedCaller() == rmc_factories_multisig
    assert evm_script_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        num_factories_before = len(easy_track.getEVMScriptFactories())
        permission = mev_boost_relay_allowed_list.address + mev_boost_relay_allowed_list.remove_relay.signature[2:]

        easy_track.addEVMScriptFactory(
            evm_script_factory,
            permission,
            {"from": lido_contracts.aragon.voting},
        )
        evm_script_factories = easy_track.getEVMScriptFactories()

        # Check that the factory is added to the EasyTrack
        assert len(evm_script_factories) == num_factories_before + 1
        assert evm_script_factory in evm_script_factories

        log.ok(f"EVM Script Factory RemoveMEVBoostRelays({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


@pytest.fixture(scope="module")
def edit_mev_boost_relays_evm_script_factory(
    EditMEVBoostRelays,
    rmc_factories_multisig,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
):
    evm_script_factory = (
        EditMEVBoostRelays.at(deployed_artifact["EditMEVBoostRelays"]["address"])
        if "EditMEVBoostRelays" in deployed_artifact
        else None
    )

    if evm_script_factory is None:
        evm_script_factory = deployer.deploy(EditMEVBoostRelays, rmc_factories_multisig, mev_boost_relay_allowed_list)

    assert evm_script_factory.trustedCaller() == rmc_factories_multisig
    assert evm_script_factory.mevBoostRelayAllowedList() == mev_boost_relay_allowed_list

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        num_factories_before = len(easy_track.getEVMScriptFactories())
        permission = (
            mev_boost_relay_allowed_list.address
            + mev_boost_relay_allowed_list.add_relay.signature[2:]
            + mev_boost_relay_allowed_list.address[2:]
            + mev_boost_relay_allowed_list.remove_relay.signature[2:]
        )
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            permission,
            {"from": lido_contracts.aragon.voting},
        )

        evm_script_factories = easy_track.getEVMScriptFactories()
        # Check that the factory is added to the EasyTrack
        assert len(evm_script_factories) == num_factories_before + 1
        assert evm_script_factory in evm_script_factories

        log.ok(f"EVM Script Factory EditMEVBoostRelays({evm_script_factory}) was added to EasyTrack")

    return evm_script_factory


####
# ALLOWED RECIPIENTS FIXTURES
####


@pytest.fixture(scope="module")
def create_add_allowed_recipient_motion(easy_track):
    def _create_add_allowed_recipient_motion(
        add_allowed_recipient_evm_script_factory, recipient_address, recipient_title
    ):
        return easy_track.createMotion(
            add_allowed_recipient_evm_script_factory,
            evm_script.encode_calldata(["address", "string"], [recipient_address, recipient_title]),
            {"from": add_allowed_recipient_evm_script_factory.trustedCaller()},
        )

    return _create_add_allowed_recipient_motion


@pytest.fixture(scope="module")
def create_top_up_allowed_recipients_motion(easy_track):
    def _create_top_up_allowed_recipients_motion(
        top_up_allowed_recipients_evm_script_factory,
        recipient_addresses,
        top_up_amounts,
    ):
        return easy_track.createMotion(
            top_up_allowed_recipients_evm_script_factory,
            evm_script.encode_calldata(["address[]", "uint256[]"], [recipient_addresses, top_up_amounts]),
            {"from": top_up_allowed_recipients_evm_script_factory.trustedCaller()},
        )

    return _create_top_up_allowed_recipients_motion


@pytest.fixture(scope="module")
def top_up_allowed_recipient_by_motion(
    easy_track,
    create_top_up_allowed_recipients_motion,
    enact_top_up_allowed_recipient_motion_by_creation_tx,
):
    def _top_up_allowed_recipient_by_motion(
        top_up_allowed_recipients_evm_script_factory, recipient_addresses, top_up_amounts, spent_amount=0
    ):
        motion_creation_tx = create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            recipient_addresses,
            top_up_amounts,
        )

        enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx, spent_amount)

    return _top_up_allowed_recipient_by_motion


@pytest.fixture(scope="module")
def get_balances(interface, accounts):
    def _get_balances(token, recipients):
        if token == brownie.ZERO_ADDRESS:
            return [accounts.at(r).balance() for r in recipients]
        return [interface.ERC20(token).balanceOf(r) for r in recipients]

    return _get_balances


@pytest.fixture(scope="module")
def enact_top_up_allowed_recipient_motion_by_creation_tx(
    TopUpAllowedRecipients,
    interface,
    easy_track,
    get_balances,
    lido_contracts,
    enact_motion_by_creation_tx,
    check_top_up_motion_enactment,
):
    def _enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx, spent_amount=0):
        top_up_allowed_recipients_evm_script_factory = TopUpAllowedRecipients.at(
            motion_creation_tx.events["MotionCreated"]["_evmScriptFactory"]
        )

        (
            recipients,
            amounts,
        ) = top_up_allowed_recipients_evm_script_factory.decodeEVMScriptCallData(
            motion_creation_tx.events["MotionCreated"]["_evmScriptCallData"]
        )

        top_up_token = top_up_allowed_recipients_evm_script_factory.token()

        (sender_balance_before,) = get_balances(top_up_token, [lido_contracts.aragon.agent])
        recipients_balances_before = get_balances(top_up_token, recipients)
        sender_shares_balance_before = 0
        recipients_shares_balance_before = 0
        if top_up_token == lido_contracts.steth:
            sender_shares_balance_before = lido_contracts.steth.sharesOf(lido_contracts.aragon.agent)
            for r in recipients:
                recipients_shares_balance_before += lido_contracts.steth.sharesOf(r)

        motion_data = easy_track.getMotion(motion_creation_tx.events["MotionCreated"]["_motionId"]).dict()

        # If motion not finished wait end of it
        if motion_data["startDate"] + motion_data["duration"] > brownie.chain[-1]["timestamp"]:
            brownie.chain.sleep(easy_track.motionDuration() + 100)

        motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

        check_top_up_motion_enactment(
            top_up_allowed_recipients_evm_script_factory=top_up_allowed_recipients_evm_script_factory,
            top_up_motion_enactment_tx=motion_enactment_tx,
            sender_balance_before=sender_balance_before,
            recipients_balances_before=recipients_balances_before,
            sender_shares_balance_before=sender_shares_balance_before,
            recipients_shares_balance_before=recipients_shares_balance_before,
            top_up_recipients=recipients,
            top_up_amounts=amounts,
            spent_amount=spent_amount,
        )

    return _enact_top_up_allowed_recipient_motion_by_creation_tx


@pytest.fixture(scope="module")
def check_top_up_motion_enactment(AllowedRecipientsRegistry, get_balances, lido_contracts):
    """Note: this check works correctly only when was payment in the period"""

    def _check_top_up_motion_enactment(
        top_up_allowed_recipients_evm_script_factory,
        top_up_motion_enactment_tx,
        sender_balance_before,
        recipients_balances_before,
        sender_shares_balance_before,
        recipients_shares_balance_before,
        top_up_recipients,
        top_up_amounts,
        spent_amount,
    ):
        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            top_up_allowed_recipients_evm_script_factory.allowedRecipientsRegistry()
        )
        limit, duration = allowed_recipients_registry.getLimitParameters()

        spending = sum(top_up_amounts)
        spendable = limit - (spending + spent_amount)

        assert allowed_recipients_registry.isUnderSpendableBalance(spendable, 0)
        assert allowed_recipients_registry.isUnderSpendableBalance(limit, duration * MAX_SECONDS_IN_MONTH)
        assert allowed_recipients_registry.getPeriodState()["_alreadySpentAmount"] == spending + spent_amount
        assert allowed_recipients_registry.getPeriodState()["_spendableBalanceInPeriod"] == spendable

        top_up_token = top_up_allowed_recipients_evm_script_factory.token()
        (sender_balance,) = get_balances(top_up_token, [lido_contracts.aragon.agent])
        recipients_balances = get_balances(
            top_up_token,
            top_up_recipients,
        )

        if top_up_token == lido_contracts.steth:
            assert math.isclose(sender_balance, sender_balance_before - spending, abs_tol=STETH_ERROR_MARGIN_WEI)

            sender_shares_balance_after = lido_contracts.steth.sharesOf(lido_contracts.aragon.agent)
            recipients_shares_balance_after = 0
            for r in top_up_recipients:
                recipients_shares_balance_after += lido_contracts.steth.sharesOf(r)
            assert sender_shares_balance_before >= sender_shares_balance_after
            assert (
                sender_shares_balance_before - sender_shares_balance_after
                == recipients_shares_balance_after - recipients_shares_balance_before
            )
        else:
            assert sender_balance == sender_balance_before - spending

        for before, now, payment in zip(recipients_balances_before, recipients_balances, top_up_amounts):
            if top_up_token == lido_contracts.steth:
                assert math.isclose(now, before + payment, abs_tol=STETH_ERROR_MARGIN_WEI)
            else:
                assert now == before + payment

        assert "SpendableAmountChanged" in top_up_motion_enactment_tx.events
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"]["_alreadySpentAmount"]
            == spending + spent_amount
        )
        assert top_up_motion_enactment_tx.events["SpendableAmountChanged"]["_spendableBalance"] == spendable

    return _check_top_up_motion_enactment


@pytest.fixture(scope="module")
def allowed_recipients_factory(AllowedRecipientsFactory, load_deployed_contract, deployer):

    loaded_allowed_recipients_factory = load_deployed_contract("AllowedRecipientsFactory")

    if not loaded_allowed_recipients_factory is None:
        return loaded_allowed_recipients_factory

    return AllowedRecipientsFactory.deploy({"from": deployer})


@pytest.fixture(scope="module")
def allowed_recipients_builder(
    AllowedRecipientsBuilder,
    lido_contracts,
    load_deployed_contract,
    allowed_recipients_factory,
    bokky_poo_bahs_date_time_contract,
    easy_track,
    deployer,
):

    loaded_allowed_recipients_builder = load_deployed_contract("AllowedRecipientsBuilder")

    if not loaded_allowed_recipients_builder is None:
        return loaded_allowed_recipients_builder

    return AllowedRecipientsBuilder.deploy(
        allowed_recipients_factory,
        lido_contracts.aragon.agent,
        easy_track,
        lido_contracts.aragon.finance,
        bokky_poo_bahs_date_time_contract,
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def allowed_recipients_default_params():
    @dataclass
    class AllowedRecipientsDefaultParams:
        limit: int
        period_duration_months: int
        spent_amount: int

    return AllowedRecipientsDefaultParams(limit=100 * 10**18, period_duration_months=1, spent_amount=0)


@pytest.fixture(scope="module")
def allowed_recipients_registry(
    AllowedRecipientsRegistry,
    allowed_recipients_default_params,
    allowed_recipients_builder,
    load_deployed_contract,
    lido_contracts,
    easy_track,
    deployer,
):
    allowed_recipients_registry = load_deployed_contract("AllowedRecipientsRegistry")

    if allowed_recipients_registry is None:
        tx = allowed_recipients_builder.deployAllowedRecipientsRegistry(
            allowed_recipients_default_params.limit,
            allowed_recipients_default_params.period_duration_months,
            [],
            [],
            allowed_recipients_default_params.spent_amount,
            True,
            {"from": deployer},
        )

        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
        )

    if not allowed_recipients_registry.hasRole(
        allowed_recipients_registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE(),
        easy_track.evmScriptExecutor(),
    ):
        allowed_recipients_registry.grantRole(
            allowed_recipients_registry.ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE(),
            easy_track.evmScriptExecutor(),
            {"from": lido_contracts.aragon.agent},
        )

    if not allowed_recipients_registry.hasRole(
        allowed_recipients_registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE(),
        easy_track.evmScriptExecutor(),
    ):
        allowed_recipients_registry.grantRole(
            allowed_recipients_registry.REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE(),
            easy_track.evmScriptExecutor(),
            {"from": lido_contracts.aragon.agent},
        )

    return allowed_recipients_registry


@pytest.fixture(scope="module")
def allowed_recipients_limit_params(allowed_recipients_registry):
    @dataclass
    class AllowedRecipientsLimits:
        limit: int
        duration: int

    limit, duration = allowed_recipients_registry.getLimitParameters()
    return AllowedRecipientsLimits(limit, duration)


@pytest.fixture(scope="module")
def bokky_poo_bahs_date_time_contract():
    return deployed_date_time.date_time_contract(network=brownie.network.show_active())
