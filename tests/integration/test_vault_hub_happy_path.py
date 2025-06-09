import pytest
import brownie

from utils.evm_script import encode_calldata
from utils.test_helpers import assert_event_exists

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]


@pytest.fixture(scope="module", autouse=True)
def vault_hub(owner, VaultHubStub, easy_track):
    vault_hub = owner.deploy(VaultHubStub, owner)
    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), easy_track.evmScriptExecutor(), {"from": owner})
    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), owner, {"from": owner})
    return vault_hub


@pytest.fixture(scope="module", autouse=True)
def adapter(owner, vault_hub, ForceValidatorExitAdapter, easy_track):
    adapter = owner.deploy(ForceValidatorExitAdapter, owner, vault_hub, easy_track.evmScriptExecutor())
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    vault_hub.grantRole(vault_hub.VALIDATOR_EXIT_ROLE(), adapter, {"from": owner})
    return adapter


@pytest.fixture(scope="module")
def vaults(owner, StakingVaultStub):
    vaults = [owner.deploy(StakingVaultStub).address for _ in range(3)]
    return vaults


@pytest.fixture(scope="module", autouse=True)
def update_vaults_fees_adapter(owner, vault_hub, UpdateVaultsFeesAdapter, easy_track):
    adapter = owner.deploy(UpdateVaultsFeesAdapter, vault_hub, easy_track.evmScriptExecutor())
    vault_hub.grantRole(vault_hub.VAULT_MASTER_ROLE(), adapter, {"from": owner})
    return adapter


def setup_evm_script_factory(
    factory, permissions, easy_track, trusted_address, voting, deployer, vault_hub, adapter=None
):
    if adapter is not None:
        factory_instance = deployer.deploy(factory, trusted_address, adapter)
        assert factory_instance.trustedCaller() == trusted_address
        assert factory_instance.adapter() == adapter
    else:
        factory_instance = deployer.deploy(factory, trusted_address, vault_hub)
        assert factory_instance.trustedCaller() == trusted_address
        assert factory_instance.vaultHub() == vault_hub

    num_factories_before = len(easy_track.getEVMScriptFactories())
    easy_track.addEVMScriptFactory(factory_instance, permissions, {"from": voting})
    evm_script_factories = easy_track.getEVMScriptFactories()

    assert len(evm_script_factories) == num_factories_before + 1
    assert evm_script_factories[0] == factory_instance

    return factory_instance


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
    adapter,
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

    assert len(tx.events["ValidatorExitsForced"]) == len(vault_addresses) - 1 # First vault is special and will revert
    for i, event in enumerate(tx.events["ValidatorExitsForced"]):
        assert event["vault"] == vault_addresses[i+1]
        assert event["pubkeys"] == "0x" + pubkeys[i+1].hex()
        assert event["refundRecipient"] == adapter.address


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
    permission = vault_hub.address + vault_hub.updateShareLimit.signature[2:]
    update_share_limits_factory = setup_evm_script_factory(
        DecreaseShareLimitsInVaultHub,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        vault_hub,
    )

    create_enact_and_check_update_share_limits_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        update_share_limits_factory,
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
    update_vaults_fees_adapter,
):
    permission = update_vaults_fees_adapter.address + update_vaults_fees_adapter.updateVaultFees.signature[2:]
    update_vaults_fees_factory = setup_evm_script_factory(
        DecreaseVaultsFeesInVaultHub,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        vault_hub,
        update_vaults_fees_adapter,
    )

    create_enact_and_check_update_vaults_fees_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        update_vaults_fees_factory,
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
    adapter,
    vaults,
):
    permission = adapter.address + adapter.forceValidatorExit.signature[2:]
    force_validator_exits_factory = setup_evm_script_factory(
        ForceValidatorExitsInVaultHub,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        vault_hub,
        adapter,
    )

    create_enact_and_check_force_validator_exits_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        force_validator_exits_factory,
        vaults,
        [b"01" * 48, b"02" * 48, b"03" * 48],  # 48 bytes per pubkey
        adapter,
    )
