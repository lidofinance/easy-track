import pytest
import brownie

from utils.evm_script import encode_calldata

MOTION_BUFFER_TIME = 100


@pytest.fixture(scope="module")
def trusted_address(accounts):
    return accounts[7]


# TODO - use real address of operator grid when it will be deployed
@pytest.fixture(scope="module", autouse=True)
def operator_grid(owner, OperatorGridStub, easy_track):
    operator_grid = owner.deploy(OperatorGridStub, owner)
    evm_executor = easy_track.evmScriptExecutor()
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), evm_executor, {"from": owner})
    operator_grid.grantRole(operator_grid.REGISTRY_ROLE(), owner, {"from": owner})
    return operator_grid


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
):
    motion_transaction = easy_track.createMotion(
        register_group_factory.address,
        encode_calldata(["address", "uint256"], [operator_address, share_limit]),
        {"from": trusted_address},
    )
    motions = easy_track.getMotions()
    assert len(motions) == 1

    group = operator_grid.group(operator_address)
    assert group[0] == 0 # shareLimit
    assert group[2] == brownie.ZERO_ADDRESS # operator

    execute_motion(easy_track, motion_transaction, stranger)

    group = operator_grid.group(operator_address)
    assert group[0] == share_limit # shareLimit
    assert group[2] == operator_address # operator


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
    assert group[0] == new_share_limit*2  # shareLimit
    
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
    assert group[0] == new_share_limit  # shareLimit
    assert group[2] == operator_address  # operator


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
    tiers = operator_grid.getTiers()
    for i, tier in enumerate(tiers_params):
        assert tiers[i+1][0] == tier[0]  # shareLimit
        assert tiers[i+1][2] == tier[1]  # reserveRatioBP
        assert tiers[i+1][3] == tier[2]  # rebalanceThresholdBP
        assert tiers[i+1][4] == tier[3]  # treasuryFeeBP


@pytest.mark.skip_coverage
def test_register_group_happy_path(
    RegisterGroupInOperatorGrid,
    easy_track,
    trusted_address,
    voting,
    deployer,
    stranger,
    operator_grid,
):
    permission = operator_grid.address + operator_grid.registerGroup.signature[2:]
    register_group_factory = setup_evm_script_factory(
        RegisterGroupInOperatorGrid,
        permission,
        easy_track,
        trusted_address,
        voting,
        deployer,
        operator_grid,
    )

    create_enact_and_check_register_group_motion(
        easy_track,
        operator_grid,
        stranger,
        trusted_address,
        register_group_factory,
        "0x0000000000000000000000000000000000000001",
        1000,
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
):
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
):
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
        (500, 100, 50, 10),  # (shareLimit, reserveRatioBP, rebalanceThresholdBP, treasuryFeeBP)
        (300, 80, 40, 8),
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
