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
    return lido_contracts.ldo


@pytest.fixture(scope="module")
def steth(lido_contracts):
    return lido_contracts.steth


@pytest.fixture(scope="module")
def node_operators_registry(lido_contracts):
    return lido_contracts.node_operators_registry


@pytest.fixture(scope="module")
def voting(lido_contracts):
    return lido_contracts.aragon.voting


@pytest.fixture(scope="module")
def tokens(lido_contracts):
    return lido_contracts.aragon.token_manager


@pytest.fixture(scope="module")
def agent(lido_contracts):
    return lido_contracts.aragon.agent


@pytest.fixture(scope="module")
def finance(lido_contracts):
    return lido_contracts.aragon.finance


@pytest.fixture(scope="module")
def acl(lido_contracts):
    return lido_contracts.aragon.acl


@pytest.fixture(scope="module")
def calls_script(lido_contracts):
    return lido_contracts.aragon.calls_script


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


############################
# Helper/Functional Fixtures
############################

# NOTE: the function returned can modify state, but the factory fixture itself shouldn't


@pytest.fixture(scope="module")
def fund_with_ldo(ldo, agent):
    # NOTE: module scope because it depends on ldo, agent
    # but the fixture doesn't change state when executed - only returns a function

    def method(account, amount):
        ldo.transfer(account, amount, {"from": agent})

    return method
