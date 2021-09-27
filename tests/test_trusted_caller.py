from brownie import reverts, ZERO_ADDRESS


def test_deploy_zero_address(owner, TrustedCaller):
    "Must revert with message 'TRUSTED_CALLER_IS_ZERO_ADDRESS'"
    with reverts("TRUSTED_CALLER_IS_ZERO_ADDRESS"):
        owner.deploy(TrustedCaller, ZERO_ADDRESS)


def test_deploy(owner, accounts, TrustedCaller):
    "Must deploy contract with correct params"
    trusted_caller = accounts[3]
    contract = owner.deploy(TrustedCaller, trusted_caller)
    assert contract.trustedCaller() == trusted_caller
