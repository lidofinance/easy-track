// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/SubmitExitRequestHashesUtils.sol";

/// @notice Helper contract to wrap SubmitExitRequestHashesUtils functions for testing purposes.
contract SubmitExitRequestHashesUtilsWrapper {
    function hashExitRequests(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory _requests
    ) external pure returns (bytes32) {
        return SubmitExitRequestHashesUtils.hashExitRequests(_requests);
    }

    function validateExitRequests(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter,
        address _creator
    ) external view {
        SubmitExitRequestHashesUtils.validateExitRequests(
            _requests,
            _nodeOperatorsRegistry,
            _stakingRouter,
            _creator
        );
    }
}
