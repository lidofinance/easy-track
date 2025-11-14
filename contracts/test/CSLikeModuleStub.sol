// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import {ValidatorWithdrawalInfo} from "../interfaces/ICSModule.sol";

contract CSLikeModuleStub {
    uint256 internal _nodeOperatorsCount;

    event GotWithdrawalInfo(ValidatorWithdrawalInfo info);

    function submitWithdrawals(ValidatorWithdrawalInfo[] calldata withdrawalsInfo) external {
        for (uint256 i; i < withdrawalsInfo.length; ++i) {
            emit GotWithdrawalInfo(withdrawalsInfo[i]);
        }
    }

    function getNodeOperatorsCount() external view returns (uint256) {
        return _nodeOperatorsCount;
    }

    function mock_setNodeOperatorsCount(uint256 nodeOperatorsCount) external {
        _nodeOperatorsCount = nodeOperatorsCount;
    }
}
