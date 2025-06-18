import pytest
import brownie

from utils.evm_script import encode_calldata
from utils.test_helpers import assert_event_exists

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[6]


@pytest.fixture(scope="module", autouse=True)
def vault_hub(owner, VaultHubStub, easy_track):
    vault_hub = owner.deploy(VaultHubStub, owner)
    vault_hub.grantRole(vault_hub.REDEMPTION_MASTER_ROLE(), easy_track.evmScriptExecutor(), {"from": owner})
    return vault_hub


@pytest.fixture(scope="module")
def vaults(accounts):
    vaults = [account.address for account in accounts[7:10]]
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
    vault_addresses,
    new_share_limits,
):
    # First register the vaults to update
    for vault_address in vault_addresses:
        vault_hub.connectVault(vault_address, {"from": owner})
    
    # Check initial state
    for i, vault_address in enumerate(vault_addresses):
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[0] == owner  # owner
        assert connection[1] == 1000  # shareLimit (default from VaultHubStub)
    
    # Create and execute motion to update share limit
    motion_transaction = easy_track.createMotion(
        update_share_limits_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vault_addresses, new_share_limits]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vault_addresses):
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[0] == owner  # owner
        assert connection[1] == new_share_limits[i]  # shareLimit


def create_enact_and_check_update_vaults_fees_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    update_vaults_fees_factory,
    vault_addresses,
    infra_fees_bp,
    liquidity_fees_bp,
    reservation_fees_bp,
):
    # First register the vaults to update
    for vault_address in vault_addresses:
        vault_hub.connectVault(vault_address, {"from": owner})
    
    # Check initial state
    for vault_address in vault_addresses:
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[0] == owner  # owner
        assert connection[6] == 1000  # infraFeeBP (default from VaultHubStub)
        assert connection[7] == 500   # liquidityFeeBP (default from VaultHubStub)
        assert connection[8] == 500   # reservationFeeBP (default from VaultHubStub)
    
    # Create and execute motion to update fees
    motion_transaction = easy_track.createMotion(
        update_vaults_fees_factory.address,
        encode_calldata(
            ["address[]", "uint256[]", "uint256[]", "uint256[]"], 
            [vault_addresses, infra_fees_bp, liquidity_fees_bp, reservation_fees_bp]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check that events were emitted only for non-reverting vaults
    assert len(tx.events["VaultFeesUpdated"]) == len(vault_addresses) - 1  # First vault is special and will revert
    for i, event in enumerate(tx.events["VaultFeesUpdated"]):
        assert event["vault"] == vault_addresses[i+1]  # Skip first vault
        assert event["infraFeeBP"] == infra_fees_bp[i+1]
        assert event["liquidityFeeBP"] == liquidity_fees_bp[i+1]
        assert event["reservationFeeBP"] == reservation_fees_bp[i+1]


def create_enact_and_check_force_validator_exits_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    force_validator_exits_factory,
    vault_addresses,
    pubkeys,
):
    # First register the vaults to update
    for vault_address in vault_addresses:
        vault_hub.connectVault(vault_address, {"from": owner})
    
    # Create and execute motion to force validator exits
    motion_transaction = easy_track.createMotion(
        force_validator_exits_factory.address,
        encode_calldata(["address[]", "bytes[]"], [vault_addresses, pubkeys]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1
    
    tx = execute_motion(easy_track, motion_transaction, stranger)

    assert len(tx.events["ForcedValidatorExitTriggered"]) == len(vault_addresses) - 1 # First vault is special and will revert
    for i, event in enumerate(tx.events["ForcedValidatorExitTriggered"]):
        assert event["vault"] == vault_addresses[i+1]
        assert event["pubkeys"] == "0x" + pubkeys[i+1].hex()
        assert event["refundRecipient"] == force_validator_exits_factory.address


def create_enact_and_check_set_vault_redemptions_motion(
    owner,
    easy_track,
    vault_hub,
    stranger,
    trusted_address,
    set_vault_redemptions_factory,
    vault_addresses,
    redemptions_values,
):
    # First register the vaults to update
    for vault_address in vault_addresses:
        vault_hub.connectVault(vault_address, {"from": owner})
    
    # Check initial state
    for vault_address in vault_addresses:
        obligations = vault_hub.vaultObligations(vault_address)
        assert obligations[2] == 0  # redemptions (default from VaultHubStub)
    
    # Create and execute motion to set vault redemptions
    motion_transaction = easy_track.createMotion(
        set_vault_redemptions_factory.address,
        encode_calldata(["address[]", "uint256[]"], [vault_addresses, redemptions_values]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vault_addresses):
        obligations = vault_hub.vaultObligations(vault_address)
        assert obligations[2] == redemptions_values[i]  # redemptions


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
    # First register the vaults to update
    for vault_address in bad_debt_vaults:
        vault_hub.connectVault(vault_address, {"from": owner})
    
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
    assert len(tx.events["BadDebtSocialized"]) == len(bad_debt_vaults) - 1  # First vault is special and will revert
    for i, event in enumerate(tx.events["BadDebtSocialized"]):
        assert event["vaultDonor"] == bad_debt_vaults[i+1]
        assert event["vaultAcceptor"] == vault_acceptors[i+1]
        assert event["badDebtShares"] == max_shares_to_socialize[i+1]


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
):  
    factory_instance = deployer.deploy(DecreaseShareLimitsInVaultHub, trusted_address, vault_hub, easy_track.evmScriptExecutor())
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub
    assert factory_instance.evmScriptExecutor() == easy_track.evmScriptExecutor()

    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), factory_instance, {"from": owner})

    permission = factory_instance.address + factory_instance.updateShareLimit.signature[2:]

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
        ["0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002"],
        [500, 500],  # Using values less than current limit (1000)
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
):  
    factory_instance = deployer.deploy(DecreaseVaultsFeesInVaultHub, trusted_address, vault_hub, easy_track.evmScriptExecutor())
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub
    assert factory_instance.evmScriptExecutor() == easy_track.evmScriptExecutor()

    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), factory_instance, {"from": owner})

    permission = factory_instance.address + factory_instance.updateVaultFees.signature[2:]

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
        ["0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002", "0x0000000000000000000000000000000000000003"],
        [800, 900, 1000],  # infra fees BP
        [300, 400, 500],  # liquidity fees BP
        [200, 300, 400],  # reservation fees BP
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
):  
    factory_instance = deployer.deploy(ForceValidatorExitsInVaultHub, trusted_address, vault_hub, easy_track.evmScriptExecutor())
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub
    assert factory_instance.evmScriptExecutor() == easy_track.evmScriptExecutor()

    # send 10 ETH to factory
    owner.transfer(factory_instance, 10 * 10 ** 18)

    vault_hub.grantRole(vault_hub.VALIDATOR_EXIT_ROLE(), factory_instance, {"from": owner})

    permission = factory_instance.address + factory_instance.forceValidatorExit.signature[2:]

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
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        vaults,
        [b"01" * 48, b"02" * 48, b"03" * 48],  # 48 bytes per pubkey
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
):  
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
        ["0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002"],
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
):
    factory_instance = deployer.deploy(SocializeBadDebtInVaultHub, trusted_address, vault_hub, easy_track.evmScriptExecutor())
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultHub() == vault_hub
    assert factory_instance.evmScriptExecutor() == easy_track.evmScriptExecutor()

    vault_hub.grantRole(vault_hub.BAD_DEBT_MASTER_ROLE(), factory_instance, {"from": owner})

    permission = factory_instance.address + factory_instance.socializeBadDebt.signature[2:]

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
        vault_hub,
        stranger,
        trusted_address,
        factory_instance,
        vaults,  # bad debt vaults
        [vaults[1], vaults[2], vaults[0]],  # vault acceptors (rotated to avoid self-acceptance)
        [100, 200, 300],  # max shares to socialize
    )
