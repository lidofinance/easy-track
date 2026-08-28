// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/utils/SafeERC20.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Holds externally funded loan tokens to preseed Lido Lend markets and their vaults
/// @dev Minted shares are locked at PRESEED_RECIPIENT forever; unspent funds are recoverable
///      by an ERC20_RECOVERER via recoverERC20
contract LidoLendPreseeder is AccessControl {
    using SafeERC20 for IERC20;

    bytes32 public constant ERC20_RECOVERER = keccak256("ERC20_RECOVERER");
    bytes32 public constant EXECUTOR_ROLE = keccak256("EXECUTOR_ROLE");

    /// @notice Emitted when ERC20 tokens are recovered from this contract
    /// @param token Address of the recovered ERC20 token
    /// @param recipient Address that received the tokens
    /// @param amount Amount of tokens transferred
    event ERC20Recovered(address indexed token, address indexed recipient, uint256 amount);

    /// @notice Thrown when the recovery recipient is the zero address
    error ZeroRecipient();

    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_VAULT_SHARES_TOO_LOW = "VAULT_SHARES_TOO_LOW";
    string private constant ERROR_MARKET_NOT_EMPTY = "MARKET_NOT_EMPTY";
    string private constant ERROR_MARKET_ID_MISMATCH = "MARKET_ID_MISMATCH";
    string private constant ERROR_LIDO_LEND_MISMATCH = "LIDO_LEND_MISMATCH";
    string private constant ERROR_VAULT_ASSET_MISMATCH = "VAULT_ASSET_MISMATCH";
    string private constant ERROR_VAULT_NOT_EMPTY = "VAULT_NOT_EMPTY";
    string private constant ERROR_INSUFFICIENT_ASSET_BALANCE = "INSUFFICIENT_ASSET_BALANCE";
    string private constant ERROR_PRESEED_EXCEEDS_MAX_DEPOSIT = "PRESEED_EXCEEDS_MAX_DEPOSIT";

    uint256 private constant MARKET_VIRTUAL_SHARES = 1e6;
    uint256 private constant MIN_DEAD_DEPOSIT_SHARES = 1e9;
    uint256 private constant MIN_VAULT_ASSET_UNITS = 1e6;

    /// @notice Unrecoverable holder of the preseeded market and vault shares
    address public constant PRESEED_RECIPIENT = address(0xdead);

    /// @notice Address of the LidoLend core
    ILidoLend public immutable lidoLend;

    /// @notice Sets the immutable core and initial access-control roles
    /// @param _lidoLend Address of the LidoLend core
    /// @param _evmScriptExecutor Initial holder of EXECUTOR_ROLE
    /// @param _recoverer Initial holder of DEFAULT_ADMIN_ROLE and ERC20_RECOVERER
    constructor(
        ILidoLend _lidoLend,
        address _evmScriptExecutor,
        address _recoverer
    ) {
        require(address(_lidoLend) != address(0), "ZERO_LIDO_LEND");
        require(_evmScriptExecutor != address(0), "ZERO_EVM_SCRIPT_EXECUTOR");
        require(_recoverer != address(0), "ZERO_RECOVERER");
        lidoLend = _lidoLend;
        _setupRole(DEFAULT_ADMIN_ROLE, _recoverer);
        _setupRole(EXECUTOR_ROLE, _evmScriptExecutor);
        _setupRole(ERC20_RECOVERER, _recoverer);
    }

    /// @notice Returns the loan token amounts preseedMarket will spend on the market and the vault
    /// @dev Assumes an empty market and an empty vault, as preseedMarket requires
    /// @param vault ERC-4626 wrapper of the market to be preseeded
    /// @return marketSupplyAssets Loan tokens supplied to the market for MIN_DEAD_DEPOSIT_SHARES shares
    /// @return vaultAssets Loan tokens deposited into the vault (share and asset dust floors apply)
    function previewPreseed(ILidoLendERC4626 vault)
        public
        view
        returns (uint256 marketSupplyAssets, uint256 vaultAssets)
    {
        marketSupplyAssets = (MIN_DEAD_DEPOSIT_SHARES - 1) / MARKET_VIRTUAL_SHARES + 1;
        vaultAssets = vault.previewMint(MIN_DEAD_DEPOSIT_SHARES);
        if (vaultAssets < MIN_VAULT_ASSET_UNITS) {
            vaultAssets = MIN_VAULT_ASSET_UNITS;
        }
    }

    /// @notice Validates that the market, the vault, and this contract's balance allow preseeding
    /// @dev Reverts with the matching reason on any violation. Covers every preseedMarket
    ///      precondition, so factories can call it before the market is created: a not-yet-created
    ///      market reads as empty, and its existence at preseed time is enforced by the core
    /// @param marketParams Params of the market to be preseeded
    /// @param vault ERC-4626 wrapper of the market, must be empty and share its loan token
    function validatePreseed(MarketParams calldata marketParams, ILidoLendERC4626 vault)
        public
        view
    {
        require(address(vault) != address(0), ERROR_ZERO_VAULT);
        require(vault.LIDO_LEND() == lidoLend, ERROR_LIDO_LEND_MISMATCH);
        bytes32 marketId = keccak256(abi.encode(marketParams));
        require(vault.marketId() == marketId, ERROR_MARKET_ID_MISMATCH);
        Market memory market_ = lidoLend.market(marketId);
        require(
            market_.totalSupplyAssets == 0 && market_.totalSupplyShares == 0,
            ERROR_MARKET_NOT_EMPTY
        );
        require(vault.totalSupply() == 0, ERROR_VAULT_NOT_EMPTY);
        require(vault.asset() == marketParams.loanToken, ERROR_VAULT_ASSET_MISMATCH);

        (uint256 marketSupplyAssets, uint256 vaultAssets) = previewPreseed(vault);
        uint256 requiredAssets = marketSupplyAssets + vaultAssets;
        require(
            vault.maxDeposit(PRESEED_RECIPIENT) >= requiredAssets,
            ERROR_PRESEED_EXCEEDS_MAX_DEPOSIT
        );
        require(
            IERC20(marketParams.loanToken).balanceOf(address(this)) >= requiredAssets,
            ERROR_INSUFFICIENT_ASSET_BALANCE
        );
    }

    /// @notice Preseeds a just-created empty market and its empty vault with dust shares locked
    ///         at PRESEED_RECIPIENT
    /// @dev Only callable by an EXECUTOR_ROLE holder. Pays with loan tokens held by this
    ///      contract; guards against share-inflation attacks. Amounts are computed internally:
    ///      see previewPreseed. Market existence is enforced by the core's supply call
    /// @param marketParams Params of the created, still-empty market
    /// @param vault ERC-4626 wrapper of the market, must be empty and share its loan token
    function preseedMarket(MarketParams calldata marketParams, ILidoLendERC4626 vault)
        external
        onlyRole(EXECUTOR_ROLE)
    {
        validatePreseed(marketParams, vault);

        address loanToken = marketParams.loanToken;
        (uint256 marketSupplyAssets, uint256 vaultAssets) = previewPreseed(vault);

        IERC20(loanToken).safeIncreaseAllowance(address(lidoLend), marketSupplyAssets);
        lidoLend.supply(marketParams, 0, MIN_DEAD_DEPOSIT_SHARES, PRESEED_RECIPIENT, "");

        uint256 requiredVaultShares = vault.previewDeposit(MIN_VAULT_ASSET_UNITS);
        if (requiredVaultShares < MIN_DEAD_DEPOSIT_SHARES) {
            requiredVaultShares = MIN_DEAD_DEPOSIT_SHARES;
        }
        IERC20(loanToken).safeIncreaseAllowance(address(vault), vaultAssets);
        uint256 vaultShares = vault.deposit(vaultAssets, PRESEED_RECIPIENT);
        require(vaultShares >= requiredVaultShares, ERROR_VAULT_SHARES_TOO_LOW);
    }

    /// @notice Transfers ERC20 tokens held by this contract to the recipient
    /// @dev Only callable by an ERC20_RECOVERER holder
    /// @param token Address of the ERC20 token to recover
    /// @param recipient Address to receive the tokens
    /// @param amount Amount of tokens to transfer
    function recoverERC20(
        address token,
        address recipient,
        uint256 amount
    ) external onlyRole(ERC20_RECOVERER) {
        if (recipient == address(0)) revert ZeroRecipient();
        IERC20(token).safeTransfer(recipient, amount);
        emit ERC20Recovered(token, recipient, amount);
    }
}
