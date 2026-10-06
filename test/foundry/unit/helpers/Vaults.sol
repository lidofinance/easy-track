// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {OperatorGridStub, TierParams as StubTierParams} from "contracts/test/OperatorGridStub.sol";
import {VaultHubStub} from "contracts/test/VaultHubStub.sol";

/// @notice python: lido_locator_stub of `tests/conftest.py`, with the tier params and the limits
/// the vault factory tests share
library Vaults {
    /// @dev MAX_SHARE_LIMIT of the factories that validate tier params
    uint256 internal constant MAX_TIER_SHARE_LIMIT = 10_000_000 * 1e18;

    /// @dev MAX_FEE_BP of the factories that validate fees
    uint256 internal constant MAX_FEE_BP = type(uint16).max;

    /// @dev python: lido_locator_stub. A vault hub and an operator grid on the default tier params,
    /// both administered by `admin`, under a locator that names `admin` as the vault factory, the
    /// lazy oracle and the accounting oracle
    function deployLidoLocatorStub(address admin) internal returns (LidoLocatorStub) {
        VaultHubStub vaultHub = new VaultHubStub(admin);

        // the stub declares its own `TierParams`, a twin of the one in the interface
        TierParams memory params = defaultTierParams();
        OperatorGridStub operatorGrid = new OperatorGridStub(
            admin,
            StubTierParams(
                params.shareLimit,
                params.reserveRatioBP,
                params.forcedRebalanceThresholdBP,
                params.infraFeeBP,
                params.liquidityFeeBP,
                params.reservationFeeBP
            )
        );

        return new LidoLocatorStub(address(operatorGrid), address(vaultHub), admin, admin, admin);
    }

    /// @dev python: default_tier_params, the tier the operator grid stub is deployed with
    function defaultTierParams() internal pure returns (TierParams memory) {
        return tierParams(1000, 200, 100, 50, 40, 10);
    }

    /// @dev python: a `(shareLimit, reserveRatioBP, forcedRebalanceThresholdBP, infraFeeBP,
    /// liquidityFeeBP, reservationFeeBP)` tuple
    function tierParams(
        uint256 shareLimit,
        uint256 reserveRatioBP,
        uint256 forcedRebalanceThresholdBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    ) internal pure returns (TierParams memory) {
        return TierParams({
            shareLimit: shareLimit,
            reserveRatioBP: reserveRatioBP,
            forcedRebalanceThresholdBP: forcedRebalanceThresholdBP,
            infraFeeBP: infraFeeBP,
            liquidityFeeBP: liquidityFeeBP,
            reservationFeeBP: reservationFeeBP
        });
    }
}
