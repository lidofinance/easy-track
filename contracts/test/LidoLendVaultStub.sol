// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/IERC20.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/extensions/IERC20Metadata.sol";

/// @author (draft)
/// @notice Test-only stub of `LidoLendERC4626`, covering its core and market binding plus ERC-4626 deposits.
contract LidoLendVaultStub {
    bytes32 public marketId;
    address public LIDO_LEND;
    address public asset;
    uint8 public decimals = 18;
    uint256 public totalSupply;
    uint256 public totalAssets;
    uint256 private _maxDeposit = type(uint256).max;
    uint256 private _depositSharesOverride;
    mapping(address => uint256) public balanceOf;

    function setMarketId(bytes32 marketId_) external {
        marketId = marketId_;
    }

    function setLidoLend(address lidoLend_) external {
        LIDO_LEND = lidoLend_;
    }

    function setAsset(address asset_) external {
        asset = asset_;
    }

    function setDecimals(uint8 decimals_) external {
        decimals = decimals_;
    }

    function setMaxDeposit(uint256 maxDeposit_) external {
        _maxDeposit = maxDeposit_;
    }

    function setDepositSharesOverride(uint256 depositSharesOverride_) external {
        _depositSharesOverride = depositSharesOverride_;
    }

    function maxDeposit(address) external view returns (uint256) {
        return _maxDeposit;
    }

    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        shares = _depositSharesOverride == 0 ? previewDeposit(assets) : _depositSharesOverride;
        require(IERC20(asset).transferFrom(msg.sender, address(this), assets), "TRANSFER_FAILED");
        balanceOf[receiver] += shares;
        totalSupply += shares;
        totalAssets += assets;
    }

    function previewDeposit(uint256 assets) public view returns (uint256) {
        return (assets * (totalSupply + _virtualShares())) / (totalAssets + 1);
    }

    function convertToAssets(uint256 shares) external view returns (uint256) {
        return (shares * (totalAssets + 1)) / (totalSupply + _virtualShares());
    }

    function previewMint(uint256 shares) public view returns (uint256) {
        uint256 virtualShares = _virtualShares();
        return
            (shares * (totalAssets + 1) + totalSupply + virtualShares - 1) /
            (totalSupply + virtualShares);
    }

    // Mirrors the OZ ERC-4626 decimals-offset virtual shares of the real vault.
    function _virtualShares() private view returns (uint256) {
        uint8 assetDecimals = IERC20Metadata(asset).decimals();
        return decimals > assetDecimals ? 10**(decimals - assetDecimals) : 1;
    }

    function mint(uint256 shares, address receiver) external returns (uint256 assets) {
        assets = previewMint(shares);
        require(IERC20(asset).transferFrom(msg.sender, address(this), assets), "TRANSFER_FAILED");
        balanceOf[receiver] += shares;
        totalSupply += shares;
        totalAssets += assets;
    }
}
