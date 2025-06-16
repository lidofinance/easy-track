// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/ValidatorExitRequestUtils.sol";

/// @notice Helper contract to wrap ValidatorExitRequestUtils functions for testing purposes.
contract ValidatorExitRequestUtilsWrapper {
    function hashExitRequests(
        ValidatorExitRequestUtils.ExitRequestInput[] memory _requests
    ) external pure returns (bytes32) {
        return ValidatorExitRequestUtils.hashExitRequests(_requests);
    }

    function validateExitRequests(
        ValidatorExitRequestUtils.ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter
    ) external view {
        ValidatorExitRequestUtils.validateExitRequests(
            _requests,
            _nodeOperatorsRegistry,
            _stakingRouter
        );
    }
}
