// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Interface for validating and submitting stake consolidation (migration) requests
///         between operators across two modules.
interface IConsolidationMigrator {
    // =========
    //  Events
    // =========
    event ConsolidationPairAllowed(uint256 indexed sourceOperatorId, uint256 indexed targetOperatorId);
    event ConsolidationPairDisallowed(uint256 indexed sourceOperatorId, uint256 indexed targetOperatorId);
    event ConsolidationSubmitted(
        uint256 indexed sourceOperatorId,
        uint256 indexed targetOperatorId,
        uint256[] sourceValidatorIndices,
        uint256[] targetValidatorIndices
    );

    // ==================
    //  Read-only views
    // ==================

    /// @notice Gets the source module ID this migrator is bound to.
    function sourceModuleId() external view returns (uint256);

    /// @notice Gets the target module ID this migrator is bound to.
    function targetModuleId() external view returns (uint256);

    /// @notice Returns the address of the legacy curated module.
    function sourceModule() external view returns (address);

    /// @notice Returns the address of the destination module.
    function targetModule() external view returns (address);

    /// @notice Returns true if consolidation from `sourceOperatorId` to `targetOperatorId` is allowed.
    function isPairAllowed(uint256 sourceOperatorId, uint256 targetOperatorId) external view returns (bool);

    /// @notice Returns the list of target operators allowed for a given `sourceOperatorId`.
    function getAllowedTargets(uint256 sourceOperatorId) external view returns (uint256[] memory targetOperatorIds);

    // =========================
    //  Validation & Submission
    // =========================

    /// @notice Validates a batch of consolidation requests without changing state.
    /// @dev Reverts if invalid.
    function validateConsolidationBatch(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        uint256[] calldata sourceValidatorIndices,
        uint256[] calldata targetValidatorIndices
    ) external view;

    /// @notice Submits a batch of consolidation requests after validation.
    /// @dev MUST revert if the batch would fail validation. Emits ConsolidationSubmitted on success.
    function submitConsolidationBatch(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        uint256[] calldata sourceValidatorIndices,
        uint256[] calldata targetValidatorIndices
    ) external;

    // ======================
    //  Allowlist management
    // ======================

    /// @notice Allows consolidations from `sourceOperatorId` to `targetOperatorId`.
    /// @dev Access-controlled in the implementation (role-based).
    function allowPair(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        address consolidationManager
    ) external;

    /// @notice Disallows consolidations from `sourceOperatorId` to `targetOperatorId`.
    /// @dev Access-controlled in the implementation (role-based).
    function disallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external;
}
