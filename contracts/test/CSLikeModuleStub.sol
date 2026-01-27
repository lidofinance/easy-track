// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import {WithdrawnValidatorInfo} from "../interfaces/ICSModule.sol";

contract CSLikeModuleStub {
    uint256 internal _nodeOperatorsCount;

    event GotValidatorInfo(WithdrawnValidatorInfo info);

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
}
