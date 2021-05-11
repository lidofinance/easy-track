import pytest
from brownie import Wei, chain, reverts
from brownie.network.state import Chain
from brownie import accounts
from brownie import ValidatorsVote

def deploy_and_start_easy_track_vote(
        tx_params,
        ballot_maker,
        ballot_time,
        objections_threshold,
        stub
        ):
    # Deploy EasyTrack
    executor = ValidatorsVote.deploy(
        ballot_time,
        objections_threshold,
        stub,
        tx_params,
        )
    # Add BallotMaker
    executor.add_ballot_maker(ballot_maker, tx_params)
    tx = executor.make_ballot(
        1,
        tx_params
        )
    # Debug out
    tx.info()
    # Get vote_id
    vote_id = tx.events['EasyTrackVoteStart']['ballotId']
    # Ret
    return (executor, vote_id)

@pytest.fixture(scope='module')
def fx_ballot_maker(accounts):
  return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da', force=True)

@pytest.fixture(scope='module')
def fx_ballot_time():
  return 1

@pytest.fixture(scope='module')
def fx_objections_threshold():
  return 2

@pytest.fixture(scope='module')
def fx_stub():
  return True

@pytest.fixture(scope='module')
def deploy_executor_and_pass_easy_track_vote(
        fx_ballot_maker,
        fx_ballot_time,
        fx_objections_threshold,
        fx_stub
        ):
    def la_lambda():
      (executor, vote_id) = deploy_and_start_easy_track_vote(
          {'from': fx_ballot_maker}, # TODO: ACL
          ballot_maker=fx_ballot_maker,
          ballot_time=fx_ballot_time,
          objections_threshold=fx_objections_threshold,
          stub=fx_stub
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

def test_nor(deploy_executor_and_pass_easy_track_vote):
    print("TEST : NOR is running...")
    executor = deploy_executor_and_pass_easy_track_vote()
    print("test^output:")
    print(executor.is_node_op(0x5)) # stub id
    # Чтобы тест упал и я увидел отладочные сообщения
    # assert 0 == 1
    with reverts():
        accounts[0].transfer(accounts[1], "10 ether", gas_price=0)
    # print("TEST: NOR {res}")
