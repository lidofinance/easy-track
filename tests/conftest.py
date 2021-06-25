import pytest

from brownie import (
    MotionSettings,
    IncreaseNodeOperatorStakingLimit,
    EVMScriptFactoriesRegistry,
    EasyTrack,
    EVMScriptExecutor,
    EVMScriptCreator,
    EVMScriptPermissions,
    NodeOperatorsRegistryStub,
    AragonAgentMock,
    BytesUtils,
    EVMScriptFactoryStub,
    EVMScriptExecutorStub,
    RewardProgramsRegistry,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    TopUpLegoProgram,
)
import constants

##############
# ACCOUNTS
##############


@pytest.fixture(scope="function")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="function")
def stranger(accounts, ldo_token):
    return reset_balance(ldo_token, accounts[5])


@pytest.fixture(scope="function")
def node_operator(accounts, ldo_token):
    return accounts[4]


@pytest.fixture(scope="function")
def ldo_holders(accounts, ldo_token):
    holders = accounts[6:9]
    total_supply = ldo_token.totalSupply()
    holder_balance = total_supply / 500  # 0.2 %
    for holder in holders:
        balance = ldo_token.balanceOf(holder)
        # to make sure that holder will have exact 0.2 % of total supply of tokens
        if balance > 0:
            ldo_token.transfer(constants.LDO_WHALE_HOLDER, balance, {"from": holder})
        ldo_token.transfer(holder, holder_balance, {"from": constants.LDO_WHALE_HOLDER})
    return holders


@pytest.fixture(scope="module")
def lego_program(accounts):
    return accounts[3]


##############
# CONTRACTS
##############


@pytest.fixture(scope="function")
def motion_settings(owner):
    return owner.deploy(MotionSettings)


@pytest.fixture(scope="function")
def evm_script_factories_registry(owner):
    return owner.deploy(EVMScriptFactoriesRegistry)


@pytest.fixture(scope="function")
def easy_track(owner, ldo_token):
    return owner.deploy(EasyTrack, ldo_token)


@pytest.fixture(scope="function")
def evm_script_executor(owner, easy_track):
    return owner.deploy(EVMScriptExecutor, constants.CALLS_SCRIPT, easy_track)


@pytest.fixture(scope="function")
def reward_programs_registry(owner, evm_script_executor_stub):
    return owner.deploy(RewardProgramsRegistry, evm_script_executor_stub)


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
def top_up_reward_programs(owner, finance, ldo_token, reward_programs_registry):
    return owner.deploy(
        TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo_token
    )


@pytest.fixture(scope="function")
def top_up_lego_program(owner, finance, lego_program):
    return owner.deploy(TopUpLegoProgram, owner, finance, lego_program)


###############
# LIBRARIES
###############
@pytest.fixture(scope="module", autouse=True)
def evm_script_creator(accounts):
    return accounts[0].deploy(EVMScriptCreator)


@pytest.fixture(scope="module", autouse=True)
def evm_script_permissions(accounts):
    return accounts[0].deploy(EVMScriptPermissions)


@pytest.fixture(scope="module", autouse=True)
def bytes_utils(accounts):
    return accounts[0].deploy(BytesUtils)


############
# MOCKS
############


@pytest.fixture(scope="function")
def aragon_agent_mock(owner):
    return owner.deploy(AragonAgentMock)


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


@pytest.fixture(scope="function")
def ldo_token(interface):
    return interface.ERC20(constants.LDO_TOKEN)


@pytest.fixture(scope="function")
def steth_token(interface):
    return interface.Lido(constants.STETH_TOKEN)


@pytest.fixture(scope="function")
def node_operators_registry(interface):
    return interface.NodeOperatorsRegistry(constants.NODE_OPERATORS_REGISTRY)


@pytest.fixture(scope="function")
def voting(interface):
    return interface.Voting(constants.VOTING)


@pytest.fixture(scope="function")
def token_manager(interface):
    return interface.TokenManager(constants.TOKENS)


@pytest.fixture(scope="function")
def agent(interface):
    return interface.Agent(constants.ARAGON_AGENT)


@pytest.fixture(scope="function")
def finance(interface):
    return interface.Finance(constants.FINANCE)


#############
# INIT
#############


@pytest.fixture(scope="function", autouse=True)
def init(owner, easy_track, evm_script_executor_stub):
    easy_track.setEvmScriptExecutor(evm_script_executor_stub, {"from": owner})


# @pytest.fixture(scope="function")
# def top_up_reward_program_easy_track(owner, motions_registry_stub, finance, ldo_token):
#     return owner.deploy(
#         TopUpRewardProgramEasyTrack, motions_registry_stub, owner, finance, ldo_token
#     )


# @pytest.fixture(scope="function")
# def add_reward_program_easy_track(
#     owner, motions_registry_stub, top_up_reward_program_easy_track
# ):
#     return owner.deploy(
#         AddRewardProgramEasyTrack,
#         motions_registry_stub,
#         owner,
#         top_up_reward_program_easy_track,
#     )


# @pytest.fixture(scope="function")
# def remove_reward_program_easy_track(
#     owner, motions_registry_stub, top_up_reward_program_easy_track
# ):
#     return owner.deploy(
#         RemoveRewardProgramEasyTrack,
#         motions_registry_stub,
#         owner,
#         top_up_reward_program_easy_track,
#     )


# @pytest.fixture(scope="function")
# def lego_easy_track(owner, finance, motions_registry_stub, lego_program):
#     return owner.deploy(
#         LegoEasyTrack, motions_registry_stub, owner, finance, lego_program
#     )


def reset_balance(ldo_token, account):
    balance = ldo_token.balanceOf(account)
    if balance > 0:
        ldo_token.transfer(constants.LDO_WHALE_HOLDER, balance, {"from": account})
    return account
