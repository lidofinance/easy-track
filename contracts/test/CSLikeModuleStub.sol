// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import {WithdrawnValidatorInfo} from "../interfaces/IBaseModule.sol";

contract CSLikeModuleStub {
    uint256 internal _nodeOperatorsCount;
    mapping(uint256 => uint256) internal _lockedBond;

    uint256 public lastSettledCount;
    uint256 public lastSettledFirstNodeOperatorId;
    uint256 public lastSettledFirstMaxAmount;

    event GotValidatorInfo(WithdrawnValidatorInfo info);
    event GeneralDelayedPenaltySettled(uint256[] nodeOperatorIds, uint256[] maxAmounts);

    function ACCOUNTING() external view returns (address) {
        return address(this);
    }

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external {
        for (uint256 i; i < validatorInfos.length; ++i) {
            emit GotValidatorInfo(validatorInfos[i]);
        }
    }

    function getNodeOperatorsCount() external view returns (uint256) {
        return _nodeOperatorsCount;
    }

    function mock_setNodeOperatorsCount(uint256 nodeOperatorsCount) external {
        _nodeOperatorsCount = nodeOperatorsCount;
    }

    function getLockedBond(uint256 nodeOperatorId) external view returns (uint256) {
        return _lockedBond[nodeOperatorId];
    }

    function mock_setLockedBond(uint256 nodeOperatorId, uint256 amount) external {
        _lockedBond[nodeOperatorId] = amount;
    }

    function settleGeneralDelayedPenalty(uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts) external {
        require(nodeOperatorIds.length == maxAmounts.length, "LENGTH_MISMATCH");

        lastSettledCount = 0;
        lastSettledFirstNodeOperatorId = 0;
        lastSettledFirstMaxAmount = 0;

        for (uint256 i; i < nodeOperatorIds.length; ++i) {
            uint256 nodeOperatorId = nodeOperatorIds[i];
            uint256 maxAmount = maxAmounts[i];
            uint256 locked = _lockedBond[nodeOperatorId];

            if (locked == 0 || locked > maxAmount) {
                continue;
            }

            if (lastSettledCount == 0) {
                lastSettledFirstNodeOperatorId = nodeOperatorId;
                lastSettledFirstMaxAmount = maxAmount;
            }

            _lockedBond[nodeOperatorId] = 0;
            ++lastSettledCount;
        }

        emit GeneralDelayedPenaltySettled(nodeOperatorIds, maxAmounts);
    }
}
