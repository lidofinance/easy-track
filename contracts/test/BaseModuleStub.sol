// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import {WithdrawnValidatorInfo} from "../interfaces/IBaseModule.sol";

/// @notice Test stub implementing the IBaseModule method surface.
/// Specialized module stubs (e.g. curated) inherit from this contract.
contract BaseModuleStub {
    uint256 internal _nodeOperatorsCount;
    address internal _accounting;

    uint256 public lastSettledCount;
    uint256 public lastSettledFirstNodeOperatorId;
    uint256 public lastSettledFirstMaxAmount;

    event GotValidatorInfo(WithdrawnValidatorInfo info);
    event GeneralDelayedPenaltySettled(uint256[] nodeOperatorIds, uint256[] maxAmounts);

    function ACCOUNTING() external view returns (address) {
        return _accounting;
    }

    function mock_setAccounting(address accounting_) external {
        _accounting = accounting_;
    }

    function getNodeOperatorsCount() external view returns (uint256) {
        return _nodeOperatorsCount;
    }

    function mock_setNodeOperatorsCount(uint256 nodeOperatorsCount) external {
        _nodeOperatorsCount = nodeOperatorsCount;
    }

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external {
        for (uint256 i; i < validatorInfos.length; ++i) {
            emit GotValidatorInfo(validatorInfos[i]);
        }
    }

    function settleGeneralDelayedPenalty(uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts) external {
        require(nodeOperatorIds.length == maxAmounts.length, "LENGTH_MISMATCH");

        lastSettledCount = 0;
        lastSettledFirstNodeOperatorId = 0;
        lastSettledFirstMaxAmount = 0;

        for (uint256 i; i < nodeOperatorIds.length; ++i) {
            uint256 nodeOperatorId = nodeOperatorIds[i];
            uint256 maxAmount = maxAmounts[i];

            // Read locked bond from the accounting contract
            (bool ok, bytes memory data) = _accounting.staticcall(
                abi.encodeWithSignature("getLockedBond(uint256)", nodeOperatorId)
            );
            require(ok, "ACCOUNTING_CALL_FAILED");
            uint256 locked = abi.decode(data, (uint256));

            if (locked == 0 || locked > maxAmount) {
                continue;
            }

            if (lastSettledCount == 0) {
                lastSettledFirstNodeOperatorId = nodeOperatorId;
                lastSettledFirstMaxAmount = maxAmount;
            }

            // Clear locked bond on accounting
            (bool ok2, ) = _accounting.call(
                abi.encodeWithSignature("mock_clearLockedBond(uint256)", nodeOperatorId)
            );
            require(ok2, "ACCOUNTING_CLEAR_FAILED");

            ++lastSettledCount;
        }

        emit GeneralDelayedPenaltySettled(nodeOperatorIds, maxAmounts);
    }
}
