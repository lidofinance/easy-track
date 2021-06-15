import pytest
from brownie import (
    LegoEasyTrack,
    MotionsRegistryStub,
    RemoveRewardProgramEasyTrack,
    NodeOperatorsEasyTrack,
    MotionsRegistry,
    AddRewardProgramEasyTrack,
    TopUpRewardProgramEasyTrack,
    NodeOperatorsRegistryStub,
    AragonAgentMock,
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
    return reset_balance(ldo_token, accounts[5])


@pytest.fixture(scope="function")
def node_operator(accounts, ldo_token):
    return accounts[4]


@pytest.fixture(scope="function")
def aragon_agent_mock(owner):
    return owner.deploy(AragonAgentMock)


@pytest.fixture(scope="function")
def easy_tracks_registry(owner):
    return owner.deploy(EasyTracksRegistry)


@pytest.fixture(scope="function")
def motions_registry(owner, aragon_agent_mock, ldo_token, easy_tracks_registry):
    return owner.deploy(
        MotionsRegistry, easy_tracks_registry, ldo_token, aragon_agent_mock
    )


@pytest.fixture(scope="function")
def motions_registry_stub(owner):
    return owner.deploy(MotionsRegistryStub)


@pytest.fixture(scope="function")
def ldo_token(interface):
    return interface.ERC20(constants.LDO_TOKEN)


@pytest.fixture(scope="function")
def steth_token(interface):
    return interface.Lido(constants.STETH_TOKEN)


@pytest.fixture(scope="function")
def node_operators_registry_stub(owner, easy_tracks_registry, node_operator):
    return owner.deploy(NodeOperatorsRegistryStub, node_operator)


@pytest.fixture(scope="function")
def node_operators_easy_track(
    owner, motions_registry_stub, node_operators_registry_stub
):
    return owner.deploy(
        NodeOperatorsEasyTrack, motions_registry_stub, node_operators_registry_stub
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
def top_up_reward_program_easy_track(owner, motions_registry_stub, finance, ldo_token):
    return owner.deploy(
        TopUpRewardProgramEasyTrack, motions_registry_stub, owner, finance, ldo_token
    )


@pytest.fixture(scope="function")
def add_reward_program_easy_track(
    owner, motions_registry_stub, top_up_reward_program_easy_track
):
    return owner.deploy(
        AddRewardProgramEasyTrack,
        motions_registry_stub,
        owner,
        top_up_reward_program_easy_track,
    )


@pytest.fixture(scope="function")
def remove_reward_program_easy_track(
    owner, motions_registry_stub, top_up_reward_program_easy_track
):
    return owner.deploy(
        RemoveRewardProgramEasyTrack,
        motions_registry_stub,
        owner,
        top_up_reward_program_easy_track,
    )


@pytest.fixture(scope="module")
def lego_program(accounts):
    return accounts[3]


@pytest.fixture(scope="function")
def lego_easy_track(owner, finance, motions_registry_stub, lego_program):
    return owner.deploy(
        LegoEasyTrack, motions_registry_stub, owner, finance, lego_program
    )


@pytest.fixture(scope="function")
def finance(interface):
    return interface.Finance(constants.FINANCE)


def reset_balance(ldo_token, account):
    balance = ldo_token.balanceOf(account)
    if balance > 0:
        ldo_token.transfer(constants.LDO_WHALE_HOLDER, balance, {"from": account})
    return account
