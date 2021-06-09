import pytest
from brownie import (
    AddRewardProgramEasyTrackExecutor,
    RemoveRewardProgramEasyTrackExecutor,
    TopUpRewardProgramEasyTrackExecutor,
    NodeOperatorsRegistryStub,
    NodeOperatorsEasyTrackExecutor,
    AragonAgentMock,
    EasyTrackExecutorStub,
    EasyTracksRegistry,
    chain,
    Wei,
    ZERO_ADDRESS,
)
import constants


@pytest.fixture(scope="function")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="function")
def stranger(accounts, ldo_token):
    balance = ldo_token.balanceOf(accounts[5])
    if balance > 0:
        ldo_token.transfer(constants.LDO_WHALE_HOLDER, balance, {"from": accounts[5]})
    return accounts[5]


@pytest.fixture(scope="function")
def aragon_agent_mock(owner):
    return owner.deploy(AragonAgentMock)


@pytest.fixture(scope="function")
def easy_tracks_registry(owner, aragon_agent_mock):
    return owner.deploy(EasyTracksRegistry, aragon_agent_mock, constants.LDO_TOKEN)


@pytest.fixture(scope="function")
def easy_track_executor_stub(owner, easy_tracks_registry):
    return owner.deploy(EasyTrackExecutorStub, easy_tracks_registry)


@pytest.fixture(scope="function")
def ldo_token(interface):
    return interface.ERC20(constants.LDO_TOKEN)


@pytest.fixture(scope="function")
def node_operators_registry_stub(owner, easy_tracks_registry):
    return owner.deploy(NodeOperatorsRegistryStub)


@pytest.fixture(scope="function")
def node_operators_easy_track_executor(
    owner,
    easy_tracks_registry,
    node_operators_registry_stub,
):
    return owner.deploy(
        NodeOperatorsEasyTrackExecutor,
        easy_tracks_registry,
        node_operators_registry_stub,
    )


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
def top_up_reward_program_easy_track_executor(owner, easy_tracks_registry):
    return owner.deploy(
        TopUpRewardProgramEasyTrackExecutor,
        easy_tracks_registry,
        owner,
        constants.FINANCE,
        constants.LDO_TOKEN,
    )


@pytest.fixture(scope="function")
def add_reward_program_easy_track_executor(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    return owner.deploy(
        AddRewardProgramEasyTrackExecutor,
        easy_tracks_registry,
        top_up_reward_program_easy_track_executor,
        owner,
    )


@pytest.fixture(scope="function")
def remove_reward_program_easy_track_executor(
    owner,
    easy_tracks_registry,
    top_up_reward_program_easy_track_executor,
):
    return owner.deploy(
        RemoveRewardProgramEasyTrackExecutor,
        easy_tracks_registry,
        top_up_reward_program_easy_track_executor,
        owner,
    )


@pytest.fixture(scope="function")
def finance(interface):
    return interface.Finance(constants.FINANCE)
