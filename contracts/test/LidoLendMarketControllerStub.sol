// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of `LidoLendMarketController` (lido-lend-market/src/controllers/LidoLendMarketController.sol),
/// covering only the surface the collateral-activation, settlement-config, supply-cap, and unfreeze factories
/// call into.
contract LidoLendMarketControllerStub {
    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    bytes32 public constant UNFREEZER_ROLE = keccak256("UNFREEZER_ROLE");
    bytes32 public constant FREEZER_ROLE = keccak256("FREEZER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");

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
    mapping(bytes32 => mapping(address => bool)) public hasRole;
    bool public enforceRoles;
    address public guardianSignals;
    bytes32 public marketId;

    modifier onlyRoleWhenEnforced(bytes32 role) {
        require(!enforceRoles || hasRole[role][msg.sender], "CONTROLLER_MISSING_ROLE");
        _;
    }

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function setEnforceRoles(bool value) external {
        enforceRoles = value;
    }

    function setGuardianSignals(address registry) external {
        guardianSignals = registry;
    }

    function setMarketId(bytes32 marketId_) external {
        marketId = marketId_;
    }

    function grantInstantActivation(address caller) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        hasInstantActivation[caller] = true;
    }

    function setFrozen(bool value) external {
        isFrozen = value;
    }

    function freeze() external onlyRoleWhenEnforced(FREEZER_ROLE) {
        isFrozen = true;
    }

    function unfreeze() external onlyRoleWhenEnforced(UNFREEZER_ROLE) {
        isFrozen = false;
    }

    function setCollateralActivationConfig(CollateralActivationConfig calldata cfg)
        external
        onlyRoleWhenEnforced(MANAGER_ROLE)
    {
        _activationConfig = cfg;
    }

    function collateralActivationConfig() external view returns (CollateralActivationConfig memory) {
        return _activationConfig;
    }

    function setSettlementConfig(SettlementConfig calldata config) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        _settlementConfig = config;
    }

    function settlementConfig() external view returns (SettlementConfig memory) {
        return _settlementConfig;
    }

    function setSupplyCap(uint256 cap) external onlyRoleWhenEnforced(MANAGER_ROLE) {
        supplyCap = cap;
    }
}
