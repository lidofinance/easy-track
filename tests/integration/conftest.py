import pytest
import brownie

import constants
from utils import lido, deployment, deployed_date_time, evm_script
from collections import namedtuple
from dataclasses import dataclass

#####
# CONSTANTS
#####

MAX_SECONDS_IN_MONTH = 31 * 24 * 60 * 60

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

        if (
            contract_name in deployed_contracts
            and deployed_contracts[contract_name] != ""
        ):
            loaded_contract = Contract.at(deployed_contracts[contract_name])
            print(f"Loaded contract: {contract_name}('{loaded_contract.address}')")
            return loaded_contract

    return _load_deployed_contract


@pytest.fixture(scope="module")
def lido_contracts():
    return lido.contracts(network=brownie.network.show_active())


@pytest.fixture(scope="module")
def easy_track(
    EasyTrack,
    EVMScriptExecutor,
    lido_contracts,
    deployer,
    load_deployed_contract,
):

    loaded_easy_track = load_deployed_contract("EasyTrack")

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

    deployed_easy_track.setEVMScriptExecutor(
        evm_script_executor, {"from": lido_contracts.aragon.voting}
    )
    evm_script_executor.transferOwnership(
        lido_contracts.aragon.voting, {"from": deployer}
    )

    assert evm_script_executor.owner() == lido_contracts.aragon.voting

    create_payments_permission = lido.permissions(
        contracts=lido_contracts
    ).finance.CREATE_PAYMENTS_ROLE

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
        evm_script_factory = AddAllowedRecipient.at(
            tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
        )

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            deployment.create_permission(allowed_recipients_registry, "addRecipient"),
            {"from": lido_contracts.aragon.voting},
        )
        print(
            f"EVM Script Factory AddAllowedRecipient({evm_script_factory}) was added to EasyTrack"
        )

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
            deployment.create_permission(
                allowed_recipients_registry, "removeRecipient"
            ),
            {"from": lido_contracts.aragon.voting},
        )
        print(
            f"EVM Script Factory RemoveAllowedRecipient({evm_script_factory}) was added to EasyTrack"
        )

    return evm_script_factory


@pytest.fixture(scope="module")
def add_allowed_recipient_by_motion(AllowedRecipientsRegistry, easy_track, stranger):
    def _add_allowed_recipient_via_motion(
        add_allowed_recipient_evm_script_factory, recipient_address, recipient_title
    ):
        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            add_allowed_recipient_evm_script_factory.allowedRecipientsRegistry()
        )

        tx = easy_track.createMotion(
            add_allowed_recipient_evm_script_factory,
            evm_script.encode_calldata(
                "(address,string)", [recipient_address, recipient_title]
            ),
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
    def _remove_recipient_by_motion(
        remove_allowed_recipient_evm_script_factory, recipient_address
    ):

        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            remove_allowed_recipient_evm_script_factory.allowedRecipientsRegistry()
        )
        call_data = evm_script.encode_calldata("(address)", [recipient_address])

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
    ldo,
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
            trusted_caller, allowed_recipients_registry, ldo, {"from": deployer}
        )

        evm_script_factory = TopUpAllowedRecipients.at(
            tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
        )

    if not easy_track.isEVMScriptFactory(evm_script_factory):
        easy_track.addEVMScriptFactory(
            evm_script_factory,
            deployment.create_permission(
                lido_contracts.aragon.finance, "newImmediatePayment"
            )
            + deployment.create_permission(
                allowed_recipients_registry, "updateSpentAmount"
            )[2:],
            {"from": lido_contracts.aragon.voting},
        )
        print(
            f"EVM Script Factory TopUpAllowedRecipient({evm_script_factory}) was added to EasyTrack"
        )

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
            evm_script.encode_calldata(
                "(address,string)", [recipient_address, recipient_title]
            ),
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
            evm_script.encode_calldata(
                "(address[],uint256[])", [recipient_addresses, top_up_amounts]
            ),
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
        top_up_allowed_recipients_evm_script_factory,
        recipient_addresses,
        top_up_amounts,
    ):
        motion_creation_tx = create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            recipient_addresses,
            top_up_amounts,
        )

        enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx)

    return _top_up_allowed_recipient_by_motion


@pytest.fixture(scope="module")
def get_balances(interface):
    def _get_balances(token, recipients):
        return [interface.ERC20(token).balanceOf(r) for r in recipients]

    return _get_balances


@pytest.fixture(scope="module")
def enact_top_up_allowed_recipient_motion_by_creation_tx(
    TopUpAllowedRecipients,
    interface,
    easy_track,
    get_balances,
    enact_motion_by_creation_tx,
    check_top_up_motion_enactment,
):
    def _enact_top_up_allowed_recipient_motion_by_creation_tx(motion_creation_tx):
        top_up_allowed_recipients_evm_script_factory = TopUpAllowedRecipients.at(
            motion_creation_tx.events["MotionCreated"]["_evmScriptFactory"]
        )

        (
            recipients,
            amounts,
        ) = top_up_allowed_recipients_evm_script_factory.decodeEVMScriptCallData(
            motion_creation_tx.events["MotionCreated"]["_evmScriptCallData"]
        )

        balances_before = get_balances(
            top_up_allowed_recipients_evm_script_factory.token(), recipients
        )

        motion_data = easy_track.getMotion(
            motion_creation_tx.events["MotionCreated"]["_motionId"]
        ).dict()

        # If motion not finished wait end of it
        if (
            motion_data["startDate"] + motion_data["duration"]
            > brownie.chain[-1]["timestamp"]
        ):
            brownie.chain.sleep(easy_track.motionDuration() + 100)

        motion_enactment_tx = enact_motion_by_creation_tx(motion_creation_tx)

        check_top_up_motion_enactment(
            top_up_allowed_recipients_evm_script_factory,
            motion_enactment_tx,
            balances_before,
            recipients,
            amounts,
        )

    return _enact_top_up_allowed_recipient_motion_by_creation_tx


@pytest.fixture(scope="module")
def check_top_up_motion_enactment(
    AllowedRecipientsRegistry,
    get_balances,
):
    """Note: this check works correctly only when was payment in the period"""

    def _check_top_up_motion_enactment(
        top_up_allowed_recipients_evm_script_factory,
        top_up_motion_enactment_tx,
        balances_before,
        top_up_recipients,
        top_up_amounts,
    ):
        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            top_up_allowed_recipients_evm_script_factory.allowedRecipientsRegistry()
        )
        limit, duration = allowed_recipients_registry.getLimitParameters()

        spending = sum(top_up_amounts)
        spendable = limit - spending

        assert allowed_recipients_registry.isUnderSpendableBalance(spendable, 0)
        assert allowed_recipients_registry.isUnderSpendableBalance(
            limit, duration * MAX_SECONDS_IN_MONTH
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_alreadySpentAmount"]
            == spending
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_spendableBalanceInPeriod"]
            == spendable
        )

        balances = get_balances(
            top_up_allowed_recipients_evm_script_factory.token(),
            top_up_recipients,
        )
        for before, now, payment in zip(balances_before, balances, top_up_amounts):
            assert now == before + payment

        assert "SpendableAmountChanged" in top_up_motion_enactment_tx.events
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"][
                "_alreadySpentAmount"
            ]
            == spending
        )
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"][
                "_spendableBalance"
            ]
            == spendable
        )

    return _check_top_up_motion_enactment


@pytest.fixture(scope="module")
def allowed_recipients_factory(
    AllowedRecipientsFactory, load_deployed_contract, deployer
):

    loaded_allowed_recipients_factory = load_deployed_contract(
        "AllowedRecipientsFactory"
    )

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

    loaded_allowed_recipients_builder = load_deployed_contract(
        "AllowedRecipientsBuilder"
    )

    if not loaded_allowed_recipients_builder is None:
        return loaded_allowed_recipients_builder

    return AllowedRecipientsBuilder.deploy(
        allowed_recipients_factory,
        easy_track.evmScriptExecutor(),
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

    return AllowedRecipientsDefaultParams(
        limit=100 * 10 ** 18, period_duration_months=1, spent_amount=0
    )


@pytest.fixture(scope="module")
def allowed_recipients_registry(
    AllowedRecipientsRegistry,
    allowed_recipients_default_params,
    allowed_recipients_builder,
    load_deployed_contract,
    deployer,
):
    loaded_allowed_recipients_registry = load_deployed_contract(
        "AllowedRecipientsRegistry"
    )

    if not loaded_allowed_recipients_registry is None:
        return loaded_allowed_recipients_registry

    tx = allowed_recipients_builder.deployAllowedRecipientsRegistry(
        allowed_recipients_default_params.limit,
        allowed_recipients_default_params.period_duration_months,
        [],
        [],
        allowed_recipients_default_params.spent_amount,
        False,
        {"from": deployer},
    )

    return AllowedRecipientsRegistry.at(
        tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    )


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
