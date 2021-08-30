import pytest

from brownie import (
    Contract,
    ContractProxy,
    MotionSettings,
    IncreaseNodeOperatorStakingLimit,
    EVMScriptFactoriesRegistry,
    EasyTrack,
    EVMScriptExecutor,
    EVMScriptCreatorWrapper,
    NodeOperatorsRegistryStub,
    BytesUtilsWrapper,
    EVMScriptFactoryStub,
    EVMScriptExecutorStub,
    RewardProgramsRegistry,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    TopUpLegoProgram,
    EVMScriptPermissionsWrapper,
)
from utils.lido import contracts

##############
# ACCOUNTS
##############


@pytest.fixture(scope="function")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="function")
def stranger(accounts, ldo, agent):
    return reset_balance(ldo, agent, accounts[5])


@pytest.fixture(scope="function")
def node_operator(accounts, ldo):
    return accounts[4]


@pytest.fixture(scope="function")
def ldo_holders(accounts, ldo, agent):
    holders = accounts[6:9]
    total_supply = ldo.totalSupply()
    holder_balance = total_supply / 500  # 0.2 %
    for holder in holders:
        reset_balance(ldo, agent, holder)
        ldo.transfer(holder, holder_balance, {"from": agent})
    return holders


@pytest.fixture(scope="module")
def lego_program(accounts):
    return accounts[3]


##############
# CONTRACTS
##############


@pytest.fixture(scope="function")
def motion_settings(owner, voting, ldo):
    contract = owner.deploy(MotionSettings)
    contract.__EasyTrackStorage_init(ldo, voting, {"from": owner})
    return contract


@pytest.fixture(scope="function")
def evm_script_factories_registry(owner, voting, ldo):
    contract = owner.deploy(EVMScriptFactoriesRegistry)
    contract.__EasyTrackStorage_init(ldo, voting, {"from": owner})
    return contract


@pytest.fixture(scope="function")
def easy_track(owner, ldo, voting):
    contract = owner.deploy(EasyTrack)
    contract.__EasyTrackStorage_init(ldo, voting)
    return contract


@pytest.fixture(scope="function")
def evm_script_executor(owner, easy_track, calls_script):
    return owner.deploy(EVMScriptExecutor, calls_script, easy_track)


@pytest.fixture(scope="function")
def reward_programs_registry(owner, voting, evm_script_executor_stub):
    return owner.deploy(
        RewardProgramsRegistry,
        voting,
        [voting, evm_script_executor_stub],
        [voting, evm_script_executor_stub],
    )


############
# EVM SCRIPT FACTORIES
############


@pytest.fixture(scope="function")
def increase_node_operator_staking_limit(owner, node_operators_registry_stub):
    return owner.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry_stub)


@pytest.fixture(scope="function")
def add_reward_program(owner, reward_programs_registry):
    return owner.deploy(AddRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="function")
def remove_reward_program(owner, reward_programs_registry):
    return owner.deploy(RemoveRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="function")
def top_up_reward_programs(owner, finance, ldo, reward_programs_registry):
    return owner.deploy(
        TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo
    )


@pytest.fixture(scope="function")
def top_up_lego_program(owner, finance, lego_program):
    return owner.deploy(TopUpLegoProgram, owner, finance, lego_program)


############
# MOCKS AND TEST WRAPPERS
############


@pytest.fixture(scope="module")
def evm_script_creator_wrapper(accounts):
    return accounts[0].deploy(EVMScriptCreatorWrapper)


@pytest.fixture(scope="module")
def evm_script_permissions_wrapper(accounts):
    return accounts[0].deploy(EVMScriptPermissionsWrapper)


@pytest.fixture(scope="module")
def bytes_utils_wrapper(accounts):
    return accounts[0].deploy(BytesUtilsWrapper)


@pytest.fixture(scope="function")
def node_operators_registry_stub(owner, node_operator):
    return owner.deploy(NodeOperatorsRegistryStub, node_operator)


@pytest.fixture(scope="function")
def evm_script_factory_stub(owner):
    return owner.deploy(EVMScriptFactoryStub)


@pytest.fixture(scope="function")
def evm_script_executor_stub(owner):
    return owner.deploy(EVMScriptExecutorStub)


##########
# INTERFACES
##########


@pytest.fixture()
def ldo():
    return contracts()["dao"]["ldo"]


@pytest.fixture()
def steth():
    return contracts()["lido"]


@pytest.fixture()
def node_operators_registry():
    return contracts()["node_operators_registry"]


@pytest.fixture()
def voting():
    return contracts()["dao"]["voting"]


@pytest.fixture()
def tokens():
    return contracts()["dao"]["tokens"]


@pytest.fixture()
def agent():
    return contracts()["dao"]["agent"]


@pytest.fixture()
def finance():
    return contracts()["dao"]["finance"]


@pytest.fixture()
def acl():
    return contracts()["dao"]["acl"]


@pytest.fixture()
def calls_script():
    return contracts()["dao"]["calls_script"]


#############
# INIT
#############


@pytest.fixture(scope="function", autouse=True)
def init(voting, easy_track, evm_script_executor_stub):
    easy_track.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})


def reset_balance(ldo, agent, account):
    balance = ldo.balanceOf(account)
    if balance > 0:
        ldo.transfer(agent, balance, {"from": account})
    return account
