// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/IERC20.sol";

/// @author (draft)
/// @notice Test-only stub of the LidoLend core, covering market resolution, fee updates, and asset supply.
///         An unset market resolves to the zero controller / zero-`irm` params.
contract LidoLendCoreStub {
    string private constant ERROR_MARKET_ALREADY_ACTIVATED = "MARKET_ALREADY_ACTIVATED";
    string private constant ERROR_MARKET_NOT_CREATED = "MARKET_NOT_CREATED";
    string private constant ERROR_ALREADY_SET = "ALREADY_SET";
    string private constant ERROR_NOT_OWNER = "NOT_OWNER";

    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    struct Market {
        uint128 totalSupplyAssets;
        uint128 totalSupplyShares;
        uint128 totalBorrowAssets;
        uint128 totalBorrowShares;
        uint128 lastUpdate;
        uint128 fee;
    }

    mapping(bytes32 => address) public marketController;
    mapping(bytes32 => MarketParams) private _idToMarketParams;
    mapping(bytes32 => Market) private _market;
    mapping(bytes32 => bool) public isSettlementEnabled;
    address public owner;
    mapping(bytes32 => mapping(address => uint256)) public supplyShares;

    function setOwner(address owner_) external {
        owner = owner_;
    }

    function setMarketController(bytes32 marketId, address controller) external {
        marketController[marketId] = controller;
    }

    function setMarketParams(bytes32 marketId, MarketParams calldata marketParams) external {
        _idToMarketParams[marketId] = marketParams;
    }

    function idToMarketParams(bytes32 marketId) external view returns (MarketParams memory) {
        return _idToMarketParams[marketId];
    }

    function market(bytes32 marketId) external view returns (Market memory) {
        return _market[marketId];
    }

    function accrueInterest(MarketParams calldata) external {}

    function supply(
        MarketParams calldata marketParams,
        uint256 assets,
        uint256 shares,
        address onBehalf,
        bytes calldata
    ) external returns (uint256, uint256) {
        bytes32 marketId = keccak256(abi.encode(marketParams));
        require(_market[marketId].lastUpdate != 0, ERROR_MARKET_NOT_CREATED);
        require((assets == 0) != (shares == 0), "INCONSISTENT_INPUT");

        Market storage market_ = _market[marketId];
        if (assets == 0) {
            uint256 denominator = uint256(market_.totalSupplyShares) + 1e6;
            assets =
                (shares * (uint256(market_.totalSupplyAssets) + 1) + denominator - 1) /
                denominator;
        } else {
            shares =
                (assets * (uint256(market_.totalSupplyShares) + 1e6)) /
                (uint256(market_.totalSupplyAssets) + 1);
        }
        require(
            IERC20(marketParams.loanToken).transferFrom(msg.sender, address(this), assets),
            "TRANSFER_FAILED"
        );
        market_.totalSupplyAssets += uint128(assets);
        market_.totalSupplyShares += uint128(shares);
        supplyShares[marketId][onBehalf] += shares;
        return (assets, shares);
    }

    function setFee(MarketParams calldata marketParams, uint256 newFee) external {
        require(msg.sender == owner, ERROR_NOT_OWNER);
        bytes32 marketId = keccak256(abi.encode(marketParams));
        require(_market[marketId].lastUpdate != 0, ERROR_MARKET_NOT_CREATED);
        require(_market[marketId].fee != newFee, ERROR_ALREADY_SET);
        _market[marketId].fee = uint128(newFee);
    }

    function activateMarket(
        bytes32 marketId,
        MarketParams calldata marketParams,
        bool settlementEnabled
    ) external {
        require(_market[marketId].lastUpdate == 0, ERROR_MARKET_ALREADY_ACTIVATED);
        _idToMarketParams[marketId] = marketParams;
        _market[marketId].lastUpdate = uint128(block.timestamp == 0 ? 1 : block.timestamp);
        isSettlementEnabled[marketId] = settlementEnabled;
    }
}
