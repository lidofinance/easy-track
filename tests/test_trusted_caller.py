from brownie import reverts, ZERO_ADDRESS
from utils.hardhat_helpers import get_last_block_revert_reason


def test_deploy_zero_address(owner, TrustedCaller):
    "Must revert with message 'TRUSTED_CALLER_IS_ZERO_ADDRESS'"
    revert_reason = "TRUSTED_CALLER_IS_ZERO_ADDRESS"
    try:
        with reverts(revert_reason):
            owner.deploy(TrustedCaller, ZERO_ADDRESS)
    except Exception as e:
        if isinstance(e, ValueError) and "is not a valid ETH address" in str(e):
            assert revert_reason == get_last_block_revert_reason()
        else:
            raise e

def test_deploy(owner, accounts, TrustedCaller):
    "Must deploy contract with correct params"
    trusted_caller = accounts[3]
    contract = owner.deploy(TrustedCaller, trusted_caller)
    assert contract.trustedCaller() == trusted_caller
