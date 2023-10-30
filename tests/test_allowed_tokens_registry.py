import pytest

from brownie import reverts, ZERO_ADDRESS, MockERC20, accounts

from utils.test_helpers import (
    access_revert_message,
    DEFAULT_ADMIN_ROLE,
    ADD_TOKEN_TO_ALLOWED_LIST_ROLE,
    REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE,
)

# ------------
# constructor
# ------------


def test_registry_initial_state(AllowedTokensRegistry, accounts, owner):
    add_token_role_holder = accounts[6]
    remove_token_role_holder = accounts[7]

    registry = owner.deploy(
        AllowedTokensRegistry,
        owner,
        [add_token_role_holder],
        [remove_token_role_holder],
    )

    assert registry.hasRole(DEFAULT_ADMIN_ROLE, owner)

    assert registry.hasRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, add_token_role_holder)
    assert registry.hasRole(
        REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, remove_token_role_holder
    )

    for role_holder in [add_token_role_holder, remove_token_role_holder]:
        assert not registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), role_holder)

    assert len(registry.getAllowedTokens()) == 0


def test_registry_zero_admin_allowed(AllowedTokensRegistry, owner):
    """Checking no revert"""
    owner.deploy(AllowedTokensRegistry, ZERO_ADDRESS, [owner], [owner])


def test_registry_none_role_holders_allowed(AllowedTokensRegistry, owner):
    """Checking no revert"""
    owner.deploy(AllowedTokensRegistry, owner, [], [])


# ------------
# access control
# ------------


def test_rights_are_not_shared_by_different_roles(
    AllowedTokensRegistry,
    owner,
    stranger,
    voting,
    ldo,
    accounts,
):
    deployer = owner
    add_role_holder = accounts[6]
    remove_role_holder = accounts[7]

    registry = deployer.deploy(
        AllowedTokensRegistry, voting, [add_role_holder], [remove_role_holder]
    )
    assert registry.hasRole(registry.DEFAULT_ADMIN_ROLE(), voting)

    for caller in [
        deployer,
        remove_role_holder,
        stranger,
    ]:
        with reverts(access_revert_message(caller, ADD_TOKEN_TO_ALLOWED_LIST_ROLE)):
            registry.addToken(ldo, {"from": caller})

    for caller in [
        deployer,
        add_role_holder,
        stranger,
    ]:
        with reverts(
            access_revert_message(caller, REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE)
        ):
            registry.removeToken(ldo, {"from": caller})


def test_multiple_role_holders(
    AllowedTokensRegistry, owner, voting, accounts, ldo, steth
):
    deployer = owner
    add_role_holders = (accounts[2], accounts[3])
    remove_role_holders = (accounts[4], accounts[5])

    registry = deployer.deploy(
        AllowedTokensRegistry, voting, add_role_holders, remove_role_holders
    )

    for caller in accounts:
        if not caller in add_role_holders:
            with reverts(access_revert_message(caller, ADD_TOKEN_TO_ALLOWED_LIST_ROLE)):
                registry.addToken(ldo, {"from": caller})

    registry.addToken(ldo, {"from": add_role_holders[0]})
    registry.addToken(steth, {"from": add_role_holders[1]})

    for caller in accounts:
        if not caller in remove_role_holders:
            with reverts(
                access_revert_message(caller, REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE)
            ):
                registry.removeToken(ldo, {"from": caller})

    registry.removeToken(ldo, {"from": remove_role_holders[0]})
    registry.removeToken(steth, {"from": remove_role_holders[1]})


# ------------
# logic
# ------------



def test_add_tokens(allowed_tokens_registry, ldo):
    (registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_role_holder})

    assert registry.isTokenAllowed(ldo)
    assert len(registry.getAllowedTokens()) == 1
    assert registry.getAllowedTokens()[0] == ldo


def test_add_multiple_tokens(allowed_tokens_registry, ldo, steth):
    (registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_role_holder})
    registry.addToken(steth, {"from": add_token_role_holder})

    assert registry.isTokenAllowed(ldo)
    assert registry.isTokenAllowed(steth)
    assert len(registry.getAllowedTokens()) == 2
    assert registry.getAllowedTokens()[0] == ldo
    assert registry.getAllowedTokens()[1] == steth


def test_add_zero_token(allowed_tokens_registry):
    (registry, _, add_token_role_holder, _) = allowed_tokens_registry

    with reverts("TOKEN_ADDRESS_IS_ZERO"):
        registry.addToken(ZERO_ADDRESS, {"from": add_token_role_holder})


def test_add_the_same_token(allowed_tokens_registry, ldo):
    (registry, _, add_token_role_holder, _) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_role_holder})

    with reverts("TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST"):
        registry.addToken(ldo, {"from": add_token_role_holder})


def test_remove_token(allowed_tokens_registry, ldo):
    (registry, _, add_token_holder, remove_token_role_holder) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_holder})

    assert registry.isTokenAllowed(ldo)
    assert len(registry.getAllowedTokens()) == 1

    registry.removeToken(ldo, {"from": remove_token_role_holder})

    assert not registry.isTokenAllowed(ldo)
    assert len(registry.getAllowedTokens()) == 0


def test_remove_multiple_tokens(allowed_tokens_registry, ldo, steth):
    (registry, _, add_token_holder, remove_token_role_holder) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_holder})
    registry.addToken(steth, {"from": add_token_holder})

    assert registry.isTokenAllowed(ldo)
    assert registry.isTokenAllowed(steth)
    assert len(registry.getAllowedTokens()) == 2

    registry.removeToken(ldo, {"from": remove_token_role_holder})

    assert not registry.isTokenAllowed(ldo)
    assert registry.isTokenAllowed(steth)
    assert len(registry.getAllowedTokens()) == 1

    registry.removeToken(steth, {"from": remove_token_role_holder})

    assert not registry.isTokenAllowed(ldo)
    assert not registry.isTokenAllowed(steth)
    assert len(registry.getAllowedTokens()) == 0


def test_remove_the_same_token(allowed_tokens_registry, ldo):
    (registry, _, add_token_holder, remove_token_role_holder) = allowed_tokens_registry

    registry.addToken(ldo, {"from": add_token_holder})

    assert registry.isTokenAllowed(ldo)
    assert len(registry.getAllowedTokens()) == 1

    registry.removeToken(ldo, {"from": remove_token_role_holder})

    assert not registry.isTokenAllowed(ldo)
    assert len(registry.getAllowedTokens()) == 0

    with reverts("TOKEN_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeToken(ldo, {"from": remove_token_role_holder})


def test_remove_not_existing_token(allowed_tokens_registry, ldo):
    (registry, _, _, remove_token_role_holder) = allowed_tokens_registry

    with reverts("TOKEN_NOT_FOUND_IN_ALLOWED_LIST"):
        registry.removeToken(ldo, {"from": remove_token_role_holder})


def test_normalize_amount(allowed_tokens_registry):
    (registry, _, _, _) = allowed_tokens_registry

    erc20decimals18 = MockERC20.deploy(18, {"from": accounts[0]})

    with reverts("TOKEN_ADDRESS_IS_ZERO"):
        registry.normalizeAmount(1, ZERO_ADDRESS)

    
    amount1 = 1000000000000000999
    assert registry.normalizeAmount(amount1, erc20decimals18) == amount1

    erc20decimals21 = MockERC20.deploy(21, {"from": accounts[0]})
    amount2 = 1000000000000000999000
    assert registry.normalizeAmount(amount2, erc20decimals21) == amount1
    assert registry.normalizeAmount(amount2 + 1, erc20decimals21) == amount1 + 1

    erc20decimals12 = MockERC20.deploy(12, {"from": accounts[0]})
    amount3 = 1000000000009
    assert registry.normalizeAmount(amount3, erc20decimals12) == 1000000000009000000
