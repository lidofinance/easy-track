import pytest
import brownie
from brownie import VaultsAdapter, interface, accounts # type: ignore
from utils.evm_script import encode_calldata
from utils.test_helpers import assert_event_exists, set_account_balance

MOTION_BUFFER_TIME = 100

INITIAL_VAULT_BALANCE = 2 * 10**18


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[6]


@pytest.fixture(scope="module", autouse=True)
def adapter(owner, locator, easy_track, trusted_address, agent):
    adapter = VaultsAdapter.deploy(trusted_address, locator, easy_track.evmScriptExecutor(), 1000000000000000000, {"from": owner})
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    # grant all needed roles to adapter
    vault_hub = interface.IVaultHub(locator.vaultHub())
    vault_hub.grantRole(vault_hub.BAD_DEBT_MASTER_ROLE(), adapter, {"from": agent})
    vault_hub.grantRole(vault_hub.VALIDATOR_EXIT_ROLE(), adapter, {"from": agent})
    vault_hub.grantRole(vault_hub.REDEMPTION_MASTER_ROLE(), adapter, {"from": agent})
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), adapter, {"from": agent})
    return adapter


@pytest.fixture(scope="module", autouse=True)
def vaults(owner, accounts, locator, adapter):
    # Enable minting in default group
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    operator_grid.alterTiers([0], [(100_000 * 10**18, 300, 250, 50, 40, 10)], {"from": accounts.at(adapter.address, force=True)})

    # create vaults
    vault_factory = interface.IVaultFactory(locator.vaultFactory())
    vault_hub = interface.IVaultHub(locator.vaultHub())
    vault_factory.createVaultWithDashboard(owner, accounts[1], accounts[2], 10000, 10000, [], {"from": owner, "value": INITIAL_VAULT_BALANCE})
    vault1 = vault_hub.vaultByIndex(vault_hub.vaultsCount())
    vault_factory.createVaultWithDashboard(owner, accounts[1], accounts[2], 10000, 10000, [], {"from": owner, "value": INITIAL_VAULT_BALANCE})
    vault2 = vault_hub.vaultByIndex(vault_hub.vaultsCount())
    return [vault1, vault2]


def setup_evm_script_factory(
    factory_instance, permissions, easy_track, trusted_address, voting
):
    num_factories_before = len(easy_track.getEVMScriptFactories())
    print(f"factory_instance: {factory_instance}")
    print(f"permissions: {permissions}")
    easy_track.addEVMScriptFactory(factory_instance, permissions, {"from": voting})
    evm_script_factories = easy_track.getEVMScriptFactories()

    assert len(evm_script_factories) == num_factories_before + 1
    assert evm_script_factories[0] == factory_instance


def execute_motion(easy_track, motion_transaction, stranger):
    brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)
    motions = easy_track.getMotions()
    assert len(motions) == 1
    tx = easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0
    return tx


def create_enact_and_check_force_validator_exits_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    force_validator_exits_factory,
    vault_addresses,
    pubkeys,
    adapter,
):
    # Prepare all contracts
    lazy_oracle = interface.ILazyOracle(locator.lazyOracle())
    vault_hub = interface.IVaultHub(locator.vaultHub())
    accounting_oracle = locator.accountingOracle()
    set_account_balance(accounting_oracle)
    set_account_balance(lazy_oracle.address)

    # Create and execute motion to force validator exits
    motion_transaction = easy_track.createMotion(
        force_validator_exits_factory.address,
        encode_calldata(["address[]", "bytes[]"], [vault_addresses, pubkeys]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)

    # bring fresh report for vault
    current_time = brownie.chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})

    # make vault unhealthy
    vault_hub.applyVaultReport(
        vault_addresses[0],
        current_time,
        INITIAL_VAULT_BALANCE,
        INITIAL_VAULT_BALANCE,
        4 * INITIAL_VAULT_BALANCE,
        0,
        0,
        0,
        {"from": lazy_oracle})

    tx = easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0

    assert len(tx.events["ForcedValidatorExitTriggered"]) == len(vault_addresses)
    for i, event in enumerate(tx.events["ForcedValidatorExitTriggered"]):
        assert event["vault"] == vault_addresses[i]
        assert event["pubkeys"] == "0x" + pubkeys[i].hex()
        assert event["refundRecipient"] == adapter.address


def create_enact_and_check_set_liability_shares_target_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    set_liability_shares_target_factory,
    vaults,
    liability_shares_targets,
):
    # Prepare all contracts
    vault_hub = interface.IVaultHub(locator.vaultHub())
    lazy_oracle = interface.ILazyOracle(locator.lazyOracle())
    accounting_oracle = locator.accountingOracle()
    set_account_balance(accounting_oracle)
    set_account_balance(lazy_oracle.address)

    # Create and execute motion to set liability shares target
    motion_transaction = easy_track.createMotion(
        set_liability_shares_target_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vaults, liability_shares_targets]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    # bring fresh report for vaults
    current_time = brownie.chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})
    minted_shares = []
    for i, vault in enumerate(vaults):
        minted_shares.append(liability_shares_targets[i] * (i + 1))
        vault_hub.applyVaultReport(
            vault,
            current_time,
            INITIAL_VAULT_BALANCE,
            INITIAL_VAULT_BALANCE,
            0,
            0,
            0,
            0,
            {"from": lazy_oracle})

        vaultConnection = vault_hub.vaultConnection(vault)
        dashboard = vaultConnection[0]
        set_account_balance(dashboard)
        vault_hub.mintShares(vault, owner, minted_shares[i], {"from": dashboard})

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check that events were emitted from VaultHub via adapter
    assert len(tx.events["VaultRedemptionSharesUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultRedemptionSharesUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["redemptionShares"] == minted_shares[i] - liability_shares_targets[i]


def create_enact_and_check_socialize_bad_debt_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    socialize_bad_debt_factory,
    bad_debt_vaults,
    vault_acceptors,
    max_shares_to_socialize,
):
    # Prepare all contracts
    vault_hub = interface.IVaultHub(locator.vaultHub())
    lazy_oracle = interface.ILazyOracle(locator.lazyOracle())
    accounting_oracle = locator.accountingOracle()
    set_account_balance(accounting_oracle)
    set_account_balance(lazy_oracle.address)

    # Create and execute motion to socialize bad debt
    motion_transaction = easy_track.createMotion(
        socialize_bad_debt_factory.address,
        encode_calldata(
            ["address[]", "address[]", "uint256[]"],
            [bad_debt_vaults, vault_acceptors, max_shares_to_socialize]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    # bring fresh report bad debt vault
    current_time = brownie.chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})
    vault_hub.applyVaultReport(
        bad_debt_vaults[0],
        current_time,
        INITIAL_VAULT_BALANCE,
        INITIAL_VAULT_BALANCE,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle})

    vaultConnection = vault_hub.vaultConnection(bad_debt_vaults[0])
    dashboard = vaultConnection[0]
    set_account_balance(dashboard)
    vault_hub.mintShares(bad_debt_vaults[0], owner, 10 * max_shares_to_socialize[0], {"from": dashboard})

    brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)

    # bring fresh report for vaults
    current_time = brownie.chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})

    # fresh report for first vault
    vault_hub.applyVaultReport(
        vault_acceptors[0],
        current_time,
        INITIAL_VAULT_BALANCE,
        INITIAL_VAULT_BALANCE,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle})

    # make bad debt on second vault
    vault_hub.applyVaultReport(
        bad_debt_vaults[0],
        current_time,
        10 * max_shares_to_socialize[0],
        INITIAL_VAULT_BALANCE,
        0,
        INITIAL_VAULT_BALANCE,
        0,
        0,
        {"from": lazy_oracle})

    bad_debt_record_before = vault_hub.vaultRecord(bad_debt_vaults[0])
    bad_liability_before = bad_debt_record_before[2]
    acceptor_record_before = vault_hub.vaultRecord(vault_acceptors[0])
    acceptor_liability_before = acceptor_record_before[2]

    tx = easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0

    bad_debt_record_after = vault_hub.vaultRecord(bad_debt_vaults[0])
    bad_liability_after = bad_debt_record_after[2]
    acceptor_record_after = vault_hub.vaultRecord(vault_acceptors[0])
    acceptor_liability_after = acceptor_record_after[2]

    assert bad_liability_after + acceptor_liability_after == bad_liability_before + acceptor_liability_before
    liability_delta = bad_liability_before - bad_liability_after
    assert liability_delta > 0

    # Check that events were emitted for failed socializations
    assert len(tx.events["BadDebtSocialized"]) == len(bad_debt_vaults)
    for i, event in enumerate(tx.events["BadDebtSocialized"]):
        assert event["vaultDonor"] == bad_debt_vaults[i]
        assert event["vaultAcceptor"] == vault_acceptors[i]
        assert event["badDebtShares"] == liability_delta


@pytest.mark.skip_coverage
def test_force_validator_exits_happy_path(
    owner,
    ForceValidatorExitsInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    vaults,
    adapter,
):
    vault_hub = interface.IVaultHub(locator.vaultHub())

    factory_instance = deployer.deploy(ForceValidatorExitsInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 10**18 # 1 ETH
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.forceValidatorExit.signature[2:]

    print("force_validator_exits_happy_path")
    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_force_validator_exits_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        factory_instance,
        [vaults[0]],
        [b"01" * 48],  # 48 bytes per pubkey
        adapter,
    )


@pytest.mark.skip_coverage
def test_set_liability_shares_target_happy_path(
    owner,
    SetLiabilitySharesTargetInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    agent,
    vaults,
    adapter,
):
    factory_instance = deployer.deploy(SetLiabilitySharesTargetInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter

    permission = adapter.address + adapter.setLiabilitySharesTarget.signature[2:]

    print("set_liability_shares_target_happy_path")
    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_set_liability_shares_target_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        factory_instance,
        [vaults[0], vaults[1]],
        [100, 200],  # liability shares target values
    )


@pytest.mark.skip_coverage
def test_socialize_bad_debt_happy_path(
    owner,
    SocializeBadDebtInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    vaults,
    adapter,
):
    vault_hub = interface.IVaultHub(locator.vaultHub())

    factory_instance = deployer.deploy(SocializeBadDebtInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.socializeBadDebt.signature[2:]

    print("socialize_bad_debt_happy_path")
    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_socialize_bad_debt_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        factory_instance,
        [vaults[0]],  # bad debt vaults
        [vaults[1]],  # vault acceptors - both vaults have same operator
        [INITIAL_VAULT_BALANCE // 100],  # max shares to socialize
    )
