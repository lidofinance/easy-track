// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IStakingRouter.sol";
import "../interfaces/IStakingRouter.sol";

/// @author swissarmytowel
/// @title SubmitExitRequestHashesUtils
/// @notice Library for creating and validating EVM scripts for validators exit requests.
library SubmitExitRequestHashesUtils {
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
    uint256 private constant PUBKEY_LENGTH = 48;
    /// @notice Maximum number of items to process in one motion
    uint256 private constant MAX_REQUESTS_PER_MOTION = 250;
    /// @notice Data format identifier for the list of exit requests, only 1 is supported at the moment (ref: https://etherscan.io/address/0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e)
    uint256 private constant DATA_FORMAT_LIST = 1;

    // -------------
    // ERRORS
    // -------------

    // Error messages for input validation
    string private constant ERROR_EMPTY_REQUESTS_LIST = "EMPTY_REQUESTS_LIST";
    string private constant ERROR_MAX_REQUESTS_PER_MOTION_EXCEEDED =
        "MAX_REQUESTS_PER_MOTION_EXCEEDED";
    string private constant ERROR_DUPLICATE_EXIT_REQUESTS = "DUPLICATE_EXIT_REQUESTS";
    // Error messages for validator public key validation
    string private constant ERROR_INVALID_PUBKEY = "INVALID_PUBKEY";
    string private constant ERROR_INVALID_PUBKEY_LENGTH = "INVALID_PUBKEY_LENGTH";
    string private constant ERROR_INVALID_EXIT_REQUESTS_SORT_ORDER =
        "INVALID_EXIT_REQUESTS_SORT_ORDER";

    // Error messages for node operator ID validation
    string private constant ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST =
        "NODE_OPERATOR_ID_DOES_NOT_EXIST";
    string public constant ERROR_EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR =
        "EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR";
    string private constant ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE =
        "EXECUTOR_NOT_PERMISSIONED_ON_MODULE";

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
    /// @param _exitRequests Array of exit requests to validate
    /// @param _nodeOperatorsRegistry Address of the NodeOperatorsRegistry contract
    /// @param _stakingRouter Address of the StakingRouter contract
    /// @param _creator Address of the creator of the exit requests (used for permission checks for Curated module).
    ///                 Should be set to either the node operator's reward address or zero if the check is not needed.
    ///                 When zero, the check should be performed in the factory for trusted caller (SDVT Case).
    function validateExitRequests(
        ExitRequestInput[] memory _exitRequests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter,
        address _creator
    ) internal view {
        uint256 length = _exitRequests.length;

        // Validate the length of the exit requests array
        require(length > 0, ERROR_EMPTY_REQUESTS_LIST);
        require(length <= MAX_REQUESTS_PER_MOTION, ERROR_MAX_REQUESTS_PER_MOTION_EXCEEDED);

        // Use the first request to determine the module ID (should be the same for all requests)
        ExitRequestInput memory firstRequest = _exitRequests[0];

        // Retrieve the first request module details
        IStakingRouter.StakingModule memory module = _stakingRouter.getStakingModule(
            firstRequest.moduleId
        );

        // Check if the module is valid and matches the registry address. If this passes, all subsequent requests
        // will only have to be checked to have the same module ID
        require(
            module.stakingModuleAddress == address(_nodeOperatorsRegistry),
            ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE
        );

        uint256 moduleId = module.id;
        // cache the node operator ID from the first request for checking the creator
        uint256 prevNodeOpId = firstRequest.nodeOpId;
        uint256 nodeOperatorsCount = _nodeOperatorsRegistry.getNodeOperatorsCount();

        // Prepare array for deduplication hashes
        bool shouldCheckCreator = _creator != address(0);
        uint256 prevValIndex = firstRequest.valIndex;

        // Iterate through all exit requests to validate them
        for (uint256 i; i < length; ) {
            ExitRequestInput memory _input = _exitRequests[i];

            // Node operator ids are ordered from 0 to nodeOperatorsCount - 1, so we check that the id is less than the count
            require(_input.nodeOpId < nodeOperatorsCount, ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST);
            // Check that the validator public key is exactly 48 bytes long
            require(_input.valPubkey.length == PUBKEY_LENGTH, ERROR_INVALID_PUBKEY_LENGTH);
            // Check that all requests have the same module ID, which ensures that all requests are for the same staking module
            require(_input.moduleId == moduleId, ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE);
            // Check that the validator public key index is in ascending order. Strict comparison is used to ensure that there are no duplicates.
            if (i > 0) {
                require(_input.valIndex > prevValIndex, ERROR_INVALID_EXIT_REQUESTS_SORT_ORDER);
                prevValIndex = _input.valIndex;
            }

            // Check that the node operator ID matches the previous request's node operator ID if a creator is specified
            // As node operators can trigger exist requests only for their own ids, they should match.
            // Reward address is checked above and is unique for the Curated module.
            if (shouldCheckCreator) {
                require(
                    prevNodeOpId == _input.nodeOpId,
                    ERROR_EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR
                );
            }

            // Fetch the registered signing key for this operator and pubkey index
            (bytes memory key, , ) = _nodeOperatorsRegistry.getSigningKey(
                _input.nodeOpId,
                _input.valPubKeyIndex
            );

            // Duplicate check: linear scan over hashes so far
            bytes32 providedPubkeyHash = keccak256(_input.valPubkey);

            // Compare the keccak256 hash of the provided public key with the keccak256 hash of the signing key
            require(keccak256(key) == providedPubkeyHash, ERROR_INVALID_PUBKEY);

            unchecked {
                ++i;
            }
        }
    }
}
