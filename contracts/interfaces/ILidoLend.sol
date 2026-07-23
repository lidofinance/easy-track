// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Shared minimal interfaces of the Lido Lend protocol that the Lido Lend EasyTrack factories
///         call into. Redeclared here (not imported from lido-lend-market, which is a separate repo on a
///         different solc); kept in sync with the deployed ABIs by the factory tests.

struct MarketParams {
    address loanToken;
    address collateralToken;
    address oracle;
    address irm;
    uint256 lltv;
}

struct AdaptiveCurveParams {
    int256 curveSteepness;
    int256 adjustmentSpeed;
    int256 targetUtilization;
    int256 initialRateAtTarget;
    int256 minRateAtTarget;
    int256 maxRateAtTarget;
    uint256 maxBorrowRate;
}

interface ILidoLend {
    function marketController(bytes32 marketId) external view returns (address);

    function idToMarketParams(bytes32 marketId) external view returns (MarketParams memory);
}

interface ILidoLendOwner {
    function LIDO_LEND() external view returns (ILidoLend);

    function createMarket(
        MarketParams calldata marketParams,
        address controller,
        bool enableSettlement
    ) external;

    function setMarketSupplyCap(bytes32 marketId, uint256 cap) external;

    function unfreezeMarket(bytes32 marketId) external;

    function setMarketCollateralActivationConfig(
        bytes32 marketId,
        ILidoLendMarketController.CollateralActivationConfig calldata config
    ) external;

    function setMarketSettlementConfig(
        bytes32 marketId,
        ILidoLendMarketController.SettlementConfig calldata config
    ) external;

    function grantMarketInstantActivation(bytes32 marketId, address caller) external;

    function addGuardian(bytes32 marketId, address guardian) external;

    function removeGuardian(bytes32 marketId, address guardian) external;

    function setGuardiansQuorum(bytes32 marketId, uint256 quorum) external;

    function setGuardiansSuspectWindow(bytes32 marketId, uint256 suspectWindow) external;

    function unbanGuardianSignals(bytes32[] calldata marketIds, address account) external;
}

interface ILidoLendMarketController {
    struct CollateralActivationConfig {
        uint40 minActivationDelay;
        uint40 maxActivationDelay;
        uint128 maxDelayInflow;
        uint128 activatingLockAmount;
        uint40 activatingLockDuration;
        uint128 minActivationAmount;
        uint40 maxGuardiansQuorumDelay;
        uint40 delayPerStrike;
        uint40 delayPerSuspect;
    }

    struct SettlementConfig {
        uint16 sliceFloorBps;
        uint96 sliceFloorAssets;
        uint96 fullCutBelowCollateral;
        uint16 ltvStepBps;
    }

    function marketId() external view returns (bytes32);

    function guardianSignals() external view returns (address);

    function grantInstantActivation(address caller) external;

    function hasInstantActivation(address caller) external view returns (bool);

    function setCollateralActivationConfig(CollateralActivationConfig calldata cfg) external;

    function collateralActivationConfig() external view returns (CollateralActivationConfig memory);

    function setSettlementConfig(SettlementConfig calldata config) external;

    function settlementConfig() external view returns (SettlementConfig memory);

    function setSupplyCap(uint256 cap) external;

    function supplyCap() external view returns (uint256);

    function unfreeze() external;

    function isFrozen() external view returns (bool);
}

interface IIrmRouter {
    function setMarketIrm(MarketParams calldata marketParams, address irm) external;

    function marketIrm(bytes32 marketId) external view returns (address);
}

interface IAdaptiveCurveIrm {
    function setMarketCurveParams(
        MarketParams calldata marketParams,
        AdaptiveCurveParams calldata curveParams
    ) external;
}

interface ICircuitBreaker {
    function registerPauser(address pausable, address newPauser) external;
}

interface IGuardianSignals {
    function addGuardian(address guardian) external;

    function removeGuardian(address guardian) external;

    function isGuardian(address account) external view returns (bool);

    function getGuardianCount() external view returns (uint256);

    function getQuorum() external view returns (uint256);

    function setQuorum(uint256 newQuorum) external;

    function setSuspectWindow(uint256 suspectWindow) external;

    function getSuspectWindow() external view returns (uint256);

    function unban(bytes32 marketId, address account) external;

    function isBanned(bytes32 marketId, address account) external view returns (bool);
}

interface IRiskStewardDashboard {
    function addMarketSteward(bytes32 marketId, address steward) external;

    function removeMarketSteward(bytes32 marketId, address steward) external;

    function isMarketSteward(bytes32 marketId, address steward) external view returns (bool);
}

interface IMorphoExitBook {
    function setMarketAllowed(MarketParams calldata marketParams, bool allowed) external;
}

interface IErc4626ExitBook {
    function setVaultAllowed(address vault, bool allowed) external;
}

interface ILidoLendVault {
    function marketId() external view returns (bytes32);
}
