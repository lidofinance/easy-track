// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Test-only stub of the Trailing Anchor Oracle methods that the Lido Lend factories use.
///         It requires `MANAGER_ROLE`, as the oracle does, but it stores each value without the other
///         checks of the oracle.
contract TrailingAnchorOracleStub {
    string private constant ERROR_MISSING_MANAGER_ROLE = "MISSING_MANAGER_ROLE";

    struct Parameters {
        uint64 maxPriceAboveAnchor;
        uint64 maxPriceBelowAnchor;
        uint64 maxAnchorContinuousRiseRate;
        uint64 maxAnchorContinuousFallRate;
        uint64 maxAnchorBelowBase;
        uint64 maxAnchorAboveBase;
        uint40 reanchorDelay;
        uint40 reanchorWindow;
    }

    bytes32 public constant MANAGER_ROLE = keccak256("MANAGER_ROLE");
    uint256 public constant MIN_REANCHOR_DELAY = 1 hours;
    uint256 public constant MIN_REANCHOR_WINDOW = 1 hours;
    uint256 public constant MAX_PRICING_SUSPENSION = 7 days;

    mapping(bytes32 => mapping(address => bool)) public hasRole;

    uint64 public maxPriceAboveAnchor;
    uint64 public maxPriceBelowAnchor;
    uint64 public maxAnchorContinuousRiseRate;
    uint64 public maxAnchorContinuousFallRate;
    uint64 public maxAnchorBelowBase;
    uint64 public maxAnchorAboveBase;
    uint40 public reanchorDelay;
    uint40 public reanchorWindow;
    uint40 public pricingResumesAt;

    modifier onlyManager() {
        require(hasRole[MANAGER_ROLE][msg.sender], ERROR_MISSING_MANAGER_ROLE);
        _;
    }

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function revokeRole(bytes32 role, address account) external {
        hasRole[role][account] = false;
    }

    function setParameters(Parameters calldata parameters) external onlyManager {
        maxPriceAboveAnchor = parameters.maxPriceAboveAnchor;
        maxPriceBelowAnchor = parameters.maxPriceBelowAnchor;
        maxAnchorContinuousRiseRate = parameters.maxAnchorContinuousRiseRate;
        maxAnchorContinuousFallRate = parameters.maxAnchorContinuousFallRate;
        maxAnchorBelowBase = parameters.maxAnchorBelowBase;
        maxAnchorAboveBase = parameters.maxAnchorAboveBase;
        reanchorDelay = parameters.reanchorDelay;
        reanchorWindow = parameters.reanchorWindow;
    }

    function setPricingResumesAt(uint40 resumesAt) external onlyManager {
        pricingResumesAt = resumesAt;
    }
}
