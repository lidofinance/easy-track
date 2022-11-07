import pytest
import brownie

import constants
from utils import lido
from utils import deployment
from collections import namedtuple
from dataclasses import dataclass

EasyTrackDefaults = namedtuple(
    "EasyTrackDefaults",
    ["min_motion_duration", "max_motions_limit", "default_objections_threshold"],
)

#####
# CONSTANTS
#####


@pytest.fixture(scope="module")
def easy_track_defaults():
    return EasyTrackDefaults(
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )


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


#####
# CONTRACTS
#####


@pytest.fixture(scope="module")
def deployed_contracts():
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
    return lido.contracts()


@pytest.fixture(scope="module")
def easy_track(
    EasyTrack,
    EVMScriptExecutor,
    easy_track_defaults,
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
        easy_track_defaults.min_motion_duration,
        easy_track_defaults.max_motions_limit,
        easy_track_defaults.default_objections_threshold,
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

    loaded_add_allowed_recipient_evm_script_factory = load_deployed_contract(
        "AddAllowedRecipient"
    )

    if not loaded_add_allowed_recipient_evm_script_factory is None:
        return loaded_add_allowed_recipient_evm_script_factory

    tx = allowed_recipients_builder.deployAddAllowedRecipient(
        trusted_caller, allowed_recipients_registry, {"from": deployer}
    )

    factory = AddAllowedRecipient.at(
        tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    )

    easy_track.addEVMScriptFactory(
        factory,
        deployment.create_permission(allowed_recipients_registry, "addRecipient"),
        {"from": lido_contracts.aragon.voting},
    )
    return factory


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
    loaded_remove_allowed_recipient_evm_script_factory = load_deployed_contract(
        "RemoveAllowedRecipient"
    )

    if not loaded_remove_allowed_recipient_evm_script_factory is None:
        return loaded_remove_allowed_recipient_evm_script_factory

    tx = allowed_recipients_builder.deployRemoveAllowedRecipient(
        trusted_caller, allowed_recipients_registry, {"from": deployer}
    )

    evm_script_factory = RemoveAllowedRecipient.at(
        tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]
    )

    easy_track.addEVMScriptFactory(
        evm_script_factory,
        deployment.create_permission(allowed_recipients_registry, "removeRecipient"),
        {"from": lido_contracts.aragon.voting},
    )
    return evm_script_factory


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

    loaded_top_up_allowed_recipients_evm_script_factory = load_deployed_contract(
        "TopUpAllowedRecipients"
    )

    if not loaded_top_up_allowed_recipients_evm_script_factory is None:
        return loaded_top_up_allowed_recipients_evm_script_factory

    tx = allowed_recipients_builder.deployTopUpAllowedRecipients(
        trusted_caller, allowed_recipients_registry, ldo, {"from": deployer}
    )

    evm_script_factory = TopUpAllowedRecipients.at(
        tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    )

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

    return evm_script_factory


####
# ALLOWED RECIPIENTS FIXTURES
####


@pytest.fixture(scope="module")
def allowed_recipients_factory(
    AllowedRecipientsFactory,
    lido_contracts,
    easy_track,
    bokky_poo_bahs_date_time_contract,
    load_deployed_contract,
    deployer,
):

    loaded_allowed_recipients_factory = load_deployed_contract(
        "AllowedRecipientsFactory"
    )

    if not loaded_allowed_recipients_factory is None:
        return loaded_allowed_recipients_factory

    return AllowedRecipientsFactory.deploy(
        easy_track,
        lido_contracts.aragon.finance,
        easy_track.evmScriptExecutor(),
        lido_contracts.aragon.agent,
        bokky_poo_bahs_date_time_contract,
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def allowed_recipients_builder(
    AllowedRecipientsBuilder,
    lido_contracts,
    load_deployed_contract,
    allowed_recipients_factory,
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
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def allowed_recipients_default_params():
    @dataclass
    class AllowedRecipientsDefaultParams:
        limit: int
        period_duration_month: int
        spent_amount: int

    return AllowedRecipientsDefaultParams(
        limit=100 * 10 ** 18, period_duration_month=1, spent_amount=0
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
        allowed_recipients_default_params.period_duration_month,
        [],
        [],
        allowed_recipients_default_params.spent_amount,
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
    return "0x23d23d8f243e57d0b924bff3a3191078af325101"
