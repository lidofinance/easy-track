// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/ValidatorSubmitExitHashesUtils.sol";

/// @notice Helper contract to wrap ValidatorSubmitExitHashesUtils functions for testing purposes.
contract ValidatorExitRequestUtilsWrapper {
    function hashExitRequests(
        ValidatorSubmitExitHashesUtils.ExitRequestInput[] memory _requests
    ) external pure returns (bytes32) {
        return ValidatorSubmitExitHashesUtils.hashExitRequests(_requests);
    }

    function validateExitRequests(
        ValidatorSubmitExitHashesUtils.ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter
    ) external view {
        ValidatorSubmitExitHashesUtils.validateExitRequests(
            _requests,
            _nodeOperatorsRegistry,
            _stakingRouter
        );
    }
}
