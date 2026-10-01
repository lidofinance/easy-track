// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import {WithdrawnValidatorInfo} from "../interfaces/IBaseModule.sol";

import {AccountingStub} from "./AccountingStub.sol";

/// @notice Test stub implementing the IBaseModule method surface.
/// Specialized module stubs (e.g. curated) inherit from this contract.
contract BaseModuleStub {
    uint256 internal _nodeOperatorsCount;
    AccountingStub internal _accounting;
    mapping(uint256 => mapping(uint256 => bool)) internal _isValidatorSlashed;

    event GotValidatorInfo(WithdrawnValidatorInfo info);
    event GeneralDelayedPenaltySettled(uint256 nodeOperatorId);

    function ACCOUNTING() external view returns (address) {
        return address(_accounting);
    }

    function mock_setAccounting(AccountingStub accounting_) external {
        _accounting = accounting_;
    }

    function getNodeOperatorsCount() external view returns (uint256) {
        return _nodeOperatorsCount;
    }

    function mock_setNodeOperatorsCount(uint256 nodeOperatorsCount) external {
        _nodeOperatorsCount = nodeOperatorsCount;
    }

    function mock_setValidatorSlashed(
        uint256 nodeOperatorId,
        uint256 keyIndex,
        bool isSlashed
    ) external {
        _isValidatorSlashed[nodeOperatorId][keyIndex] = isSlashed;
    }

    function isValidatorSlashed(uint256 nodeOperatorId, uint256 keyIndex)
        external
        view
        returns (bool)
    {
        return _isValidatorSlashed[nodeOperatorId][keyIndex];
    }

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos)
        external
    {
        for (uint256 i; i < validatorInfos.length; ++i) {
            emit GotValidatorInfo(validatorInfos[i]);
        }
    }

    function settleGeneralDelayedPenalty(uint256[] memory nodeOperatorIds, uint256[] memory nonces)
        external
    {
        require(nodeOperatorIds.length == nonces.length, "LENGTH_MISMATCH");

        for (uint256 i; i < nodeOperatorIds.length; ++i) {
            uint256 nodeOperatorId = nodeOperatorIds[i];
            uint256 nonce = nonces[i];

            // Read locked bond from the accounting contract.
            uint256 locked = _accounting.getLockedBond(nodeOperatorId);
            if (locked == 0) {
                continue;
            }

            require(nonce == _accounting.getBondLockNonce(nodeOperatorId), "LOCK_NONCE_MISMATCH");

            emit GeneralDelayedPenaltySettled(nodeOperatorId);
            // Clear locked bond on accounting
            _accounting.mock_clearLock(nodeOperatorId);
        }
    }
}
