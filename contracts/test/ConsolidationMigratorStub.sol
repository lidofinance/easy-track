// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/IConsolidationMigrator.sol";

/// @notice Lightweight stub of the ConsolidationMigrator used in tests
contract ConsolidationMigratorStub is IConsolidationMigrator {
    error ZeroArgument(string name);
    error PairNotInAllowlist(uint256 sourceOperatorId, uint256 targetOperatorId);

    uint256 private _sourceModuleId;
    uint256 private _targetModuleId;
    address private _stakingRouter;

    mapping(uint256 => mapping(uint256 => bool)) private _allowedPairs;
    mapping(uint256 => mapping(uint256 => address)) private _submitters;
    mapping(uint256 => uint256[]) private _allowedTargets;

    constructor(
        uint256 sourceModuleId_,
        uint256 targetModuleId_,
        address stakingRouter_
    ) {
        _sourceModuleId = sourceModuleId_;
        _targetModuleId = targetModuleId_;
        _stakingRouter = stakingRouter_;
    }

    function setModuleIds(uint256 newSourceId, uint256 newTargetId) external {
        _sourceModuleId = newSourceId;
        _targetModuleId = newTargetId;
    }

    function setStakingRouter(address newStakingRouter) external {
        _stakingRouter = newStakingRouter;
    }

    function setPairStatus(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        bool allowed
    ) external {
        if (allowed) {
            if (!_allowedPairs[sourceOperatorId][targetOperatorId]) {
                _allowedPairs[sourceOperatorId][targetOperatorId] = true;
                _allowedTargets[sourceOperatorId].push(targetOperatorId);
            }
        } else if (_allowedPairs[sourceOperatorId][targetOperatorId]) {
            _allowedPairs[sourceOperatorId][targetOperatorId] = false;
            _removeAllowedTarget(sourceOperatorId, targetOperatorId);
            _submitters[sourceOperatorId][targetOperatorId] = address(0);
        }
    }

    function sourceModuleId() external view override returns (uint256) {
        return _sourceModuleId;
    }

    function targetModuleId() external view override returns (uint256) {
        return _targetModuleId;
    }

    function getStakingRouter() external view override returns (address) {
        return _stakingRouter;
    }

    function getConsolidationBus() external view override returns (address) {
        return address(0);
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

    function getSubmitter(
        uint256 sourceOperatorId,
        uint256 targetOperatorId
    ) external view override returns (address) {
        return _submitters[sourceOperatorId][targetOperatorId];
    }

    function submitConsolidationBatch(
        uint256,
        uint256,
        ConsolidationIndexGroup[] calldata
    ) external override {}

    function allowPair(
        uint256 sourceOperatorId,
        uint256 targetOperatorId,
        address submitter
    ) external override {
        if (submitter == address(0)) {
            revert ZeroArgument("submitter");
        }

        _submitters[sourceOperatorId][targetOperatorId] = submitter;

        if (!_allowedPairs[sourceOperatorId][targetOperatorId]) {
            _allowedPairs[sourceOperatorId][targetOperatorId] = true;
            _allowedTargets[sourceOperatorId].push(targetOperatorId);
        }

        emit ConsolidationPairAllowed(sourceOperatorId, targetOperatorId, submitter);
    }

    function disallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external override {
        if (!_allowedPairs[sourceOperatorId][targetOperatorId]) {
            revert PairNotInAllowlist(sourceOperatorId, targetOperatorId);
        }

        _allowedPairs[sourceOperatorId][targetOperatorId] = false;
        _removeAllowedTarget(sourceOperatorId, targetOperatorId);
        address submitter = _submitters[sourceOperatorId][targetOperatorId];
        _submitters[sourceOperatorId][targetOperatorId] = address(0);
        emit ConsolidationPairDisallowed(sourceOperatorId, targetOperatorId, submitter);
    }

    function selfDisallowPair(uint256 sourceOperatorId, uint256 targetOperatorId) external override {
        require(
            _submitters[sourceOperatorId][targetOperatorId] == msg.sender,
            "NOT_AUTHORIZED"
        );

        _allowedPairs[sourceOperatorId][targetOperatorId] = false;
        _removeAllowedTarget(sourceOperatorId, targetOperatorId);
        _submitters[sourceOperatorId][targetOperatorId] = address(0);
        emit ConsolidationPairDisallowed(sourceOperatorId, targetOperatorId, msg.sender);
    }

    function _removeAllowedTarget(uint256 sourceOperatorId, uint256 targetOperatorId) private {
        uint256[] storage targets = _allowedTargets[sourceOperatorId];
        for (uint256 i; i < targets.length; ++i) {
            if (targets[i] == targetOperatorId) {
                targets[i] = targets[targets.length - 1];
                targets.pop();
                return;
            }
        }
    }
}
