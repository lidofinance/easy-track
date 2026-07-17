// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

struct OwnerStubMarketParams {
    address loanToken;
    address collateralToken;
    address oracle;
    address irm;
    uint256 lltv;
}

interface ILidoLendCoreLikeForOwnerStub {
    function activateMarket(bytes32 marketId, OwnerStubMarketParams calldata marketParams, bool settlementEnabled)
        external;
}

interface IIrmProbe {
    function borrowRate(OwnerStubMarketParams calldata marketParams) external view returns (uint256);
}

/// @author (draft)
/// @notice Test-only stub of `LidoLendOwner` (lido-lend-market/src/periphery/LidoLendOwner.sol),
/// covering only the two-arg `createMarket` overload `LidoLendActivateMarket` calls into. It is
/// MARKET_CREATOR_ROLE-gated (so an executor lacking the role is caught) and reproduces the real
/// `createMarket`'s first `borrowRate` ping, which reverts unless the market was routed and its curve
/// params set first — enforcing the mandatory activation order.
contract LidoLendOwnerStub {
    bytes32 public constant MARKET_CREATOR_ROLE = keccak256("MARKET_CREATOR_ROLE");

    OwnerStubMarketParams public lastMarketParams;
    address public lastController;
    bool public lastEnableSettlement;
    bool public called;
    address public core;
    mapping(bytes32 => mapping(address => bool)) public hasRole;

    function setCore(address core_) external {
        core = core_;
    }

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function createMarket(OwnerStubMarketParams calldata marketParams, address controller, bool enableSettlement)
        external
    {
        require(hasRole[MARKET_CREATOR_ROLE][msg.sender], "NOT_MARKET_CREATOR");
        lastMarketParams = marketParams;
        lastController = controller;
        lastEnableSettlement = enableSettlement;
        called = true;
        if (core != address(0)) {
            ILidoLendCoreLikeForOwnerStub(core).activateMarket(
                keccak256(abi.encode(marketParams)), marketParams, enableSettlement
            );
        }
        // Mirror the real createMarket's first borrowRate ping (LidoLend.sol): reverts if the market's IRM
        // is unrouted or its curve params are unset. This is what makes the activation order mandatory —
        // setMarketCurveParams and setMarketIrm must both precede createMarket.
        if (marketParams.irm != address(0)) {
            IIrmProbe(marketParams.irm).borrowRate(marketParams);
        }
    }
}
