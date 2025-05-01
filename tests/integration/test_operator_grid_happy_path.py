import pytest
import brownie

from utils.evm_script import encode_calldata

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]


def setup_operator_grid(owner, operator_grid, easy_track, agent):
    evm_executor = easy_track.evmScriptExecutor()
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), evm_executor, {"from": agent})
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), owner, {"from": agent})


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
    operator_address,
    share_limit,
    tiers_params,
):
    motion_transaction = easy_track.createMotion(
        register_group_factory.address,
        encode_calldata(["address", "uint256", "(uint256,uint256,uint256,uint256)[]"], [operator_address, share_limit, tiers_params]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    group = operator_grid.group(operator_address)
    assert group[0] == brownie.ZERO_ADDRESS  # operator
    assert group[1] == 0  # shareLimit
    assert len(group[3]) == 0  # tiersId array should be empty

    execute_motion(easy_track, motion_transaction, stranger)

    group = operator_grid.group(operator_address)
    assert group[0] == operator_address  # operator
    assert group[1] == share_limit  # shareLimit
    assert len(group[3]) == len(tiers_params)  # tiersId array should have the same length as tiers_params

    # Check tier details
    for i, tier_id in enumerate(group[3]):
        tier = operator_grid.tier(tier_id)
        assert tier[1] == tiers_params[i][0]  # shareLimit
        assert tier[3] == tiers_params[i][1]  # reserveRatioBP
        assert tier[4] == tiers_params[i][2]  # forcedRebalanceThresholdBP
        assert tier[5] == tiers_params[i][3]  # treasuryFeeBP


def create_enact_and_check_update_share_limit_motion(
    owner,
    easy_track,
    operator_grid,
    stranger,
    trusted_address,
    update_share_limit_factory,
    operator_address,
    new_share_limit,
):
    # First register the group to update
    operator_grid.registerGroup(operator_address, new_share_limit*2, {"from": owner})
    
    # Check initial state
    group = operator_grid.group(operator_address)
    assert group[1] == new_share_limit*2  # shareLimit
    
    # Create and execute motion to update share limit
    motion_transaction = easy_track.createMotion(
        update_share_limit_factory.address,
        encode_calldata(["address", "uint256"], [operator_address, new_share_limit]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    group = operator_grid.group(operator_address)
    assert group[0] == operator_address  # operator
    assert group[1] == new_share_limit  # shareLimit


def create_enact_and_check_register_tiers_motion(
    owner,
    easy_track,
    operator_grid,
    stranger,
    trusted_address,
    register_tiers_factory,
    operator_address,
    tiers_params,
):
    # First register the group to add tiers to
    operator_grid.registerGroup(operator_address, 1000, {"from": owner})
    
    # Check initial state - no tiers
    group = operator_grid.group(operator_address)
    assert len(group[3]) == 0  # tiersId array should be empty
    
    # Create and execute motion to register tiers
    motion_transaction = easy_track.createMotion(
        register_tiers_factory.address,
        encode_calldata(["address", "(uint256,uint256,uint256,uint256)[]"], [operator_address, tiers_params]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state - tiers should be registered
    group = operator_grid.group(operator_address)
    assert len(group[3]) == len(tiers_params)  # tiersId array should have the same length as tiers_params

    # Check tier details
    for i, _tier in enumerate(tiers_params):
        tier = operator_grid.tier(i+1)
        assert tier[1] == _tier[0]  # shareLimit
        assert tier[3] == _tier[1]  # reserveRatioBP
        assert tier[4] == _tier[2]  # forcedRebalanceThresholdBP
        assert tier[5] == _tier[3]  # treasuryFeeBP


def create_enact_and_check_alter_tier_motion(
    owner,
    easy_track,
    operator_grid,
    stranger,
    trusted_address,
    alter_tier_factory,
    tier_id,
    new_tier_params,
):
    # First register a group and tier to alter
    operator_address = "0x0000000000000000000000000000000000000001"
    operator_grid.registerGroup(operator_address, 1000, {"from": owner})
    initial_tier_params = [(1000, 200, 100, 50)]
    operator_grid.registerTiers(operator_address, initial_tier_params, {"from": owner})

    # Check initial state
    tier = operator_grid.tier(tier_id)
    assert tier[1] == initial_tier_params[0][0]  # shareLimit
    assert tier[3] == initial_tier_params[0][1]  # reserveRatioBP
    assert tier[4] == initial_tier_params[0][2]  # forcedRebalanceThresholdBP
    assert tier[5] == initial_tier_params[0][3]  # treasuryFeeBP

    # Create and execute motion to alter tier
    motion_transaction = easy_track.createMotion(
        alter_tier_factory.address,
        encode_calldata(["uint256", "(uint256,uint256,uint256,uint256)"], [tier_id, new_tier_params]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    execute_motion(easy_track, motion_transaction, stranger)

    # Check final state
    tier = operator_grid.tier(tier_id)
    assert tier[1] == new_tier_params[0]  # shareLimit
    assert tier[3] == new_tier_params[1]  # reserveRatioBP
    assert tier[4] == new_tier_params[2]  # forcedRebalanceThresholdBP
    assert tier[5] == new_tier_params[3]  # treasuryFeeBP


@pytest.mark.skip_coverage
def test_register_group_happy_path(
    owner,
    RegisterGroupInOperatorGrid,
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
        RegisterGroupInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    # Define tier parameters
    tiers_params = [
        (500, 200, 100, 50),  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)
        (300, 150, 75, 25),
    ]

    create_enact_and_check_register_group_motion(
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        register_group_factory,
        "0x0000000000000000000000000000000000000001",
        1000,
        tiers_params,
    )


@pytest.mark.skip_coverage
def test_update_group_share_limit_happy_path(
    owner,
    UpdateGroupShareLimitInOperatorGrid,
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
    update_share_limit_factory = setup_evm_script_factory(
        UpdateGroupShareLimitInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    create_enact_and_check_update_share_limit_motion(
        owner,
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        update_share_limit_factory,
        "0x0000000000000000000000000000000000000001",
        2000,
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

    # Define tier parameters
    tiers_params = [
        (500, 200, 100, 50),  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)
        (300, 150, 75, 25),
    ]

    create_enact_and_check_register_tiers_motion(
        owner,
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        register_tiers_factory,
        "0x0000000000000000000000000000000000000001",
        tiers_params,
    )


@pytest.mark.skip_coverage
@pytest.mark.skip(reason="operatorGrid.tiersCount() logic is not implemented yet") # TODO
def test_alter_tier_happy_path(
    owner,
    AlterTierInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    operator_grid,
    agent,
):
    setup_operator_grid(owner, operator_grid, easy_track, agent)

    permission = operator_grid.address + operator_grid.alterTier.signature[2:]
    alter_tier_factory = setup_evm_script_factory(
        AlterTierInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    # Define new tier parameters
    new_tier_params = (2000, 300, 150, 75)  # (shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, treasuryFeeBP)

    create_enact_and_check_alter_tier_motion(
        owner,
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        alter_tier_factory,
        1,  # tier ID to alter
        new_tier_params,
    )
