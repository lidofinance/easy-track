from brownie import ZERO_ADDRESS, accounts

try:
    from brownie import PurchaseExecutor, interface
except ImportError:
    print(
        "You're probably running inside Brownie console. Please call `set_console_globals`, "
        "passing `interface` and `PurchaseExecutor` global variables"
    )
    pass


def set_console_globals(**kwargs):
    global PurchaseExecutor
    global interface
    PurchaseExecutor = kwargs['PurchaseExecutor']
    interface = kwargs['interface']


from utils.dao import propose_vesting_manager_contract

from utils.config import (
    lido_dao_acl_address,
    lido_dao_voting_address,
    lido_dao_finance_address,
    lido_dao_token_manager_address
)

from purchase_config import (
    ETH_TO_LDO_RATE,
    VESTING_CLIFF_DELAY,
    VESTING_END_DELAY,
    OFFER_EXPIRATION_DELAY,
    LDO_PURCHASERS,
    ALLOCATIONS_TOTAL
)


def deploy_and_start_dao_vote(
    tx_params,
    eth_to_ldo_rate=ETH_TO_LDO_RATE,
    vesting_cliff_delay=VESTING_CLIFF_DELAY,
    vesting_end_delay=VESTING_END_DELAY,
    offer_expiration_delay=OFFER_EXPIRATION_DELAY,
    ldo_purchasers=LDO_PURCHASERS,
    allocations_total = ALLOCATIONS_TOTAL
):
    zero_padding_len = 50 - len(ldo_purchasers)
    ldo_recipients = [ p[0] for p in ldo_purchasers ] + [ZERO_ADDRESS] * zero_padding_len
    ldo_allocations = [ p[1] for p in ldo_purchasers ] + [0] * zero_padding_len

    executor = PurchaseExecutor.deploy(
        eth_to_ldo_rate,
        vesting_cliff_delay,
        vesting_end_delay,
        offer_expiration_delay,
        ldo_recipients,
        ldo_allocations,
        allocations_total,
        tx_params,
        # Etherscan doesn't support Vyper verification yet
        publish_source=False
    )

    (vote_id, _) = propose_vesting_manager_contract(
        manager_address=executor.address,
        total_ldo_amount=sum(ldo_allocations),
        ldo_transfer_reference=f"Transfer LDO tokens to be sold for ETH",
        acl=interface.ACL(lido_dao_acl_address),
        voting=interface.Voting(lido_dao_voting_address),
        finance=interface.Finance(lido_dao_finance_address),
        token_manager=interface.TokenManager(lido_dao_token_manager_address),
        tx_params=tx_params
    )

    return (executor, vote_id)
