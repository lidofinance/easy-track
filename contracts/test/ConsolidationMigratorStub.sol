// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IConsolidationMigrator.sol";

/// @notice Lightweight stub of the ConsolidationMigrator used in tests
contract ConsolidationMigratorStub is IConsolidationMigrator {
    uint256 private _sourceModuleId;
    uint256 private _targetModuleId;
    address private _sourceModule;
    address private _targetModule;

    mapping(uint256 => mapping(uint256 => bool)) private _allowedPairs;
    mapping(uint256 => uint256[]) private _allowedTargets;

    constructor(
        uint256 sourceModuleId_,
        uint256 targetModuleId_,
        address sourceModule_,
        address targetModule_
    ) {
        _sourceModuleId = sourceModuleId_;
        _targetModuleId = targetModuleId_;
        _sourceModule = sourceModule_;
        _targetModule = targetModule_;
    }

    function setModuleIds(uint256 newSourceId, uint256 newTargetId) external {
        _sourceModuleId = newSourceId;
        _targetModuleId = newTargetId;
    }

    function setModuleAddresses(address newSource, address newTarget) external {
        _sourceModule = newSource;
        _targetModule = newTarget;
    }

    function setPairStatus(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        bool allowed
    ) external {
        _allowedPairs[sourceOperatorId][targetOperatorId] = allowed;
    }

    function sourceModuleId() external view override returns (uint256) {
        return _sourceModuleId;
    }

    function targetModuleId() external view override returns (uint256) {
        return _targetModuleId;
    }

    function sourceModule() external view override returns (address) {
        return _sourceModule;
    }

    function targetModule() external view override returns (address) {
        return _targetModule;
    }

    function isPairAllowed(
        uint256 sourceOperatorId,
        uint256 targetOperatorId
    ) external view override returns (bool) {
        return _allowedPairs[sourceOperatorId][targetOperatorId];
    }

    function getAllowedTargets(
        uint256 sourceOperatorId
    ) external view override returns (uint256[] memory) {
        return _allowedTargets[sourceOperatorId];
    }

    function validateConsolidationBatch(
        uint256,
        uint256,
        uint256[] calldata,
        uint256[] calldata
    ) external view override {}

    function submitConsolidationBatch(
        uint256,
        uint256,
        uint256[] calldata,
        uint256[] calldata
    ) external override {}

    function allowPair(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        address /* consolidationManager */
    ) external override {
        if (!_allowedPairs[sourceOperatorId][targetOperatorId]) {
            _allowedPairs[sourceOperatorId][targetOperatorId] = true;
            _allowedTargets[sourceOperatorId].push(targetOperatorId);
            emit ConsolidationPairAllowed(sourceOperatorId, targetOperatorId);
        }
    }

    function disallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external override {
        if (_allowedPairs[sourceOperatorId][targetOperatorId]) {
            _allowedPairs[sourceOperatorId][targetOperatorId] = false;
            emit ConsolidationPairDisallowed(sourceOperatorId, targetOperatorId);
        }
    }
}
