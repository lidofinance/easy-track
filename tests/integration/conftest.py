import pytest
import brownie
import constants
from utils import log
from utils.config import get_network_name, set_balance_in_wei
from utils.deployed_addresses import load_addresses, load_deployed_artifact, try_load_deployed_contract
from utils.test_helpers import set_account_balance


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
    """
    Merges contract addresses from two sources:
    - integration-test-addresses-{network}.json (structured payout data, easytrack)
    - deployed-{network}.json (flat factory addresses, takes priority)
    """
    data = load_addresses()
    artifact = load_deployed_artifact()

    contracts = {
        "EasyTrack": data.get("easytrack", ""),
    }

    # deployed-{network}.json has priority for flat factory addresses
    contracts.update(artifact)

    # "local" entries from integration JSON always win
    for key, value in data.items():
        if value == "local":
            contracts[key] = "local"

    return contracts


@pytest.fixture(scope="module")
def load_deployed_contract(request):
    deployed_contracts = request.getfixturevalue('deployed_contracts')
    def _load_deployed_contract(contract_name):
        return try_load_deployed_contract(contract_name, deployed_contracts)

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
def rmc_factories_multisig():
    network_name = get_network_name()
    if network_name == "mainnet" or network_name == "mainnet-fork":
        address = "0x98be4a407Bff0c125e25fBE9Eb1165504349c37d"
    else:
        address = "0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A"  # QA multisig
    set_balance_in_wei(address, 10**18)
    return address


@pytest.fixture(scope="module")
def sdvt_trusted_caller():
    """
    Test multisig address for SDVT submit validator exit hashes factory.
    """
    network_name = get_network_name()
    if network_name in ("mainnet", "mainnet-fork"):
        return "0x08637515E85A4633E23dfc7861e2A9f53af640f7"
    else:
        account = brownie.accounts.at("0x418B816A7c3ecA151A31d98e30aa7DAa33aBf83A", force=True)
        set_account_balance(account.address)
        return account.address


@pytest.fixture(scope="module")
def sdvt_submit_exit_hashes_evm_script_factory(
    SDVTSubmitExitRequestHashes,
    sdvt_trusted_caller,
    easy_track,
    lido_contracts,
    sdvt_registry,
    validators_exit_bus_oracle,
    deployer,
    staking_router,
    load_deployed_contract,
):
    """
    Load deployed or deploy fresh SDVTSubmitExitRequestHashes factory.
    """
    factory = load_deployed_contract("SDVTSubmitExitRequestHashes")

    if factory is None:
        factory = deployer.deploy(
            SDVTSubmitExitRequestHashes,
            sdvt_trusted_caller,
            sdvt_registry,
            staking_router,
            validators_exit_bus_oracle,
        )

    assert factory.trustedCaller() == sdvt_trusted_caller
    assert factory.nodeOperatorsRegistry() == sdvt_registry

    if not easy_track.isEVMScriptFactory(factory):
        permission = (
            validators_exit_bus_oracle.address + validators_exit_bus_oracle.submitExitRequestsHash.signature[2:]
        )
        easy_track.addEVMScriptFactory(
            factory,
            permission,
            {"from": lido_contracts.aragon.voting},
        )
        assert factory in easy_track.getEVMScriptFactories()

    set_account_balance(factory.trustedCaller())
    return factory


@pytest.fixture(scope="module")
def curated_submit_exit_hashes_evm_script_factory(
    CuratedSubmitExitRequestHashes,
    easy_track,
    lido_contracts,
    curated_registry,
    validators_exit_bus_oracle,
    deployer,
    staking_router,
    load_deployed_contract,
):
    """
    Load deployed or deploy fresh CuratedSubmitExitRequestHashes factory.
    """
    factory = load_deployed_contract("CuratedSubmitExitRequestHashes")

    if factory is None:
        factory = deployer.deploy(
            CuratedSubmitExitRequestHashes,
            curated_registry,
            staking_router,
            validators_exit_bus_oracle,
        )

    assert factory.nodeOperatorsRegistry() == curated_registry

    if not easy_track.isEVMScriptFactory(factory):
        permission = (
            validators_exit_bus_oracle.address + validators_exit_bus_oracle.submitExitRequestsHash.signature[2:]
        )
        easy_track.addEVMScriptFactory(
            factory,
            permission,
            {"from": lido_contracts.aragon.voting},
        )
        assert factory in easy_track.getEVMScriptFactories()

    return factory


@pytest.fixture(scope="module")
def add_mev_boost_relays_evm_script_factory(
    AddMEVBoostRelays,
    rmc_factories_multisig,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
    load_deployed_contract,
):
    evm_script_factory = load_deployed_contract("AddMEVBoostRelays")

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

        assert len(evm_script_factories) == num_factories_before + 1
        assert evm_script_factory in evm_script_factories

        log.ok(f"EVM Script Factory AddMEVBoostRelays({evm_script_factory}) was added to EasyTrack")

    set_account_balance(evm_script_factory.trustedCaller())
    return evm_script_factory


@pytest.fixture(scope="module")
def remove_mev_boost_relays_evm_script_factory(
    RemoveMEVBoostRelays,
    rmc_factories_multisig,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
    load_deployed_contract,
):
    evm_script_factory = load_deployed_contract("RemoveMEVBoostRelays")

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

        assert len(evm_script_factories) == num_factories_before + 1
        assert evm_script_factory in evm_script_factories

        log.ok(f"EVM Script Factory RemoveMEVBoostRelays({evm_script_factory}) was added to EasyTrack")

    set_account_balance(evm_script_factory.trustedCaller())
    return evm_script_factory


@pytest.fixture(scope="module")
def edit_mev_boost_relays_evm_script_factory(
    EditMEVBoostRelays,
    rmc_factories_multisig,
    easy_track,
    lido_contracts,
    mev_boost_relay_allowed_list,
    deployer,
    load_deployed_contract,
):
    evm_script_factory = load_deployed_contract("EditMEVBoostRelays")

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

    set_account_balance(evm_script_factory.trustedCaller())
    return evm_script_factory
