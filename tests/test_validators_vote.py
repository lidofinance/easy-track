import pytest
from brownie import Wei, chain, reverts
from brownie.network.state import Chain
from brownie import accounts
from brownie import ValidatorsVote

def deploy_and_start_easy_track_vote(
        tx_params,
        ballot_time,
        objections_threshold,
        stub
        ):
    executor = ValidatorsVote.deploy(
        ballot_time,
        objections_threshold,
        stub,
        tx_params,
        # Etherscan doesn't support Vyper verification yet
        publish_source=False
        )
    # (vote_id, _) = propose_vesting_manager_contract(
    #     manager_address=executor.address,
    #     total_ldo_amount=sum(ldo_allocations),
    #     ldo_transfer_reference=f"Transfer LDO tokens to be sold for ETH",
    #     acl=interface.ACL(lido_dao_acl_address),
    #     voting=interface.Voting(lido_dao_voting_address),
    #     finance=interface.Finance(lido_dao_finance_address),
    #     token_manager=interface.TokenManager(lido_dao_token_manager_address),
    #     tx_params=tx_params
    #     )
    # return (executor, vote_id)
    return (executor, 0)

@pytest.fixture(scope='module')
def _ballot_maker(accounts):
  return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da', force=True)

@pytest.fixture(scope='module')
def _ballot_time():
  return 1

@pytest.fixture(scope='module')
def _objections_threshold():
  return 2

@pytest.fixture(scope='module')
def _stub():
  return True

@pytest.fixture(scope='module')
def deploy_executor_and_pass_easy_track_vote(
        _ballot_maker,
        _ballot_time,
        _objections_threshold,
        _stub
        ):
    def la_lambda():
      (executor, vote_id) = deploy_and_start_easy_track_vote(
          {'from': _ballot_maker}, # TODO: ACL
          ballot_time=_ballot_time,
          objections_threshold=_objections_threshold,
          stub=_stub
      )
      print(f'vote id: {vote_id}')
      # TODO: определить аккаунты, которые будут голосовать
      # Wait for the vote to end
      chain.sleep(3 * 60 * 60 * 24)
      chain.mine()
      print(f'vote executed')
      # Ret
      return executor

    return la_lambda

def test_example(deploy_executor_and_pass_easy_track_vote):
    print("DBG : test is running...")
    deploy_executor_and_pass_easy_track_vote()
    # Чтобы тест упал и я увидел отладочные сообщения
    # assert 0 == 1
    with reverts():
        accounts[0].transfer(accounts[1], "10 ether", gas_price=0)
