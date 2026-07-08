// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `LidoLendMarketController` (lido-lend-market/src/controllers/LidoLendMarketController.sol),
/// covering only the surface the collateral-activation, settlement-config, supply-cap, and unfreeze factories
/// call into.
contract LidoLendMarketControllerStub {
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

    CollateralActivationConfig private _activationConfig;
    SettlementConfig private _settlementConfig;
    uint256 public supplyCap;
    bool public isFrozen;
    mapping(address => bool) public hasInstantActivation;
    address public guardianSignals;
    bytes32 public marketId;

    function setGuardianSignals(address registry) external {
        guardianSignals = registry;
    }

    function setMarketId(bytes32 marketId_) external {
        marketId = marketId_;
    }

    function grantInstantActivation(address caller) external {
        hasInstantActivation[caller] = true;
    }

    function setFrozen(bool value) external {
        isFrozen = value;
    }

    function unfreeze() external {
        isFrozen = false;
    }

    function setCollateralActivationConfig(CollateralActivationConfig calldata cfg) external {
        _activationConfig = cfg;
    }

    function collateralActivationConfig() external view returns (CollateralActivationConfig memory) {
        return _activationConfig;
    }

    function setSettlementConfig(SettlementConfig calldata config) external {
        _settlementConfig = config;
    }

    function settlementConfig() external view returns (SettlementConfig memory) {
        return _settlementConfig;
    }

    function setSupplyCap(uint256 cap) external {
        supplyCap = cap;
    }
}
