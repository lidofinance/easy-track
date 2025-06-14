import pytest
import brownie

from utils.evm_script import encode_calldata

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]


# TODO: use real address of operator grid when it will be deployed - remove this fixture and uncomment the setup_operator_grid function
@pytest.fixture(scope="module", autouse=True)
def operator_grid(owner, OperatorGridStub, easy_track):
    default_tier_params = (1000, 200, 100, 50, 40, 10) # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)
    operator_grid = owner.deploy(OperatorGridStub, owner, default_tier_params)
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), easy_track.evmScriptExecutor(), {"from": owner})
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), owner, {"from": owner})
    return operator_grid


def setup_operator_grid(owner, operator_grid, easy_track, agent):
    evm_executor = easy_track.evmScriptExecutor()
    # TODO: uncomment this once the operator grid is deployed
    # operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), evm_executor, {"from": agent})
    # operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), owner, {"from": agent})


def setup_evm_script_factory(
    factory, permissions, easy_track, trusted_address, voting, deployer, operator_grid
):
    factory_instance = deployer.deploy(factory, trusted_address, operator_grid)
    assert factory_instance.trustedCaller() == trusted_address
    assert factory_instance.operatorGrid() == operator_grid

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


def create_enact_and_check_register_group_motion(
    easy_track,
    operator_grid,
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
    operator_grid,
    stranger,
    trusted_address,
    update_share_limits_factory,
    operator_addresses,
    new_share_limits,
):
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
    operator_grid,
    stranger,
    trusted_address,
    register_tiers_factory,
    operator_addresses,
    tiers_params_array,
):
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
    operator_grid,
    stranger,
    trusted_address,
    alter_tiers_factory,
    tier_ids,
    new_tier_params,
):
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid.registerGroup(operator_address, 10000, {"from": owner})
    initial_tier_params = [(1000, 200, 100, 50, 40, 10), (1000, 200, 100, 50, 40, 10)]
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": owner})

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

@pytest.mark.skip_coverage
def test_register_group_happy_path(
    owner,
    RegisterGroupsInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    operator_grid,
    agent,
):
    setup_operator_grid(owner, operator_grid, easy_track, agent)

    permission = operator_grid.address + operator_grid.registerGroup.signature[2:] + operator_grid.address[2:] + operator_grid.registerTiers.signature[2:]
    register_group_factory = setup_evm_script_factory(
        RegisterGroupsInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    # Define operator addresses and share limits
    operator_addresses = [
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002"
    ]
    share_limits = [1000, 1500]

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

    create_enact_and_check_register_group_motion(
        easy_track,
        operator_grid,
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
    operator_grid,
    agent,
):
    setup_operator_grid(owner, operator_grid, easy_track, agent)

    permission = operator_grid.address + operator_grid.updateGroupShareLimit.signature[2:]
    update_share_limits_factory = setup_evm_script_factory(
        UpdateGroupsShareLimitInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    create_enact_and_check_update_share_limits_motion(
        owner,
        easy_track,
        operator_grid,
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
    operator_grid,
    agent,
):
    setup_operator_grid(owner, operator_grid, easy_track, agent)

    permission = operator_grid.address + operator_grid.registerTiers.signature[2:]
    register_tiers_factory = setup_evm_script_factory(
        RegisterTiersInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
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
        operator_grid,
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
    operator_grid,
    agent,
):
    setup_operator_grid(owner, operator_grid, easy_track, agent)

    permission = operator_grid.address + operator_grid.alterTiers.signature[2:]
    alter_tiers_factory = setup_evm_script_factory(
        AlterTiersInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    # Define new tier parameters
    new_tier_params = [(2000, 300, 150, 75, 60, 20), (3000, 400, 200, 100, 80, 30)]  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP, liquidityFeeBP, reservationFeeBP)

    create_enact_and_check_alter_tiers_motion(
        owner,
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        alter_tiers_factory,
        [1, 2],  # tier IDs to alter
        new_tier_params,
    )
