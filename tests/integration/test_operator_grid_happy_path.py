import pytest
import brownie
from brownie import VaultsAdapter, interface # type: ignore
from utils.evm_script import encode_calldata
from utils.test_helpers import set_account_balance

MOTION_BUFFER_TIME = 100
INITIAL_VAULT_BALANCE = 2 * 10 ** 18

@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]

@pytest.fixture(scope="module", autouse=True)
def adapter(owner, locator, easy_track, trusted_address, agent):
    adapter = VaultsAdapter.deploy(trusted_address, locator, easy_track.evmScriptExecutor(), 1000000000000000000, {"from": owner})
    # send 10 ETH to adapter
    owner.transfer(adapter, 10 * 10 ** 18)
    # grant all needed roles to adapter
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), adapter, {"from": agent})
    return adapter

@pytest.fixture(scope="module", autouse=True)
def vaults(owner, accounts, locator):
    vault_factory = interface.IVaultFactory(locator.vaultFactory())
    vault_hub = interface.IVaultHub(locator.vaultHub())
    tx = vault_factory.createVaultWithDashboard(accounts[0], accounts[1], accounts[2], 10000, 10000, [], {"from": owner, "value": INITIAL_VAULT_BALANCE})
    vault1 = vault_hub.vaultByIndex(vault_hub.vaultsCount())
    return [vault1]


def setup_operator_grid(owner, locator, easy_track, agent):
    set_account_balance(agent.address)
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), easy_track.evmScriptExecutor(), {"from": agent})
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), owner, {"from": agent})


def setup_evm_script_factory(
    factory_instance, permissions, easy_track, trusted_address, voting, deployer
):
    num_factories_before = len(easy_track.getEVMScriptFactories())
    print(f"factory_instance: {factory_instance}")
    print(f"permissions: {permissions}")
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


def create_enact_and_check_register_group_motion(
    easy_track,
    locator,
    stranger,
    trusted_address,
    register_group_factory,
    operator_addresses,
    share_limits,
    tiers_params_array,
):
    motion_transaction = easy_track.createMotion(
        register_group_factory.address,
        encode_calldata(
            ["address[]", "uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
            [operator_addresses, share_limits, tiers_params_array]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == brownie.ZERO_ADDRESS  # operator
        assert group[1] == 0  # shareLimit
        assert len(group[3]) == 0  # tiersId array should be empty

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == share_limits[i]  # shareLimit
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should have the same length as tiers_params

        # Check tier details
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP


def create_enact_and_check_update_share_limits_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    update_share_limits_factory,
    operator_addresses,
    new_share_limits,
):
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())

    # First register the group to update
    for i, operator_address in enumerate(operator_addresses):
        operator_grid.registerGroup(operator_address, new_share_limits[i]*2, {"from": owner})

    # Check initial state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i]*2  # shareLimit

    # Create and execute motion to update share limit
    motion_transaction = easy_track.createMotion(
        update_share_limits_factory.address,
        encode_calldata(["address[]", "uint256[]"], [operator_addresses, new_share_limits]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert group[0] == operator_address  # operator
        assert group[1] == new_share_limits[i] # shareLimit


def create_enact_and_check_register_tiers_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    register_tiers_factory,
    operator_addresses,
    tiers_params_array,
):
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())

    # First register the groups to add tiers to
    for operator_address in operator_addresses:
        operator_grid.registerGroup(operator_address, 1000, {"from": owner})

    # Check initial state - no tiers
    for operator_address in operator_addresses:
        group = operator_grid.group(operator_address)
        assert len(group[3]) == 0  # tiersId array should be empty

    # Create and execute motion to register tiers
    motion_transaction = easy_track.createMotion(
        register_tiers_factory.address,
        encode_calldata(
            ["address[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[][]"],
            [operator_addresses, tiers_params_array]
        ),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state - tiers should be registered
    for i, operator_address in enumerate(operator_addresses):
        group = operator_grid.group(operator_address)
        assert len(group[3]) == len(tiers_params_array[i])  # tiersId array should have the same length as tiers_params

        # Check tier details
        for j, tier_id in enumerate(group[3]):
            tier = operator_grid.tier(tier_id)
            assert tier[1] == tiers_params_array[i][j][0]  # shareLimit
            assert tier[3] == tiers_params_array[i][j][1]  # reserveRatioBP
            assert tier[4] == tiers_params_array[i][j][2]  # forcedRebalanceThresholdBP
            assert tier[5] == tiers_params_array[i][j][3]  # infraFeeBP
            assert tier[6] == tiers_params_array[i][j][4]  # liquidityFeeBP
            assert tier[7] == tiers_params_array[i][j][5]  # reservationFeeBP


def create_enact_and_check_alter_tiers_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    alter_tiers_factory,
    new_tier_params,
):
    operator_grid = interface.IOperatorGrid(locator.operatorGrid())

    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid.registerGroup(operator_address, 10000, {"from": owner})
    initial_tier_params = [(1000, 200, 100, 50, 40, 10), (1000, 200, 100, 50, 40, 10)]
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": owner})

    tiers_count = operator_grid.tiersCount()
    tier_ids = [tiers_count - 2, tiers_count - 1]

    # Check initial state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == initial_tier_params[i][0]  # shareLimit
        assert tier[3] == initial_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == initial_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == initial_tier_params[i][3]  # infraFeeBP
        assert tier[6] == initial_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == initial_tier_params[i][5]  # reservationFeeBP

    # Create and execute motion to alter tier
    motion_transaction = easy_track.createMotion(
        alter_tiers_factory.address,
        encode_calldata(["uint256[]", "(uint256,uint256,uint256,uint256,uint256,uint256)[]"], [tier_ids, new_tier_params]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    for i, tier_id in enumerate(tier_ids):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == new_tier_params[i][0]  # shareLimit
        assert tier[3] == new_tier_params[i][1]  # reserveRatioBP
        assert tier[4] == new_tier_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == new_tier_params[i][3]  # infraFeeBP
        assert tier[6] == new_tier_params[i][4]  # liquidityFeeBP
        assert tier[7] == new_tier_params[i][5]  # reservationFeeBP


def create_enact_and_check_set_jail_status_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    set_jail_status_factory,
    vaults,
    jail_statuses,
):
    # Create and execute motion to set jail status
    motion_transaction = easy_track.createMotion(
        set_jail_status_factory.address,
        encode_calldata(["address[]", "bool[]"], [vaults, jail_statuses]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    tx = execute_motion(easy_track, motion_transaction, stranger)

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())

    # Check final state
    for i, vault in enumerate(vaults):
        is_in_jail = operator_grid.isVaultInJail(vault)
        assert is_in_jail == jail_statuses[i]

    # Check that events were emitted
    assert len(tx.events["VaultJailStatusUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultJailStatusUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["isInJail"] == jail_statuses[i]


def create_enact_and_check_update_vaults_fees_motion(
    owner,
    easy_track,
    locator,
    stranger,
    trusted_address,
    update_vaults_fees_factory,
    vaults,
    infra_fees_bp,
    liquidity_fees_bp,
    reservation_fees_bp,
):
    # Prepare all contracts
    lazy_oracle = interface.ILazyOracle(locator.lazyOracle())
    vault_hub = interface.IVaultHub(locator.vaultHub())
    accounting_oracle = locator.accountingOracle()
    set_account_balance(accounting_oracle)
    set_account_balance(lazy_oracle.address)

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

    brownie.chain.sleep(easy_track.motionDuration() + MOTION_BUFFER_TIME)
    motions = easy_track.getMotions()
    assert len(motions) == 1

    # bring fresh report for vault
    current_time = brownie.chain.time()
    lazy_oracle.updateReportData(current_time, 1000, "0x00", "0x00", {"from": accounting_oracle})
    vault_hub.applyVaultReport(
        vaults[0],
        current_time,
        INITIAL_VAULT_BALANCE,
        INITIAL_VAULT_BALANCE,
        0,
        0,
        0,
        0,
        {"from": lazy_oracle})

    # Check initial state
    connection = vault_hub.vaultConnection(vaults[0])
    assert connection[6] != infra_fees_bp[0] # infraFeeBP
    assert connection[7] != liquidity_fees_bp[0] # liquidityFeeBP
    assert (connection[8] != reservation_fees_bp[0] or connection[8] == 0) # reservationFeeBP

    tx = easy_track.enactMotion(
        motions[0][0],
        motion_transaction.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )
    assert len(easy_track.getMotions()) == 0

    # Check final state
    connection = vault_hub.vaultConnection(vaults[0])
    assert connection[6] == infra_fees_bp[0] # infraFeeBP
    assert connection[7] == liquidity_fees_bp[0] # liquidityFeeBP
    assert connection[8] == reservation_fees_bp[0] # reservationFeeBP

    # Check that events were emitted
    assert len(tx.events["VaultFeesUpdated"]) == len(vaults)
    for i, event in enumerate(tx.events["VaultFeesUpdated"]):
        assert event["vault"] == vaults[i]
        assert event["infraFeeBP"] == infra_fees_bp[i]
        assert event["liquidityFeeBP"] == liquidity_fees_bp[i]
        assert event["reservationFeeBP"] == reservation_fees_bp[i]


@pytest.mark.skip_coverage
def test_register_group_happy_path(
    owner,
    RegisterGroupsInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    agent,
):
    setup_operator_grid(owner, locator, easy_track, agent)

    factory_instance = deployer.deploy(RegisterGroupsInOperatorGrid, trusted_address, locator, 10000)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.lidoLocator() == locator
    assert factory_instance.maxShareLimit() == 10000

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    permission = operator_grid.address + operator_grid.registerGroup.signature[2:] + operator_grid.address[2:] + operator_grid.registerTiers.signature[2:]
    print("register_group_happy_path")
    register_group_factory = setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    # Define operator addresses
    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    ]

    share_limits = [1000, 5000]

    tiers_params_array = [
        [(500, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
        [(800, 200, 100, 50, 40, 10), (800, 200, 100, 50, 40, 10)],
    ]

    create_enact_and_check_register_group_motion(
        easy_track,
        locator,
        stranger,
        trusted_address,
        register_group_factory,
        operator_addresses,
        share_limits,
        tiers_params_array,
    )


@pytest.mark.skip_coverage
def test_update_groups_share_limit_happy_path(
    owner,
    UpdateGroupsShareLimitInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    agent,
):
    setup_operator_grid(owner, locator, easy_track, agent)

    factory_instance = deployer.deploy(UpdateGroupsShareLimitInOperatorGrid, trusted_address, locator, 10000)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.lidoLocator() == locator
    assert factory_instance.maxShareLimit() == 10000

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    permission = operator_grid.address + operator_grid.updateGroupShareLimit.signature[2:]
    print("update_groups_share_limit_happy_path")
    update_share_limits_factory = setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    create_enact_and_check_update_share_limits_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        update_share_limits_factory,
        ["0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002"],
        [2000, 3000],
    )


@pytest.mark.skip_coverage
def test_register_tiers_happy_path(
    owner,
    RegisterTiersInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    agent,
):
    setup_operator_grid(owner, locator, easy_track, agent)

    factory_instance = deployer.deploy(RegisterTiersInOperatorGrid, trusted_address, locator)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.lidoLocator() == locator

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    permission = operator_grid.address + operator_grid.registerTiers.signature[2:]
    print("register_tiers_happy_path")
    register_tiers_factory = setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    # Define operator addresses
    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002"
    ]

    # Define tier parameters for each operator
    tiers_params_array = [
        [  # Tiers for operator 1
            (500, 200, 100, 50, 40, 10),
            (300, 150, 75, 25, 20, 5),
        ],
        [  # Tiers for operator 2
            (800, 250, 125, 60, 50, 15),
            (400, 180, 90, 30, 25, 8),
        ]
    ]

    create_enact_and_check_register_tiers_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        register_tiers_factory,
        operator_addresses,
        tiers_params_array,
    )


@pytest.mark.skip_coverage
def test_alter_tiers_happy_path(
    owner,
    AlterTiersInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    agent,
):
    setup_operator_grid(owner, locator, easy_track, agent)

    max_share_limit = 1000 * 10**18  # 1000 ETH for testing
    factory_instance = deployer.deploy(AlterTiersInOperatorGrid, trusted_address, locator, max_share_limit)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.lidoLocator() == locator
    assert factory_instance.defaultTierMaxShareLimit() == max_share_limit

    operator_grid = interface.IOperatorGrid(locator.operatorGrid())
    permission = operator_grid.address + operator_grid.alterTiers.signature[2:]
    print("alter_tiers_happy_path")
    alter_tiers_factory = setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    # Define new tier parameters
    new_tier_params = [(2000, 300, 150, 75, 60, 20), (3000, 400, 200, 100, 80, 30)]  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)

    create_enact_and_check_alter_tiers_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        alter_tiers_factory,
        new_tier_params,
    )


@pytest.mark.skip_coverage
def test_set_jail_status_happy_path(
    owner,
    SetJailStatusInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    adapter,
    vaults,
):
    factory_instance = deployer.deploy(SetJailStatusInOperatorGrid, trusted_address, adapter)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.setVaultJailStatus.signature[2:]

    print("set_jail_status_happy_path")
    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    create_enact_and_check_set_jail_status_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        factory_instance,
        vaults,
        [True],  # jail statuses
    )


@pytest.mark.skip_coverage
def test_update_vaults_fees_happy_path(
    owner,
    UpdateVaultsFeesInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    locator,
    vaults,
    adapter,
):
    max_liquidity_fee_bp = 1000
    max_reservation_fee_bp = 100
    max_infra_fee_bp = 100
    factory_instance = deployer.deploy(UpdateVaultsFeesInOperatorGrid, trusted_address, adapter, locator, max_liquidity_fee_bp, max_reservation_fee_bp, max_infra_fee_bp)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.vaultsAdapter() == adapter
    assert factory_instance.lidoLocator() == locator
    assert adapter.validatorExitFeeLimit() == 1000000000000000000
    assert adapter.trustedCaller() == trusted_address
    assert adapter.evmScriptExecutor() == easy_track.evmScriptExecutor()

    permission = adapter.address + adapter.updateVaultFees.signature[2:]

    print("update_vaults_fees_happy_path")
    setup_evm_script_factory(
        factory_instance,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
    )

    create_enact_and_check_update_vaults_fees_motion(
        owner,
        easy_track,
        locator,
        stranger,
        trusted_address,
        factory_instance,
        vaults,
        [1],  # infra fees BP
        [1],  # liquidity fees BP
        [0],  # reservation fees BP
    )
