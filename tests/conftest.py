import pytest
import brownie

import constants
from utils.lido import contracts
from utils import test_helpers

brownie.web3.enable_strict_bytes_type_checking()

####################################
# Brownie Blockchain State Snapshots
####################################

# autouse, so enabled by default for all test modules in this directory


@pytest.fixture(scope="module", autouse=True)
def mod_isolation(module_isolation):
    """Snapshot ganache at start of module."""
    pass


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    """Snapshot ganache before every test function call."""
    pass


##############
# CONSTANTS
##############


@pytest.fixture(scope="module")
def holder_balance_amount(ldo):
    """Amount initially distributed to LDO holder accounts."""
    # By having this as a separate fixture, we can override it in
    # lower levels to change the amount distributed to holders
    # without having to modify the `distribute_holder_balance` fixture
    total_supply = ldo.totalSupply()
    holder_balance = total_supply / 500  # 0.2 %
    return holder_balance


##############
# ACCOUNTS
##############


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[5]


@pytest.fixture(scope="session")
def node_operator(accounts):
    return accounts[4]


@pytest.fixture(scope="session")
def ldo_holders(accounts):
    holders = accounts[6:9]
    return holders


@pytest.fixture(scope="session")
def lego_program(accounts):
    return accounts[3]


##############
# CONTRACTS
##############


@pytest.fixture(scope="module")
def lido_contracts():
    # Have this as a fixture to cache the result.
    return contracts()


@pytest.fixture(scope="module")
def motion_settings(owner, MotionSettings):
    return owner.deploy(
        MotionSettings,
        owner,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )


@pytest.fixture(scope="module")
def evm_script_factories_registry(owner, EVMScriptFactoriesRegistry):
    return owner.deploy(EVMScriptFactoriesRegistry, owner)


@pytest.fixture(scope="module")
def easy_track(owner, ldo, voting, evm_script_executor_stub, EasyTrack):
    contract = owner.deploy(
        EasyTrack,
        ldo,
        voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    contract.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})
    return contract


@pytest.fixture(scope="module")
def evm_script_executor(owner, easy_track, calls_script, EVMScriptExecutor):
    return owner.deploy(EVMScriptExecutor, calls_script, easy_track)


@pytest.fixture(scope="module")
def reward_programs_registry(
    owner, voting, evm_script_executor_stub, RewardProgramsRegistry
):
    return owner.deploy(
        RewardProgramsRegistry,
        voting,
        [voting, evm_script_executor_stub],
        [voting, evm_script_executor_stub],
    )


############
# EVM SCRIPT FACTORIES
############


@pytest.fixture(scope="module")
def increase_node_operator_staking_limit(
    owner, node_operators_registry_stub, IncreaseNodeOperatorStakingLimit
):
    return owner.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry_stub)


@pytest.fixture(scope="module")
def add_reward_program(owner, reward_programs_registry, AddRewardProgram):
    return owner.deploy(AddRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="module")
def remove_reward_program(owner, reward_programs_registry, RemoveRewardProgram):
    return owner.deploy(RemoveRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="module")
def top_up_reward_programs(
    owner, finance, ldo, reward_programs_registry, TopUpRewardPrograms
):
    return owner.deploy(
        TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo
    )


@pytest.fixture(scope="module")
def top_up_lego_program(owner, finance, lego_program, TopUpLegoProgram):
    return owner.deploy(TopUpLegoProgram, owner, finance, lego_program)


############
# MOCKS AND TEST WRAPPERS
############


@pytest.fixture(scope="module")
def evm_script_creator_wrapper(accounts, EVMScriptCreatorWrapper):
    return accounts[0].deploy(EVMScriptCreatorWrapper)


@pytest.fixture(scope="module")
def evm_script_permissions_wrapper(accounts, EVMScriptPermissionsWrapper):
    return accounts[0].deploy(EVMScriptPermissionsWrapper)


@pytest.fixture(scope="module")
def bytes_utils_wrapper(accounts, BytesUtilsWrapper):
    return accounts[0].deploy(BytesUtilsWrapper)


@pytest.fixture(scope="module")
def node_operators_registry_stub(owner, node_operator, NodeOperatorsRegistryStub):
    return owner.deploy(NodeOperatorsRegistryStub, node_operator)


@pytest.fixture(scope="module")
def evm_script_factory_stub(owner, EVMScriptFactoryStub):
    return owner.deploy(EVMScriptFactoryStub)


@pytest.fixture(scope="module")
def evm_script_executor_stub(owner, EVMScriptExecutorStub):
    return owner.deploy(EVMScriptExecutorStub)


##########
# INTERFACES
##########


@pytest.fixture(scope="module")
def ldo(lido_contracts):
    return lido_contracts["dao"]["ldo"]


@pytest.fixture(scope="module")
def steth(lido_contracts):
    return lido_contracts["lido"]


@pytest.fixture(scope="module")
def node_operators_registry(lido_contracts):
    return lido_contracts["node_operators_registry"]


@pytest.fixture(scope="module")
def voting(lido_contracts):
    return lido_contracts["dao"]["voting"]


@pytest.fixture(scope="module")
def tokens(lido_contracts):
    return lido_contracts["dao"]["tokens"]


@pytest.fixture(scope="module")
def agent(lido_contracts):
    return lido_contracts["dao"]["agent"]


@pytest.fixture(scope="module")
def finance(lido_contracts):
    return lido_contracts["dao"]["finance"]


@pytest.fixture(scope="module")
def acl(lido_contracts):
    return lido_contracts["dao"]["acl"]


@pytest.fixture(scope="module")
def calls_script(lido_contracts):
    return lido_contracts["dao"]["calls_script"]


###################
# Grouping Fixtures
###################

# Can be useful if you want to do some test over "all lido contracts"
# And makes it easier to depend on a group of related fixtures


@pytest.fixture(scope="module")
def all_interfaces(
    ldo,
    steth,
    node_operators_registry,
    voting,
    tokens,
    agent,
    finance,
    acl,
    calls_script,
):
    return (
        ldo,
        steth,
        node_operators_registry,
        voting,
        tokens,
        agent,
        finance,
        acl,
        calls_script,
    )


@pytest.fixture(scope="module")
def all_mocks_and_wrappers(
    evm_script_creator_wrapper,
    evm_script_permissions_wrapper,
    bytes_utils_wrapper,
    node_operators_registry_stub,
    evm_script_factory_stub,
    evm_script_executor_stub,
):
    return (
        evm_script_creator_wrapper,
        evm_script_permissions_wrapper,
        bytes_utils_wrapper,
        node_operators_registry_stub,
        evm_script_factory_stub,
        evm_script_executor_stub,
    )


@pytest.fixture(scope="module")
def all_evm_script_factories(
    increase_node_operator_staking_limit,
    add_reward_program,
    remove_reward_program,
    top_up_reward_programs,
    top_up_lego_program,
):
    return (
        increase_node_operator_staking_limit,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs,
        top_up_lego_program,
    )


@pytest.fixture(scope="module")
def all_easy_track_contracts(
    motion_settings,
    evm_script_factories_registry,
    easy_track,
    evm_script_executor,
    reward_programs_registry,
):
    return (
        motion_settings,
        evm_script_factories_registry,
        easy_track,
        evm_script_executor,
        reward_programs_registry,
    )


#########################
# State Changing Fixtures
#########################

# Non-deployment fixtures with side-effects
# Have them module scoped if you want the changes to persist across tests within a module
# Or function scoped for their changes to be rolled-back after test execution


@pytest.fixture(scope="function")
def distribute_holder_balance(ldo_holders, holder_balance_amount, fund_with_ldo):
    for holder in ldo_holders:
        fund_with_ldo(holder, holder_balance_amount)


@pytest.fixture(scope="module")
def set_easy_track_executor(voting, easy_track, evm_script_executor_stub):
    easy_track.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})


# TODO probably want a register factories one here, so the "standard_init"
# has the factories added to easy_track

############################
# Helper/Functional Fixtures
############################

# NOTE: the function returned can modify state, but the factory fixture itself shouldn't

# Use as wide a scoping as possible (e.g. session) as the fixtures should be "pure" where possible,
# not relying on any module or function-scoped state
# Saves from re-running the fixture more than once


@pytest.fixture(scope="session")
def reset_balance():
    # Or named "zero_ldo_balance"

    # More an example, because this no longer needs to be done to undo changes after test execution
    def method(ldo, agent, account):
        balance = ldo.balanceOf(account)
        if balance > 0:
            ldo.transfer(agent, balance, {"from": account})
        return account

    return method


@pytest.fixture(scope="module")
def fund_with_ldo(ldo, agent):
    # NOTE: module scope because it depends on ldo, agent
    # but the fixture doesn't change state when executed - only returns a function

    def method(account, amount):
        ldo.transfer(account, amount, {"from": agent})

    return method


@pytest.fixture(scope="session")
def access_controll_revert_message():
    # Personal(?) preference to have test helpers as fixtures, so it's clear when looking at a test
    # whether a helper was used in there or not
    # Also allows overriding
    return test_helpers.access_controll_revert_message


#############
# INIT
#############


@pytest.fixture(scope="module")
def standard_init(
    all_easy_track_contracts,
    set_easy_track_executor,
    distribute_holder_balance,
    lido_contracts,
):
    """Depend on this to have a "standard" initial state that mimics the real-world deployment."""
    # NOTE: I still prefer to avoid a "global" "conftest-level" autouse here,
    # and to instead have a autouse in the relevant test modules
    # So test modules that want an alternative setup or don't need the full setup can
    # choose to not have it
    pass


@pytest.fixture()
def init():
    # Just to override/remove the autouse fixture for tests in this directory
    pass


####################
# Pytest Adjustments
####################

# Allows you to mark tests as slow, and only run them if `--runslow` is provided
# Copied from https://docs.pytest.org/en/latest/example/simple.html?highlight=skip#control-skipping-of-tests-according-to-command-line-option

# @pytest.mark.slow
# def test_slow_example():
#    pass


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
