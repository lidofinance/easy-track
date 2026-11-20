// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Interface for validating and submitting stake consolidation (migration) requests
///         between operators across two modules.
interface IConsolidationMigrator {
    // =========
    //  Structs
    // =========

    struct ConsolidationIndexGroup {
        uint256[] sourceKeyIndices;
        uint256 targetKeyIndex;
    }

    // =========
    //  Events
    // =========
    event ConsolidationPairAllowed(
        uint256 indexed sourceOperatorId,
        uint256 indexed targetOperatorId,
        address indexed submitter
    );
    event ConsolidationPairDisallowed(
        uint256 indexed sourceOperatorId,
        uint256 indexed targetOperatorId,
        address indexed submitter
    );
    event ConsolidationSubmitted(
        uint256 indexed sourceOperatorId,
        uint256 indexed targetOperatorId,
        ConsolidationIndexGroup[] groups
    );

    // ==================
    //  Read-only views
    // ==================

    /// @notice Gets the source module ID this migrator is bound to.
    function sourceModuleId() external view returns (uint256);

    /// @notice Gets the target module ID this migrator is bound to.
    function targetModuleId() external view returns (uint256);

    /// @notice Returns the staking router address used to resolve module ids.
    function getStakingRouter() external view returns (address);

    /// @notice Returns the consolidation bus address.
    function getConsolidationBus() external view returns (address);

    /// @notice Returns true if consolidation from `sourceOperatorId` to `targetOperatorId` is allowed.
    function isPairAllowed(uint256 sourceOperatorId, uint256 targetOperatorId) external view returns (bool);

    /// @notice Returns the list of target operators allowed for a given `sourceOperatorId`.
    function getAllowedTargets(uint256 sourceOperatorId) external view returns (uint256[] memory targetOperatorIds);

    /// @notice Returns the designated submitter for a given consolidation pair.
    function getSubmitter(uint256 sourceOperatorId, uint256 targetOperatorId) external view returns (address);

    // =========================
    //  Submission
    // =========================

    /// @notice Submits a batch of consolidation requests.
    function submitConsolidationBatch(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        ConsolidationIndexGroup[] calldata groups
    ) external;

    // ======================
    //  Allowlist management
    // ======================

    /// @notice Allows consolidations from `sourceOperatorId` to `targetOperatorId`.
    function allowPair(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        address submitter
    ) external;

    /// @notice Disallows consolidations from `sourceOperatorId` to `targetOperatorId`.
    function disallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external;

    /// @notice Permissionless disallow — caller must be the designated submitter.
    function selfDisallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external;
}
