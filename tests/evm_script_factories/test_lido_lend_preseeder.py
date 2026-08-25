import pytest
from brownie import (
    ZERO_ADDRESS,
    LidoLendCoreStub,
    LidoLendPreseeder,
    LidoLendVaultStub,
    MockERC20,
    reverts,
    web3,
)
from eth_abi import encode
from utils.hardhat_helpers import get_last_tx_revert_reason


MIN_DEAD_DEPOSIT_SHARES = 10**9
MIN_VAULT_ASSET_UNITS = 10**6
MARKET_SUPPLY_ASSETS = (MIN_DEAD_DEPOSIT_SHARES + 10**6 - 1) // 10**6
DEAD_ADDRESS = "0x000000000000000000000000000000000000dEaD"


@pytest.fixture(scope="module")
def loan_token(owner):
    return MockERC20.deploy(18, {"from": owner})


@pytest.fixture(scope="module")
def collateral_token(owner):
    return MockERC20.deploy(18, {"from": owner})


@pytest.fixture(scope="module")
def market_params(loan_token, collateral_token, accounts):
    return (loan_token.address, collateral_token.address, accounts[7].address, accounts[8].address, 8 * 10**17)


@pytest.fixture(scope="module")
def market_id(market_params):
    return web3.keccak(encode(["address", "address", "address", "address", "uint256"], market_params))


@pytest.fixture(scope="module")
def core(owner, market_id, market_params):
    core = LidoLendCoreStub.deploy({"from": owner})
    core.activateMarket(market_id, market_params, False, {"from": owner})
    return core


@pytest.fixture(scope="module")
def vault(owner, core, market_id, loan_token):
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setLidoLend(core, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    return vault


@pytest.fixture(scope="module")
def recoverer(accounts):
    return accounts[9]


@pytest.fixture(scope="module")
def preseeder(owner, core, evm_script_executor_stub, recoverer):
    return LidoLendPreseeder.deploy(core, evm_script_executor_stub, recoverer, {"from": owner})


def test_deploy(core, evm_script_executor_stub, recoverer, preseeder):
    assert preseeder.lidoLend() == core
    assert preseeder.evmScriptExecutor() == evm_script_executor_stub
    assert preseeder.recoverer() == recoverer
    assert preseeder.PRESEED_RECIPIENT() == DEAD_ADDRESS


def test_constructor_rejects_zero_addresses(owner, core, evm_script_executor_stub, recoverer):
    for expected_reason, lido_lend, executor, recoverer_ in (
        ("ZERO_LIDO_LEND", ZERO_ADDRESS, evm_script_executor_stub, recoverer),
        ("ZERO_EVM_SCRIPT_EXECUTOR", core, ZERO_ADDRESS, recoverer),
        ("ZERO_RECOVERER", core, evm_script_executor_stub, ZERO_ADDRESS),
    ):
        try:
            with reverts(expected_reason):
                LidoLendPreseeder.deploy(lido_lend, executor, recoverer_, {"from": owner})
        except Exception as error:
            if expected_reason != get_last_tx_revert_reason():
                raise error


def test_only_executor_can_preseed_market(stranger, preseeder, market_params, vault):
    with reverts("CALLER_IS_FORBIDDEN"):
        preseeder.preseedMarket(market_params, vault, {"from": stranger})


def test_preview_preseed(preseeder, vault):
    # 18/18-decimals empty vault: dead shares convert 1:1 to assets
    assert preseeder.previewPreseed(vault) == (MARKET_SUPPLY_ASSETS, MIN_DEAD_DEPOSIT_SHARES)


def test_validate_preseed_checks_funding(owner, loan_token, preseeder, market_params, vault):
    with reverts("INSUFFICIENT_ASSET_BALANCE"):
        preseeder.validatePreseed(market_params, vault)

    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    loan_token.mint(preseeder, market_supply_assets + vault_assets, {"from": owner})
    preseeder.validatePreseed(market_params, vault)


def test_rejects_insufficient_balance(owner, evm_script_executor_stub, loan_token, preseeder, market_params, vault):
    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    loan_token.mint(preseeder, market_supply_assets + vault_assets - 1, {"from": owner})
    with reverts("INSUFFICIENT_ASSET_BALANCE"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_rejects_nonempty_market(
    owner,
    evm_script_executor_stub,
    loan_token,
    market_params,
    core,
    preseeder,
    vault,
):
    loan_token.mint(owner, 1, {"from": owner})
    loan_token.approve(core, 1, {"from": owner})
    core.supply(market_params, 1, 0, owner, b"", {"from": owner})

    with reverts("MARKET_NOT_EMPTY"):
        preseeder.validatePreseed(market_params, vault)
    with reverts("MARKET_NOT_EMPTY"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_validate_preseed_passes_for_uncreated_market(preseeder, owner, loan_token, market_params, core, vault):
    "A not-yet-created market reads as empty, so factories can validate before createMarket runs."
    uncreated_params = (market_params[0], market_params[1], market_params[2], market_params[3], 7 * 10**17)
    vault.setMarketId(web3.keccak(encode(["address", "address", "address", "address", "uint256"], uncreated_params)), {"from": owner})
    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    loan_token.mint(preseeder, market_supply_assets + vault_assets, {"from": owner})

    preseeder.validatePreseed(uncreated_params, vault)


def test_rejects_nonempty_vault(owner, evm_script_executor_stub, loan_token, preseeder, market_params, vault):
    loan_token.mint(owner, 1, {"from": owner})
    loan_token.approve(vault, 1, {"from": owner})
    vault.mint(1, owner, {"from": owner})

    with reverts("VAULT_NOT_EMPTY"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_preseed_market(owner, evm_script_executor_stub, loan_token, core, vault, preseeder, market_params, market_id):
    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    loan_token.mint(preseeder, market_supply_assets + vault_assets, {"from": owner})

    preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})

    assert core.supplyShares(market_id, DEAD_ADDRESS) == MIN_DEAD_DEPOSIT_SHARES
    assert vault.balanceOf(DEAD_ADDRESS) >= MIN_DEAD_DEPOSIT_SHARES
    assert vault.convertToAssets(vault.balanceOf(DEAD_ADDRESS)) >= MIN_VAULT_ASSET_UNITS
    assert loan_token.balanceOf(preseeder) == 0
    assert loan_token.balanceOf(core) == market_supply_assets
    assert loan_token.balanceOf(vault) == vault_assets
    assert loan_token.allowance(preseeder, core) == 0
    assert loan_token.allowance(preseeder, vault) == 0


def test_preseed_market_keeps_excess_balance(
    owner,
    evm_script_executor_stub,
    loan_token,
    preseeder,
    market_params,
    vault,
):
    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    excess = 12345
    loan_token.mint(preseeder, market_supply_assets + vault_assets + excess, {"from": owner})

    preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})

    assert loan_token.balanceOf(preseeder) == excess


def test_preseed_market_supports_approve_without_return_value(
    owner,
    evm_script_executor_stub,
    loan_token,
    core,
    vault,
    preseeder,
    market_params,
    market_id,
):
    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    loan_token.mint(preseeder, market_supply_assets + vault_assets, {"from": owner})
    loan_token.setApproveReturnsNoData(True, {"from": owner})

    preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})

    assert core.supplyShares(market_id, DEAD_ADDRESS) == MIN_DEAD_DEPOSIT_SHARES
    assert vault.balanceOf(DEAD_ADDRESS) >= MIN_DEAD_DEPOSIT_SHARES


@pytest.mark.parametrize(
    "asset_decimals,vault_decimals,expected_vault_assets",
    [(18, 18, 10**9), (8, 18, 10**6), (6, 18, 10**6), (6, 16, 10**6)],
)
def test_preseed_amounts_follow_vault_decimals_offset(
    owner,
    accounts,
    evm_script_executor_stub,
    recoverer,
    asset_decimals,
    vault_decimals,
    expected_vault_assets,
):
    loan_token = MockERC20.deploy(asset_decimals, {"from": owner})
    collateral_token = MockERC20.deploy(18, {"from": owner})
    market_params = (
        loan_token.address,
        collateral_token.address,
        accounts[6].address,
        accounts[7].address,
        8 * 10**17,
    )
    market_id = web3.keccak(encode(["address", "address", "address", "address", "uint256"], market_params))
    core = LidoLendCoreStub.deploy({"from": owner})
    core.activateMarket(market_id, market_params, False, {"from": owner})
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setLidoLend(core, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    vault.setDecimals(vault_decimals, {"from": owner})
    preseeder = LidoLendPreseeder.deploy(core, evm_script_executor_stub, recoverer, {"from": owner})

    market_supply_assets, vault_assets = preseeder.previewPreseed(vault)
    assert market_supply_assets == MARKET_SUPPLY_ASSETS
    assert vault_assets == expected_vault_assets

    loan_token.mint(preseeder, market_supply_assets + vault_assets, {"from": owner})
    preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})

    assert vault.balanceOf(DEAD_ADDRESS) >= MIN_DEAD_DEPOSIT_SHARES
    assert vault.convertToAssets(vault.balanceOf(DEAD_ADDRESS)) >= MIN_VAULT_ASSET_UNITS
    assert loan_token.balanceOf(preseeder) == 0


def test_rejects_foreign_vault(owner, evm_script_executor_stub, market_params, market_id, loan_token, preseeder):
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setLidoLend(owner, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    with reverts("LIDO_LEND_MISMATCH"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_rejects_vault_for_another_market(owner, evm_script_executor_stub, core, market_params, loan_token, preseeder):
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setLidoLend(core, {"from": owner})
    vault.setMarketId((123).to_bytes(32, "big"), {"from": owner})
    vault.setAsset(loan_token, {"from": owner})
    with reverts("MARKET_ID_MISMATCH"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_rejects_vault_with_wrong_asset(
    owner,
    evm_script_executor_stub,
    core,
    market_params,
    market_id,
    collateral_token,
    preseeder,
):
    vault = LidoLendVaultStub.deploy({"from": owner})
    vault.setLidoLend(core, {"from": owner})
    vault.setMarketId(market_id, {"from": owner})
    vault.setAsset(collateral_token, {"from": owner})
    with reverts("VAULT_ASSET_MISMATCH"):
        preseeder.preseedMarket(market_params, vault, {"from": evm_script_executor_stub})


def test_rejects_zero_vault(evm_script_executor_stub, preseeder, market_params):
    with reverts("ZERO_VAULT"):
        preseeder.preseedMarket(market_params, ZERO_ADDRESS, {"from": evm_script_executor_stub})


def test_recover_erc20(owner, recoverer, stranger, loan_token, preseeder):
    loan_token.mint(preseeder, 1000, {"from": owner})

    tx = preseeder.recoverERC20(loan_token, stranger, 600, {"from": recoverer})

    assert loan_token.balanceOf(stranger) == 600
    assert loan_token.balanceOf(preseeder) == 400
    assert tx.events["ERC20Recovered"] == {"token": loan_token, "recipient": stranger, "amount": 600}


def test_only_recoverer_can_recover_erc20(owner, stranger, evm_script_executor_stub, loan_token, preseeder):
    loan_token.mint(preseeder, 1000, {"from": owner})
    for caller in (stranger, evm_script_executor_stub):
        with reverts("CALLER_IS_FORBIDDEN"):
            preseeder.recoverERC20(loan_token, stranger, 1000, {"from": caller})


def test_recover_erc20_rejects_zero_recipient(owner, recoverer, loan_token, preseeder):
    loan_token.mint(preseeder, 1000, {"from": owner})
    with reverts():
        preseeder.recoverERC20(loan_token, ZERO_ADDRESS, 1000, {"from": recoverer})
