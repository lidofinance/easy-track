// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IStakingRouter.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IValidatorsExitBusOracle.sol";
import "../interfaces/IStakingRouter.sol";

/// @title ValidatorExitRequestUtils
/// @notice Library for creating and validating EVM scripts for validators exit requests.
library ValidatorExitRequestUtils {
    // -------------
    // STRUCTS
    // -------------

    /// @notice Input data for exit report
    struct ExitRequestInput {
        uint256 moduleId;
        uint256 nodeOpId;
        uint64 valIndex;
        bytes valPubkey;
        uint256 valPubKeyIndex;
    }

    // -------------
    // CONSTANTS
    // -------------

    /// @notice Maximum length of validator public key in bytes
    uint256 private constant MAX_PUBKEY_LENGTH = 48;
    /// @notice Maximum number of items to process in one motion
    uint256 private constant MAX_REQUESTS_PER_MOTION = 300;
    /// @notice Data format identifier for the list of exit requests, only 1 is supported at the moment (ref: https://etherscan.io/address/0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e)
    uint256 private constant DATA_FORMAT_LIST = 1;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_REQUESTS_LIST = "EMPTY_REQUESTS_LIST";
    string private constant ERROR_MAX_REQUESTS_PER_MOTION_EXCEEDED =
        "MAX_REQUESTS_PER_MOTION_EXCEEDED";

    // Error messages for validator public key validation
    string private constant ERROR_PUBKEY_IS_EMPTY = "PUBKEY_IS_EMPTY";
    string private constant ERROR_INVALID_PUBKEY = "INVALID_PUBKEY";
    string private constant ERROR_INVALID_PUBKEY_LENGTH = "INVALID_PUBKEY_LENGTH";

    // Error messages for node operator ID validation
    string private constant ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST =
        "NODE_OPERATOR_ID_DOES_NOT_EXIST";
    string private constant ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE =
        "EXECUTOR_NOT_PERMISSIONED_ON_MODULE";

    // Error messages for integer overflows
    string private constant ERROR_MODULE_ID_OVERFLOW = "MODULE_ID_OVERFLOW";
    string private constant ERROR_NODE_OP_ID_OVERFLOW = "NODE_OPERATOR_ID_OVERFLOW";

    // -------------
    // INTERNAL METHODS
    // -------------

    /// @notice Hashes a slice of exit requests input data.
    function hashExitRequests(ExitRequestInput[] memory _requests) internal pure returns (bytes32) {
        bytes memory packedData;
        uint256 numberOfRequests = _requests.length;

        for (uint256 i; i < numberOfRequests; ) {
            ExitRequestInput memory request = _requests[i];
            // pack into 64 bytes: 3 + 5 + 8 + 48
            packedData = abi.encodePacked(
                packedData,
                // uint24
                bytes3(uint24(request.moduleId)),
                // uint40
                bytes5(uint40(request.nodeOpId)),
                // uint64
                bytes8(request.valIndex),
                // bytes48
                request.valPubkey
            );

            unchecked {
                ++i;
            }
        }

        return keccak256(abi.encode(packedData, DATA_FORMAT_LIST));
    }

    /// @notice Validates the exit requests input data.
    function validateExitRequests(
        ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter
    ) internal view {
        uint256 length = _requests.length;
        require(length > 0, ERROR_EMPTY_REQUESTS_LIST);

        require(length <= MAX_REQUESTS_PER_MOTION, ERROR_MAX_REQUESTS_PER_MOTION_EXCEEDED);

        // Retrieve the first request module details
        IStakingRouter.StakingModule memory module = _stakingRouter.getStakingModule(
            _requests[0].moduleId
        );

        // Check if the module is valid and matches the registry address. If this passes, all subsequent requests
        // will only have to be checked to have the same module ID
        require(
            module.stakingModuleAddress == address(_nodeOperatorsRegistry),
            ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE
        );

        uint256 moduleId = module.id;
        uint256 nodeOperatorsCount = _nodeOperatorsRegistry.getNodeOperatorsCount();

        for (uint256 i; i < length; ) {
            ExitRequestInput memory _input = _requests[i];

            // Check that the module ID, node operator ID, are within the valid ranges as they are stored as uint256 but have smaller limits
            require(_input.moduleId <= type(uint24).max, ERROR_MODULE_ID_OVERFLOW);
            require(_input.nodeOpId <= type(uint40).max, ERROR_NODE_OP_ID_OVERFLOW);

            // Node operator ids are ordered from 0 to nodeOperatorsCount - 1, so we check that the id is less than the count
            require(_input.nodeOpId < nodeOperatorsCount, ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST);
            // Check the validator public key length and that it is not empty
            require(_input.valPubkey.length > 0, ERROR_PUBKEY_IS_EMPTY);
            // Check that the validator public key is exactly 48 bytes long
            require(_input.valPubkey.length == MAX_PUBKEY_LENGTH, ERROR_INVALID_PUBKEY_LENGTH);

            // Check that all requests have the same module ID, which ensures that all requests are for the same staking module
            require(_input.moduleId == moduleId, ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE);

            (bytes memory key, , ) = _nodeOperatorsRegistry.getSigningKey(
                _input.nodeOpId,
                _input.valPubKeyIndex
            );

            require(keccak256(key) == keccak256(_input.valPubkey), ERROR_INVALID_PUBKEY);

            unchecked {
                ++i;
            }
        }
    }
}
