import pytest
import brownie

from brownie import VaultsAdapter, ForceTransfer # type: ignore
from utils.evm_script import encode_calldata
from utils.test_helpers import assert_event_exists

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[6]


@pytest.fixture(scope="module", autouse=True)
def adapter(owner, vault_hub, operator_grid, easy_track, trusted_address, agent):
    adapter = VaultsAdapter.deploy(trusted_address, vault_hub, operator_grid, easy_track.evmScriptExecutor(), 1000000000000000000, {"from": owner})
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    # grant all needed roles to adapter
    vault_hub.grantRole(vault_hub.BAD_DEBT_MASTER_ROLE(), adapter, {"from": agent})
    vault_hub.grantRole(vault_hub.VALIDATOR_EXIT_ROLE(), adapter, {"from": agent})
    return adapter


@pytest.fixture(scope="module")
def vaults(accounts):
    # real vaults from Hoodi
    vaults = ["0x08bb216533b82B02D8BA713B075467aC1F9F3C53", "0x20e13020Ba6A6E9BF5FA470B02df21Fd3E97e49E"]
    return vaults


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
    vault_hub,
    stranger,
    trusted_address,
    force_validator_exits_factory,
    vault_addresses,
    pubkeys,
    adapter,
):
    # Create and execute motion to force validator exits
    motion_transaction = easy_track.createMotion(
        force_validator_exits_factory.address,
        encode_calldata(["address[]", "bytes[]"], [vault_addresses, pubkeys]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # assert len(tx.events["ForcedValidatorExitTriggered"]) == len(vault_addresses)
    # for i, event in enumerate(tx.events["ForcedValidatorExitTriggered"]):
    #     assert event["vault"] == vault_addresses[i]
    #     assert event["pubkeys"] == "0x" + pubkeys[i].hex()
    #     assert event["refundRecipient"] == adapter.address


def create_enact_and_check_set_liability_shares_target_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    set_liability_shares_target_factory,
    vaults,
    liability_shares_targets,
):
    # Create and execute motion to set liability shares target
    motion_transaction = easy_track.createMotion(
        set_liability_shares_target_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vaults, liability_shares_targets]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check that events were emitted
    assert len(tx.events["VaultRedemptionSharesUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultRedemptionSharesUpdated"]):
        assert event["vault"] == vaults[i]


def create_enact_and_check_socialize_bad_debt_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    socialize_bad_debt_factory,
    bad_debt_vaults,
    vault_acceptors,
    max_shares_to_socialize,
):
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

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check that events were emitted for failed socializations
    # assert len(tx.events["BadDebtSocialized"]) == len(bad_debt_vaults)
    # for i, event in enumerate(tx.events["BadDebtSocialized"]):
    #     assert event["vaultDonor"] == bad_debt_vaults[i]
    #     assert event["vaultAcceptor"] == vault_acceptors[i]
    #     assert event["badDebtShares"] == max_shares_to_socialize[i]


@pytest.mark.skip_coverage
def test_force_validator_exits_happy_path(
    owner,
    ForceValidatorExitsInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    vault_hub,
    vaults,
    adapter,
    lazy_oracle,
):
    factory_instance = deployer.deploy(ForceValidatorExitsInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
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

    # make vault unhealthy
    forceTransfer = ForceTransfer.deploy({"from": owner})
    forceTransfer.transfer(lazy_oracle, {"from": owner, "value": 10 * 10**18})
    vault_hub.applyVaultReport(
        vaults[0],
        1758648132,
        6 * 10**18,
        5 * 10**18,
        0,
        7 * 10**18,
        0,
        0,
        {"from": lazy_oracle})

    create_enact_and_check_force_validator_exits_motion(
        owner,
        easy_track,
        vault_hub,
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
    vault_hub,
    agent,
    vaults,
):
    # transfer 10 ETH to agent
    owner.transfer(agent, 10 * 10**18)
    vault_hub.grantRole(vault_hub.REDEMPTION_MASTER_ROLE(), easy_track.evmScriptExecutor(), {"from": agent})
    vault_hub.grantRole(vault_hub.REDEMPTION_MASTER_ROLE(), owner, {"from": agent})

    factory_instance = deployer.deploy(SetLiabilitySharesTargetInVaultHub, trusted_address, vault_hub)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub

    permission = vault_hub.address + vault_hub.setLiabilitySharesTarget.signature[2:]

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
        vault_hub,
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
    vault_hub,
    vaults,
    adapter,
    lazy_oracle,
):
    factory_instance = deployer.deploy(SocializeBadDebtInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
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

    # make vault unhealthy
    forceTransfer = ForceTransfer.deploy({"from": owner})
    forceTransfer.transfer(lazy_oracle, {"from": owner, "value": 10 * 10**18})
    vault_hub.applyVaultReport(
        vaults[0],
        1758648132,
        1 * 10**18,
        0,
        0,
        7 * 10**18,
        0,
        0,
        {"from": lazy_oracle})

    # make vault healthy and ready to accept bad debt
    vault_hub.applyVaultReport(
        vaults[1],
        1758648132,
        100 * 10**18,
        0,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle})

    create_enact_and_check_socialize_bad_debt_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        [vaults[0]],  # bad debt vaults
        [vaults[1]],  # vault acceptors - both vaults have same operator
        [100],  # max shares to socialize
    )
