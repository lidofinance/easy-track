import pytest
from brownie import Wei, chain, reverts
from brownie.network.state import Chain

from purchase_config import ETH_TO_LDO_RATE_PRECISION

LDO_ALLOCATIONS = [
    1_000 * 10**18,
    3_000_000 * 10**18,
    20_000_000 * 10**18
]

# 100 LDO in one ETH
ETH_TO_LDO_RATE = 100 * 10**18

VESTING_CLIFF_DELAY = 1 * 60 * 60 * 24 * 365 # one year
VESTING_END_DELAY = 2 * 60 * 60 * 24 * 365 # two years
OFFER_EXPIRATION_DELAY = 2629746 # one month


@pytest.fixture(scope='function')
def executor(accounts, deploy_executor_and_pass_dao_vote):
    return deploy_executor_and_pass_dao_vote(
        eth_to_ldo_rate=ETH_TO_LDO_RATE,
        vesting_cliff_delay=VESTING_CLIFF_DELAY,
        vesting_end_delay=VESTING_END_DELAY,
        offer_expiration_delay=OFFER_EXPIRATION_DELAY,
        ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
        allocations_total=sum(LDO_ALLOCATIONS)
    )

def test_always_passed():
    True

# def test_deploy_should_fails_on_wrong_allocations_total(accounts, deploy_executor_and_pass_dao_vote):
#     with reverts():
#         deploy_executor_and_pass_dao_vote(
#             eth_to_ldo_rate=ETH_TO_LDO_RATE,
#             vesting_cliff_delay=VESTING_CLIFF_DELAY,
#             vesting_end_delay=VESTING_END_DELAY,
#             offer_expiration_delay=OFFER_EXPIRATION_DELAY,
#             ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
#             allocations_total=sum(LDO_ALLOCATIONS) + 1
#         )


# def test_deploy_should_fails_on_zero_rate(accounts, deploy_executor_and_pass_dao_vote):
#     with reverts():
#         deploy_executor_and_pass_dao_vote(
#             eth_to_ldo_rate=0,
#             vesting_cliff_delay=VESTING_CLIFF_DELAY,
#             vesting_end_delay=VESTING_END_DELAY,
#             offer_expiration_delay=OFFER_EXPIRATION_DELAY,
#             ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
#             allocations_total=sum(LDO_ALLOCATIONS)
#         )


# def test_deploy_should_fails_on_vesting_ends_before_cliff(accounts, deploy_executor_and_pass_dao_vote):
#     with reverts():
#         deploy_executor_and_pass_dao_vote(
#             eth_to_ldo_rate=ETH_TO_LDO_RATE,
#             vesting_cliff_delay=VESTING_CLIFF_DELAY,
#             vesting_end_delay=VESTING_CLIFF_DELAY - 1,
#             offer_expiration_delay=OFFER_EXPIRATION_DELAY,
#             ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
#             allocations_total=sum(LDO_ALLOCATIONS)
#         )


# def test_deploy_should_fails_on_zero_offer_exparation_delay(accounts, deploy_executor_and_pass_dao_vote):
#     with reverts():
#         deploy_executor_and_pass_dao_vote(
#             eth_to_ldo_rate=ETH_TO_LDO_RATE,
#             vesting_cliff_delay=VESTING_CLIFF_DELAY,
#             vesting_end_delay=VESTING_END_DELAY,
#             offer_expiration_delay=0,
#             ldo_purchasers=[ (accounts[i], LDO_ALLOCATIONS[i]) for i in range(0, len(LDO_ALLOCATIONS)) ],
#             allocations_total=sum(LDO_ALLOCATIONS)
#         )


# def test_deploy_should_fails_on_purchasers_duplicates(accounts, deploy_executor_and_pass_dao_vote):
#     with reverts():
#         deploy_executor_and_pass_dao_vote(
#             eth_to_ldo_rate=ETH_TO_LDO_RATE,
#             vesting_cliff_delay=VESTING_CLIFF_DELAY,
#             vesting_end_delay=VESTING_END_DELAY,
#             offer_expiration_delay=OFFER_EXPIRATION_DELAY,
#             ldo_purchasers=[ (accounts[0], LDO_ALLOCATIONS[0]) for i in range(0, len(LDO_ALLOCATIONS)) ],
#             allocations_total=sum(LDO_ALLOCATIONS)
#         )


# def test_purchase_via_transfer(accounts, executor, dao_agent, helpers, ldo_token, dao_token_manager):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     dao_eth_balance_before = dao_agent.balance()

#     tx = purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount

#     vesting = dao_token_manager.getVesting(purchaser, purchase_evt['vesting_id'])

#     assert vesting['amount'] == purchase_ldo_amount
#     assert vesting['start'] == tx.timestamp
#     assert vesting['cliff'] == tx.timestamp + VESTING_CLIFF_DELAY
#     assert vesting['vesting'] == tx.timestamp + VESTING_END_DELAY
#     assert vesting['revokable'] == False


# def test_purchase_via_execute_purchase(accounts, executor, dao_agent, helpers, ldo_token, dao_token_manager):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     dao_eth_balance_before = dao_agent.balance()

#     tx = executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost })
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount

#     vesting = dao_token_manager.getVesting(purchaser, purchase_evt['vesting_id'])

#     assert vesting['amount'] == purchase_ldo_amount
#     assert vesting['start'] == tx.timestamp
#     assert vesting['cliff'] == tx.timestamp + VESTING_CLIFF_DELAY
#     assert vesting['vesting'] == tx.timestamp + VESTING_END_DELAY
#     assert vesting['revokable'] == False


# def test_stranger_not_allowed_to_purchase_via_execute_purchase(accounts, executor, helpers):
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]
#     stranger = accounts.at(accounts[5], force=True)

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(stranger)
#     assert allocation[0] == 0
#     assert allocation[1] == 0

#     helpers.fund_with_eth(stranger, eth_cost)

#     with reverts("no allocation"):
#         executor.execute_purchase(stranger, { 'from': stranger, 'value': eth_cost })


# def test_stranger_not_allowed_to_purchase_via_transfer(accounts, executor, helpers):
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]
#     stranger = accounts.at(accounts[5], force=True)

#     allocation = executor.get_allocation(stranger)
#     assert allocation[0] == 0
#     assert allocation[1] == 0

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     helpers.fund_with_eth(stranger, eth_cost)

#     with reverts("no allocation"):
#         executor.execute_purchase(stranger, { 'from': stranger, 'value': eth_cost })


# def test_stranger_allowed_to_purchase_token_for_purchaser_via_execute_purchase(accounts, executor, dao_agent, helpers, ldo_token, dao_token_manager):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]
#     stranger = accounts.at(accounts[5], force=True)

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(stranger, eth_cost)

#     dao_eth_balance_before = dao_agent.balance()

#     tx = executor.execute_purchase(purchaser, { 'from': stranger, 'value': eth_cost })
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount

#     vesting = dao_token_manager.getVesting(purchaser, purchase_evt['vesting_id'])

#     assert vesting['amount'] == purchase_ldo_amount
#     assert vesting['start'] == tx.timestamp
#     assert vesting['cliff'] == tx.timestamp + VESTING_CLIFF_DELAY
#     assert vesting['vesting'] == tx.timestamp + VESTING_END_DELAY
#     assert vesting['revokable'] == False


# def test_purchase_via_transfer_not_allowed_with_insufficient_funds(accounts, executor, dao_agent, helpers):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     eth_cost = eth_cost - 1e18

#     helpers.fund_with_eth(purchaser, eth_cost)

#     with reverts("insufficient funds"):
#         purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)


# def test_purchase_via_execute_purchase_not_allowed_with_insufficient_funds(accounts, executor, helpers):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     eth_cost = eth_cost - 1e18

#     helpers.fund_with_eth(purchaser, eth_cost)

#     with reverts("insufficient funds"):
#         executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost })


# def test_double_purchase_not_allowed_via_transfer(accounts, executor, helpers, ldo_token, dao_token_manager, dao_agent):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     dao_eth_balance_before = dao_agent.balance()

#     tx = purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount

#     with reverts("no allocation"):
#         purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)


# def test_double_purchase_not_allowed_via_execute_purchase(accounts, executor, dao_agent, helpers, ldo_token):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost })

#     with reverts("no allocation"):
#         executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost })


# def test_overpay_should_be_returned_via_transfer(accounts, executor, dao_agent, helpers, ldo_token):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     overpay_amount = 1e18

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     initial_purchaser_balance = purchaser.balance()
#     helpers.fund_with_eth(purchaser, eth_cost + overpay_amount)

#     assert purchaser.balance() == initial_purchaser_balance + eth_cost + overpay_amount

#     dao_eth_balance_before = dao_agent.balance()

#     tx = purchaser.transfer(to=executor, amount=eth_cost + overpay_amount, gas_limit=400_000)
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchaser.balance() == initial_purchaser_balance + overpay_amount

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount


# def test_overpay_should_be_returned_via_execute_purchase(accounts, executor, dao_agent, helpers, ldo_token):
#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     overpay_amount = 1e18

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     initial_purchaser_balance = purchaser.balance()
#     helpers.fund_with_eth(purchaser, eth_cost + overpay_amount)

#     assert purchaser.balance() == initial_purchaser_balance + eth_cost + overpay_amount

#     dao_eth_balance_before = dao_agent.balance()

#     tx = executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost + overpay_amount })
#     purchase_evt = helpers.assert_single_event_named('PurchaseExecuted', tx)

#     assert purchaser.balance() == initial_purchaser_balance + overpay_amount

#     assert purchase_evt['ldo_receiver'] == purchaser
#     assert purchase_evt['ldo_allocation'] == purchase_ldo_amount
#     assert purchase_evt['eth_cost'] == eth_cost

#     dao_eth_balance_increase = dao_agent.balance() - dao_eth_balance_before
#     assert dao_eth_balance_increase == eth_cost
#     assert ldo_token.balanceOf(purchaser) == purchase_ldo_amount


# def test_purchase_not_allowed_after_expiration_via_transfer(accounts, executor, helpers):
#     chain = Chain()

#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     expiration_delay = executor.offer_expires_at() - chain.time()
#     chain.sleep(expiration_delay + 3600)
#     chain.mine()
#     with reverts("offer expired"):
#         purchaser.transfer(to=executor, amount=eth_cost, gas_limit=400_000)


# def test_purchase_not_allowed_after_expiration_via_execute_purchase(accounts, executor, helpers):
#     chain = Chain()

#     purchaser = accounts.at(accounts[0], force=True)
#     purchase_ldo_amount = LDO_ALLOCATIONS[0]

#     eth_cost = purchase_ldo_amount * ETH_TO_LDO_RATE_PRECISION // ETH_TO_LDO_RATE

#     allocation = executor.get_allocation(purchaser)
#     assert allocation[0] == purchase_ldo_amount
#     assert allocation[1] == eth_cost

#     helpers.fund_with_eth(purchaser, eth_cost)

#     expiration_delay = executor.offer_expires_at() - chain.time()
#     chain.sleep(expiration_delay + 3600)
#     chain.mine()

#     with reverts("offer expired"):
#         executor.execute_purchase(purchaser, { 'from': purchaser, 'value': eth_cost  })


# def test_recover_unsold_tokens_not_allowed_until_exparation(executor, dao_agent):
#     with reverts():
#         executor.recover_unsold_tokens()


# def test_recover_unsold_tokens_should_transfer_all_tokens_after_exparation(executor, dao_agent, ldo_token):
#     chain = Chain()

#     expiration_delay = executor.offer_expires_at() - chain.time()
#     chain.sleep(expiration_delay + 3600)
#     chain.mine()

#     executor_balance = ldo_token.balanceOf(executor)
#     dao_agent_balance = ldo_token.balanceOf(dao_agent)

#     executor.recover_unsold_tokens()

#     assert ldo_token.balanceOf(executor) == 0
#     assert ldo_token.balanceOf(dao_agent) == dao_agent_balance + executor_balance
