// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IStakingRouter.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IValidatorsExitBusOracle.sol";
import "../interfaces/IStakingRouter.sol";

/// @title ValidatorExitRequestHelpers
/// @notice Library for creating and validating EVM scripts for validators exit requests.
library ValidatorExitRequestHelpers {
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
    /// @notice Maximum number of items to process in one batch, if input data contains more items, it will be split into several batches
    uint256 private constant MAX_BATCH_SIZE = 600;
    /// @notice Data format identifier for the list of exit requests, only 1 is supported at the moment (ref: https://etherscan.io/address/0x0De4Ea0184c2ad0BacA7183356Aea5B8d5Bf5c6e)
    uint256 private constant DATA_FORMAT_LIST = 1;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_REQUESTS_LIST = "EMPTY_REQUESTS_LIST";
    string private constant ERROR_MAX_BATCH_SIZE_EXCEEDED = "MAX_BATCH_SIZE_EXCEEDED";

    // Error messages for validator public key validation
    string private constant ERROR_PUBKEY_IS_EMPTY = "PUBKEY_IS_EMPTY";
    string private constant ERROR_PUBKEY_MISMATCH = "PUBKEY_MISMATCH";
    string private constant ERROR_PUBKEY_MAX_LENGTH_EXCEEDED = "PUBKEY_MAX_LENGTH_EXCEEDED";

    string private constant ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST =
        "NODE_OPERATOR_ID_DOES_NOT_EXIST";
    string private constant ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE =
        "EXECUTOR_NOT_PERMISSIONED_ON_MODULE";

    // -------------
    // INTERNAL METHODS
    // -------------

    /// @notice Validates and constructs an EVMScript for submitting exit requests to the Validators Exit Bus Oracle.
    /// @param _validatorsExitBusOracle Address of the Validators Exit Bus Oracle contract
    /// @param _requests Array of exit request inputs
    /// @param _nodeOperatorsRegistry Address of the Node Operators Registry contract
    /// @param _stakingRouter Address of the Staking Router contract
    /// @return bytes Encoded EVMScript for submitting exit requests
    function constructExitValidatorInputHash(
        address _validatorsExitBusOracle,
        ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter
    ) internal view returns (bytes memory) {
        _validateExitRequests(_requests, _nodeOperatorsRegistry, _stakingRouter);

        return
            EVMScriptCreator.createEVMScript(
                _validatorsExitBusOracle,
                IValidatorsExitBusOracle.submitExitRequestsHash.selector,
                abi.encode(_hashRequests(_requests))
            );
    }

    // -------------
    // PRIVATE METHODS
    // -------------

    /// @notice Hashes a slice of exit requests input data.
    function _hashRequests(ExitRequestInput[] memory _requests) private pure returns (bytes32) {
        uint256 numberOfRequests = _requests.length;
        require(numberOfRequests <= MAX_BATCH_SIZE, ERROR_MAX_BATCH_SIZE_EXCEEDED);

        bytes memory packedData;

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
    function _validateExitRequests(
        ExitRequestInput[] memory _requests,
        INodeOperatorsRegistry _nodeOperatorsRegistry,
        IStakingRouter _stakingRouter
    ) private view {
        uint256 length = _requests.length;
        require(length > 0, ERROR_EMPTY_REQUESTS_LIST);

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

            // Node operator ids are ordered from 0 to nodeOperatorsCount - 1, so we check that the id is less than the count
            require(_input.nodeOpId < nodeOperatorsCount, ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST);
            // Check the validator public key length and that it is not empty
            require(_input.valPubkey.length > 0, ERROR_PUBKEY_IS_EMPTY);
            require(_input.valPubkey.length <= MAX_PUBKEY_LENGTH, ERROR_PUBKEY_MAX_LENGTH_EXCEEDED);

            // Check that all requests have the same module ID, which ensures that all requests are for the same staking module
            require(_input.moduleId == moduleId, ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE);

            (bytes memory key, , ) = _nodeOperatorsRegistry.getSigningKey(
                _input.nodeOpId,
                _input.valPubKeyIndex
            );

            require(keccak256(key) == keccak256(_input.valPubkey), ERROR_PUBKEY_MISMATCH);

            unchecked {
                ++i;
            }
        }
    }
}
