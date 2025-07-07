import pytest
import brownie

from brownie import VaultHubAdapter, ForceTransfer # type: ignore
from utils.evm_script import encode_calldata
from utils.test_helpers import assert_event_exists

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[6]


@pytest.fixture(scope="module", autouse=True)
def adapter(owner, vault_hub, easy_track, trusted_address, agent):
    adapter = VaultHubAdapter.deploy(trusted_address, vault_hub, easy_track.evmScriptExecutor(), 1000000000000000000, {"from": owner})
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    # grant all needed roles to adapter
    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), adapter, {"from": agent})
    vault_hub.grantRole(vault_hub.BAD_DEBT_MASTER_ROLE(), adapter, {"from": agent})
    vault_hub.grantRole(vault_hub.VALIDATOR_EXIT_ROLE(), adapter, {"from": agent})
    return adapter


@pytest.fixture(scope="module")
def vaults(accounts):
    # real vaults from Hoodi
    vaults = ["0xa378598a89380fb1c5e973078d6e4030010f445c", "0xc7876E27Ff402a0e07BB7b566E0Db302A136Fbb9", "0x1E473b41aC408dBBc98C7E594886Fe2cb81dA42C"]
    return vaults


def setup_evm_script_factory(
    factory_instance, permissions, easy_track, trusted_address, voting
):
    num_factories_before = len(easy_track.getEVMScriptFactories())
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


def create_enact_and_check_update_share_limits_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    update_share_limits_factory,
    vaults,
    new_share_limits,
):
    # Create and execute motion to update share limit
    motion_transaction = easy_track.createMotion(
        update_share_limits_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vaults, new_share_limits]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vaults):
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[1] == new_share_limits[i]

    # Check that events were emitted
    assert len(tx.events["VaultShareLimitUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultShareLimitUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["newShareLimit"] == new_share_limits[i]


def create_enact_and_check_update_vaults_fees_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    update_vaults_fees_factory,
    vaults,
    infra_fees_bp,
    liquidity_fees_bp,
    reservation_fees_bp,
):    
    # Create and execute motion to update fees
    motion_transaction = easy_track.createMotion(
        update_vaults_fees_factory.address,
        encode_calldata(
            ["address[]", "uint256[]", "uint256[]", "uint256[]"], 
            [vaults, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vaults):
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[6] == infra_fees_bp[i]
        assert connection[7] == liquidity_fees_bp[i]
        assert connection[8] == reservation_fees_bp[i]

    # Check that events were emitted
    assert len(tx.events["VaultFeesUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultFeesUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["infraFeeBP"] == infra_fees_bp[i]
        assert event["liquidityFeeBP"] == liquidity_fees_bp[i]
        assert event["reservationFeeBP"] == reservation_fees_bp[i]


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

    assert len(tx.events["ForcedValidatorExitTriggered"]) == len(vault_addresses)
    for i, event in enumerate(tx.events["ForcedValidatorExitTriggered"]):
        assert event["vault"] == vault_addresses[i]
        assert event["pubkeys"] == "0x" + pubkeys[i].hex()
        assert event["refundRecipient"] == adapter.address


def create_enact_and_check_set_vault_redemptions_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    set_vault_redemptions_factory,
    vaults,
    redemptions_values,
):    
    # Create and execute motion to set vault redemptions
    motion_transaction = easy_track.createMotion(
        set_vault_redemptions_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vaults, redemptions_values]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vaults):
        obligations = vault_hub.vaultObligations(vault_address)
        assert obligations[2] == redemptions_values[i]  # redemptions
    
    # Check that events were emitted
    assert len(tx.events["RedemptionsUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["RedemptionsUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["unsettledRedemptions"] == redemptions_values[i]


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
    assert len(tx.events["BadDebtSocialized"]) == len(bad_debt_vaults)
    for i, event in enumerate(tx.events["BadDebtSocialized"]):
        assert event["vaultDonor"] == bad_debt_vaults[i]
        assert event["vaultAcceptor"] == vault_acceptors[i]
        assert event["badDebtShares"] == max_shares_to_socialize[i]


@pytest.mark.skip_coverage
def test_update_share_limits_happy_path(
    owner,
    DecreaseShareLimitsInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    vault_hub,
    vaults,
    adapter,
):  
    factory_instance = deployer.deploy(DecreaseShareLimitsInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.updateShareLimit.signature[2:]

    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_update_share_limits_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        vaults,
        [500, 500, 500],  # Using values less than current limit
    )


@pytest.mark.skip_coverage
def test_update_vaults_fees_happy_path(
    owner,
    DecreaseVaultsFeesInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    vault_hub,
    adapter,
    vaults,
):  
    factory_instance = deployer.deploy(DecreaseVaultsFeesInVaultHub, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.updateVaultFees.signature[2:]

    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_update_vaults_fees_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        vaults,
        [80, 90, 70],  # infra fees BP
        [30, 40, 30],  # liquidity fees BP
        [20, 30, 20],  # reservation fees BP
    )


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
    assert factory_instance.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.forceValidatorExit.signature[2:]

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
        1750427149, 
        699867039001672206, 
        3600000000000000000, 
        0, 
        799867039001672206, 
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
def test_set_vault_redemptions_happy_path(
    owner,
    SetVaultRedemptionsInVaultHub,
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

    factory_instance = deployer.deploy(SetVaultRedemptionsInVaultHub, trusted_address, vault_hub)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub

    permission = vault_hub.address + vault_hub.setVaultRedemptions.signature[2:]

    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
    )

    create_enact_and_check_set_vault_redemptions_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        [vaults[0], vaults[1]],
        [100, 200],  # redemptions values
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
    assert factory_instance.vaultHubAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.socializeBadDebt.signature[2:]

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
        1750427149, 
        699867039001672206, 
        3600000000000000000, 
        0, 
        799867039001672206, 
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
        [vaults[2]],  # vault acceptors - both vaults have same operator
        [100],  # max shares to socialize
    )
