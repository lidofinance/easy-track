import pytest
from brownie import Wei, chain, reverts
from brownie.network.state import Chain
from brownie import accounts
from brownie import ValidatorsVote


# @pytest.fixture(scope='function')
# def executor(accounts, deploy_executor_and_pass_dao_vote):
#     return deploy_executor_and_pass_dao_vote(
#     ...
#     )

# def test_always_passed():
#     return True

def deploy_validators_vote():
    executor = ValidatorsVote.deploy(1,1,True, {'from': accounts[0]})
    return executor

def test_account_balance():
    print("DBG : test is running...")
    deploy_validators_vote()
    # ValidatorsVote.deploy()
    # balance = accounts[0].balance()
    # print(balance)
    # print(type(accounts[0]))
    # accounts[0].transfer(accounts[1], "10 ether", gas_price=10)
    # print(balance)
    with reverts():
        accounts[0].transfer(accounts[1], "10 ether", gas_price=0)

    # accounts[0].transfer(accounts[1], "10 ether", gas_price=0)
    # assert balance - "10 ether" == accounts[0].balance()

# def test_deploy_should_fails_on_something(accounts, deploy_executor_and_pass_dao_vote_2):
#     print("DBG : test_deploy_should_fails_on_something running...")
#     with reverts():
#         # deploy_easy_track_and_start(
#         deploy_executor_and_pass_dao_vote_2()
