import pytest
import brownie

from utils.evm_script import encode_calldata

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


def setup_evm_script_factory(
    factory, permissions, easy_track, trusted_address, voting, deployer, vault_hub
):
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
    easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0


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

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, vault_address in enumerate(vault_addresses):
        connection = vault_hub.vaultConnection(vault_address)
        assert connection[0] == owner  # owner
        assert connection[6] == infra_fees_bp[i]  # infraFeeBP
        assert connection[7] == liquidity_fees_bp[i]  # liquidityFeeBP
        assert connection[8] == reservation_fees_bp[i]  # reservationFeeBP


@pytest.mark.skip_coverage
def test_update_share_limits_happy_path(
    owner,
    UpdateShareLimitsInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    vault_hub,
):
    permission = vault_hub.address + vault_hub.updateShareLimit.signature[2:]
    update_share_limits_factory = setup_evm_script_factory(
        UpdateShareLimitsInVaultHub,
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
    UpdateVaultsFeesInVaultHub,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    vault_hub,
):
    permission = vault_hub.address + vault_hub.updateVaultFees.signature[2:]
    update_vaults_fees_factory = setup_evm_script_factory(
        UpdateVaultsFeesInVaultHub,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        vault_hub,
    )

    create_enact_and_check_update_vaults_fees_motion(
        owner,
        easy_track,
        vault_hub,
        stranger,
        trusted_address,
        update_vaults_fees_factory,
        ["0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002"],
        [800, 900],  # infra fees BP
        [300, 400],  # liquidity fees BP
        [200, 300],  # reservation fees BP
    )
