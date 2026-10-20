// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ILidoLend.sol";

interface ILidoLendCoreLikeForOwnerStub {
    function activateMarket(
        bytes32 marketId,
        MarketParams calldata marketParams,
        bool settlementEnabled
    ) external;

    function marketController(bytes32 marketId) external view returns (address);

    function setFee(MarketParams calldata marketParams, uint256 newFee) external;
}

interface IIrmProbe {
    function borrowRate(MarketParams calldata marketParams) external view returns (uint256);
}

/// @dev Controller setters the real LidoLendOwner forwards to; the factories never call them directly,
///      so they are not part of ILidoLendMarketController anymore and are redeclared here for the stub.
interface IControllerLikeForOwnerStub {
    function setSupplyCap(uint256 cap) external;

    function unfreeze() external;

    function setCollateralActivationConfig(
        ILidoLendMarketController.CollateralActivationConfig calldata cfg
    ) external;

    function setSettlementConfig(ILidoLendMarketController.SettlementConfig calldata config)
        external;

    function setInstantActivation(address caller, bool enabled) external;
}

/// @author (draft)
/// @notice Test-only stub of `LidoLendOwner` (lido-lend-market/src/periphery/LidoLendOwner.sol). Covers the
/// two-arg `createMarket` overload `LidoLendActivateMarket` calls into, plus the marketId-parameterized market-
/// and guardian-management facade the domain-scoped factories now route through: each resolves the per-market
/// controller (or its GuardianSignals registry) via the core and forwards. `createMarket` is
/// MARKET_CREATOR_ROLE-gated (so an executor lacking the role is caught) and reproduces the real createMarket's
/// first `borrowRate` ping. Scenario fixtures enable role enforcement so the stub reproduces the production
/// executor -> facade -> market-contract authorization path; unit tests may leave it disabled.
contract LidoLendOwnerStub {
    bytes32 public constant MARKET_CREATOR_ROLE = keccak256("MARKET_CREATOR_ROLE");
    bytes32 public constant MARKET_MANAGER_ROLE = keccak256("MARKET_MANAGER_ROLE");
    bytes32 public constant GUARDIAN_MANAGER_ROLE = keccak256("GUARDIAN_MANAGER_ROLE");
    bytes32 public constant FEE_MANAGER_ROLE = keccak256("FEE_MANAGER_ROLE");

    MarketParams public lastMarketParams;
    address public lastController;
    bool public lastEnableSettlement;
    bool public called;
    address public core;
    bool public enforceRoles;
    mapping(bytes32 => mapping(address => bool)) public hasRole;

    modifier onlyRoleWhenEnforced(bytes32 role) {
        require(!enforceRoles || hasRole[role][msg.sender], "OWNER_MISSING_ROLE");
        _;
    }

    function setCore(address core_) external {
        core = core_;
    }

    function setEnforceRoles(bool value) external {
        enforceRoles = value;
    }

    /// @notice Mirrors the real facade's immutable `LIDO_LEND` getter (factories derive the core from it).
    function LIDO_LEND() external view returns (address) {
        return core;
    }

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function createMarket(
        MarketParams calldata marketParams,
        address controller,
        bool enableSettlement
    ) external {
        require(hasRole[MARKET_CREATOR_ROLE][msg.sender], "NOT_MARKET_CREATOR");
        lastMarketParams = marketParams;
        lastController = controller;
        lastEnableSettlement = enableSettlement;
        called = true;
        if (core != address(0)) {
            ILidoLendCoreLikeForOwnerStub(core).activateMarket(
                keccak256(abi.encode(marketParams)),
                marketParams,
                enableSettlement
            );
        }
        // Mirror the real createMarket's first borrowRate ping (LidoLend.sol): reverts if the market's IRM
        // is unrouted or its curve params are unset. This is what makes the activation order mandatory —
        // applyIrmConfig and setMarketIrm must both precede createMarket.
        if (marketParams.irm != address(0)) {
            IIrmProbe(marketParams.irm).borrowRate(marketParams);
        }
    }

    function setFee(MarketParams calldata marketParams, uint256 newFee)
        external
        onlyRoleWhenEnforced(FEE_MANAGER_ROLE)
    {
        ILidoLendCoreLikeForOwnerStub(core).setFee(marketParams, newFee);
    }

    // ---
    // MARKET MANAGEMENT (resolve controller by id, forward)
    // ---

    function setMarketSupplyCap(bytes32 marketId, uint256 cap)
        external
        onlyRoleWhenEnforced(MARKET_MANAGER_ROLE)
    {
        IControllerLikeForOwnerStub(_controllerOf(marketId)).setSupplyCap(cap);
    }

    function unfreezeMarket(bytes32 marketId) external onlyRoleWhenEnforced(MARKET_MANAGER_ROLE) {
        IControllerLikeForOwnerStub(_controllerOf(marketId)).unfreeze();
    }

    function setMarketCollateralActivationConfig(
        bytes32 marketId,
        ILidoLendMarketController.CollateralActivationConfig calldata config
    ) external onlyRoleWhenEnforced(MARKET_MANAGER_ROLE) {
        IControllerLikeForOwnerStub(_controllerOf(marketId)).setCollateralActivationConfig(config);
    }

    function setMarketSettlementConfig(
        bytes32 marketId,
        ILidoLendMarketController.SettlementConfig calldata config
    ) external onlyRoleWhenEnforced(MARKET_MANAGER_ROLE) {
        IControllerLikeForOwnerStub(_controllerOf(marketId)).setSettlementConfig(config);
    }

    function setInstantActivation(
        bytes32 marketId,
        address caller,
        bool enabled
    ) external onlyRoleWhenEnforced(MARKET_MANAGER_ROLE) {
        IControllerLikeForOwnerStub(_controllerOf(marketId)).setInstantActivation(caller, enabled);
    }

    // ---
    // GUARDIAN MANAGEMENT (resolve the market's GuardianSignals registry by id, forward)
    // ---

    function addGuardian(bytes32 marketId, address guardian)
        external
        onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE)
    {
        IGuardianSignals(_guardianSignalsOf(marketId)).addGuardian(guardian);
    }

    function replaceGuardian(
        bytes32 marketId,
        address oldGuardian,
        address newGuardian
    ) external onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE) {
        IGuardianSignals guardians = IGuardianSignals(_guardianSignalsOf(marketId));
        uint256 guardianCount = guardians.getGuardianCount();

        if (guardianCount < guardians.MAX_GUARDIANS_COUNT()) {
            guardians.addGuardian(newGuardian);
            guardians.removeGuardian(oldGuardian);
            return;
        }

        uint256 quorum = guardians.getQuorum();
        bool restoreQuorum = quorum == guardianCount;
        if (restoreQuorum) guardians.setQuorum(quorum - 1);
        guardians.removeGuardian(oldGuardian);
        guardians.addGuardian(newGuardian);
        if (restoreQuorum) guardians.setQuorum(quorum);
    }

    function removeGuardian(bytes32 marketId, address guardian)
        external
        onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE)
    {
        IGuardianSignals(_guardianSignalsOf(marketId)).removeGuardian(guardian);
    }

    function setGuardiansQuorum(bytes32 marketId, uint256 quorum)
        external
        onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE)
    {
        IGuardianSignals(_guardianSignalsOf(marketId)).setQuorum(quorum);
    }

    function setGuardiansSuspectWindow(bytes32 marketId, uint256 suspectWindow)
        external
        onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE)
    {
        IGuardianSignals(_guardianSignalsOf(marketId)).setSuspectWindow(suspectWindow);
    }

    function unbanGuardianSignals(bytes32[] calldata marketIds, address account)
        external
        onlyRoleWhenEnforced(GUARDIAN_MANAGER_ROLE)
    {
        for (uint256 i = 0; i < marketIds.length; ++i) {
            IGuardianSignals(_guardianSignalsOf(marketIds[i])).unban(marketIds[i], account);
        }
    }

    // ---
    // PRIVATE
    // ---

    function _controllerOf(bytes32 marketId) private view returns (address) {
        return ILidoLendCoreLikeForOwnerStub(core).marketController(marketId);
    }

    function _guardianSignalsOf(bytes32 marketId) private view returns (address) {
        return ILidoLendMarketController(_controllerOf(marketId)).guardianSignals();
    }
}
