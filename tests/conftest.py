import pytest
from brownie import EasyTrackExecutorStub, EasyTracksRegistry, chain, Wei, ZERO_ADDRESS
import constants


@pytest.fixture(scope="function")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="function")
def stranger(accounts):
    return accounts[-1]


@pytest.fixture(scope="function")
def easy_tracks_registry(owner):
    return owner.deploy(EasyTracksRegistry, constants.ARAGON_AGENT)


@pytest.fixture(scope="function")
def easy_track_executor_stub(owner, easy_tracks_registry):
    return owner.deploy(EasyTrackExecutorStub, easy_tracks_registry)


@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope="module")
def ldo_holder(accounts):
    return accounts.at("0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da", force=True)


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


@pytest.fixture(scope="module")
def ldo_token(interface):
    return interface.ERC20(ldo_token_address)
