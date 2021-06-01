import pytest
from brownie import (
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
def stranger(accounts):
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


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="function")
def ldo_holders(accounts, ldo_token):
    holders = accounts[-3:]
    total_supply = ldo_token.totalSupply()
    holder_balance = total_supply / 500  # 0.2 %
    for holder in holders:
        ldo_token.transfer(holder, holder_balance, {"from": constants.LDO_WHALE_HOLDER})
    return holders


@pytest.fixture(scope="module")
def dao_acl(interface):
    return interface.ACL(lido_dao_acl_address)


@pytest.fixture(scope="module")
def dao_voting(interface):
    return interface.Voting(lido_dao_voting_address)


@pytest.fixture(scope="module")
def dao_token_manager(interface):
    return interface.TokenManager(lido_dao_token_manager_address)


# Lido DAO Agent app
@pytest.fixture(scope="module")
def dao_agent(interface):
    return interface.Agent(lido_dao_agent_address)


# @pytest.fixture(scope="module")
# def ldo_token(interface):
#     return interface.ERC20(ldo_token_address)
