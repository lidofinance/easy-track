import pytest
import brownie

import constants
import math
from utils import lido, deployment, deployed_date_time, evm_script, log
from collections import namedtuple
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
        "AllowedTokensRegistry": "",
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
            log.ok(f"Loaded contract: {contract_name}('{loaded_contract.address}')")
            return loaded_contract

    return _load_deployed_contract


@pytest.fixture(scope="module")
def lido_contracts():
    return lido.contracts(network=brownie.network.show_active())

@pytest.fixture(scope="module")
def external_contracts():
    return lido.external_contracts(network=brownie.network.show_active())

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

    deployed_easy_track.setEVMScriptExecutor(
        evm_script_executor, {"from": lido_contracts.aragon.voting}
    )
    evm_script_executor.transferOwnership(
        lido_contracts.aragon.voting, {"from": deployer}
    )

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
    registries,
    deployer,
):

    (allowed_recipients_registry, _) = registries
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
        log.ok(
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
    registries,
    deployer,
    trusted_caller,
):
    evm_script_factory = load_deployed_contract("RemoveAllowedRecipient")
    (allowed_recipients_registry, _) = registries

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
        log.ok(
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
    easy_track,
    lido_contracts,
    load_deployed_contract,
    allowed_recipients_builder,
    registries,
    trusted_caller,
    deployer,
):
    (allowed_recipients_registry, allowed_tokens_registry) = registries
    evm_script_factory = load_deployed_contract("TopUpAllowedRecipients")

    if evm_script_factory is None:
        tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
            trusted_caller,
            allowed_recipients_registry,
            allowed_tokens_registry,
            {"from": deployer},
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
        log.ok(
            f"EVM Script Factory TopUpAllowedRecipients({evm_script_factory}) was added to EasyTrack"
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
        token,
        recipient_addresses,
        top_up_amounts,
    ):
        return easy_track.createMotion(
            top_up_allowed_recipients_evm_script_factory,
            evm_script.encode_calldata(
                "(address,address[],uint256[])", [token, recipient_addresses, top_up_amounts]
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
        token_address,
        recipient_addresses,
        top_up_amounts,
        spent_amount=0
    ):
        motion_creation_tx = create_top_up_allowed_recipients_motion(
            top_up_allowed_recipients_evm_script_factory,
            token_address,
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
            top_up_token,
            recipients,
            amounts,
        ) = top_up_allowed_recipients_evm_script_factory.decodeEVMScriptCallData(
            motion_creation_tx.events["MotionCreated"]["_evmScriptCallData"]
        )

        (sender_balance_before,) = get_balances(
            top_up_token, [lido_contracts.aragon.agent]
        )
        recipients_balances_before = get_balances(top_up_token, recipients)
        sender_shares_balance_before = 0
        recipients_shares_balance_before = 0
        if top_up_token == lido_contracts.steth:
            sender_shares_balance_before = lido_contracts.steth.sharesOf(lido_contracts.aragon.agent)
            for r in recipients:
                recipients_shares_balance_before += lido_contracts.steth.sharesOf(r)

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
            top_up_allowed_recipients_evm_script_factory=top_up_allowed_recipients_evm_script_factory,
            top_up_motion_enactment_tx=motion_enactment_tx,
            sender_balance_before=sender_balance_before,
            recipients_balances_before=recipients_balances_before,
            sender_shares_balance_before=sender_shares_balance_before,
            recipients_shares_balance_before=recipients_shares_balance_before,
            top_up_token=top_up_token,
            top_up_recipients=recipients,
            top_up_amounts=amounts,
            spent_amount=spent_amount
        )

    return _enact_top_up_allowed_recipient_motion_by_creation_tx


@pytest.fixture(scope="module")
def check_top_up_motion_enactment(
    AllowedRecipientsRegistry, get_balances, lido_contracts, interface
):
    """Note: this check works correctly only when was payment in the period"""

    def normalize_amount(token_amount, token):
        DECIMALS = 18

        if token_amount == 0:
            return 0

        token_decimals = interface.ERC20(token).decimals()

        if token_decimals == DECIMALS:
            return token_amount
        if token_decimals > DECIMALS:
            return (token_amount - 1) // (10 ** (token_decimals - DECIMALS)) + 1
        return token_amount * (10 ** (DECIMALS - token_decimals))


    def _check_top_up_motion_enactment(
        top_up_allowed_recipients_evm_script_factory,
        top_up_motion_enactment_tx,
        sender_balance_before,
        recipients_balances_before,
        sender_shares_balance_before,
        recipients_shares_balance_before,
        top_up_token,
        top_up_recipients,
        top_up_amounts,
        spent_amount,
    ):
        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            top_up_allowed_recipients_evm_script_factory.allowedRecipientsRegistry()
        )
        limit, duration = allowed_recipients_registry.getLimitParameters()

        spending_in_tokens = sum(top_up_amounts)
        spending = normalize_amount(
            spending_in_tokens, top_up_token
        )
        spendable = limit - (spending + spent_amount)

        assert allowed_recipients_registry.isUnderSpendableBalance(spendable, 0)
        assert allowed_recipients_registry.isUnderSpendableBalance(
            limit, duration * MAX_SECONDS_IN_MONTH
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_alreadySpentAmount"]
            == spending + spent_amount
        )
        assert (
            allowed_recipients_registry.getPeriodState()["_spendableBalanceInPeriod"]
            == spendable
        )

        (sender_balance,) = get_balances(top_up_token, [lido_contracts.aragon.agent])
        recipients_balances = get_balances(
            top_up_token,
            top_up_recipients,
        )

        if top_up_token == lido_contracts.steth:
            assert math.isclose(sender_balance, sender_balance_before - spending_in_tokens, abs_tol = STETH_ERROR_MARGIN_WEI)

            sender_shares_balance_after = lido_contracts.steth.sharesOf(lido_contracts.aragon.agent)
            recipients_shares_balance_after = 0
            for r in top_up_recipients:
                recipients_shares_balance_after += lido_contracts.steth.sharesOf(r)
            assert sender_shares_balance_before >= sender_shares_balance_after
            assert sender_shares_balance_before - sender_shares_balance_after  == recipients_shares_balance_after - recipients_shares_balance_before
        else:
            assert sender_balance == sender_balance_before - spending_in_tokens

        for before, now, payment in zip(
            recipients_balances_before, recipients_balances, top_up_amounts
        ):
            if top_up_token == lido_contracts.steth:
                assert math.isclose(now, before + payment, abs_tol = STETH_ERROR_MARGIN_WEI)
            else:
                assert now == before + payment

        assert "SpendableAmountChanged" in top_up_motion_enactment_tx.events
        assert (
            top_up_motion_enactment_tx.events["SpendableAmountChanged"][
                "_alreadySpentAmount"
            ]
            == spending + spent_amount
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
def registries(
    AllowedRecipientsRegistry,
    AllowedTokensRegistry,
    allowed_recipients_default_params,
    allowed_recipients_builder,
    load_deployed_contract,
    lido_contracts,
    easy_track,
    deployer,
):
    allowed_recipients_registry = load_deployed_contract("AllowedRecipientsRegistry")
    allowed_tokens_registry = load_deployed_contract("AllowedTokensRegistry")

    if allowed_recipients_registry is None:
        tx_recipients = allowed_recipients_builder.deployAllowedRecipientsRegistry(
            allowed_recipients_default_params.limit,
            allowed_recipients_default_params.period_duration_months,
            [],
            [],
            allowed_recipients_default_params.spent_amount,
            True,
            {"from": deployer},
        )

        tx_tokens = allowed_recipients_builder.deployAllowedTokensRegistry([])

        allowed_recipients_registry = AllowedRecipientsRegistry.at(
            tx_recipients.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
        )
        allowed_tokens_registry = AllowedTokensRegistry.at(
            tx_tokens.events["AllowedTokensRegistryDeployed"]["allowedTokensRegistry"]
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

    return (allowed_recipients_registry, allowed_tokens_registry)

@pytest.fixture(scope="module")
def add_allowed_token(registries, lido_contracts):
    (_, allowed_tokens_registry) = registries
    def _add_allowed_token(token):
        if (allowed_tokens_registry.isTokenAllowed(token)):
            return
        allowed_tokens_registry.addToken(token, {"from": lido_contracts.aragon.agent})
        assert allowed_tokens_registry.isTokenAllowed(token)
    return _add_allowed_token

@pytest.fixture(scope="module")
def remove_allowed_token(registries, lido_contracts):
    (_, allowed_tokens_registry) = registries
    def _remove_allowed_token(token):
        if not allowed_tokens_registry.isTokenAllowed(token):
            return
        allowed_tokens_registry.removeToken(token, {"from": lido_contracts.aragon.agent})
        assert not allowed_tokens_registry.isTokenAllowed(token)
    return _remove_allowed_token


@pytest.fixture(scope="module")
def allowed_recipients_limit_params(registries):
    @dataclass
    class AllowedRecipientsLimits:
        limit: int
        duration: int

    (allowed_recipients_registry, _) = registries

    limit, duration = allowed_recipients_registry.getLimitParameters()
    return AllowedRecipientsLimits(limit, duration)


@pytest.fixture(scope="module")
def bokky_poo_bahs_date_time_contract():
    return deployed_date_time.date_time_contract(network=brownie.network.show_active())
