// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `RiskStewardDashboard` (lido-lend-market/src/periphery/RiskStewardDashboard.sol),
/// covering only the steward-management surface the risk-steward factories call into.
contract RiskStewardDashboardStub {
    mapping(bytes32 => mapping(address => bool)) public isMarketSteward;

    function setMarketSteward(bytes32 marketId, address steward, bool value) external {
        isMarketSteward[marketId][steward] = value;
    }

    function addMarketSteward(bytes32 marketId, address steward) external {
        isMarketSteward[marketId][steward] = true;
    }

    function removeMarketSteward(bytes32 marketId, address steward) external {
        isMarketSteward[marketId][steward] = false;
    }
}
