// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IStakingRouter.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IValidatorsExitBusOracle.sol";

/// @author swissarmytowel
/// @notice Creates EVMScript to submit exit hashes to the Validators Exit Bus Oracle
contract SubmitValidatorsExitRequestHashes is TrustedCaller, IEVMScriptFactory {
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
    // IMMUTABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;

    /// @notice Address of Lido's Staking Router contract
    IStakingRouter public immutable stakingRouter;

    /// @notice Address of ValidatorsExitBusOracle contract
    IValidatorsExitBusOracle public immutable validatorsExitBusOracle;

    // -------------
    // CONSTANTS
    // -------------

    /// @notice Maximum length of validator public key in bytes
    uint256 private constant PUBKEY_LENGTH = 48;
    /// @notice Maximum number of items to process in one motion
    uint256 private constant MAX_REQUESTS_PER_MOTION = 200;
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

    // Error messages for node operator ID validation
    string private constant ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST =
        "NODE_OPERATOR_ID_DOES_NOT_EXIST";
    string private constant ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE =
        "EXECUTOR_NOT_PERMISSIONED_ON_MODULE";

    // Error messages for integer overflows
    string private constant ERROR_MODULE_ID_OVERFLOW = "MODULE_ID_OVERFLOW";
    string private constant ERROR_NODE_OP_ID_OVERFLOW = "NODE_OPERATOR_ID_OVERFLOW";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry,
        address _stakingRouter,
        address _validatorsExitBusOracle
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
        stakingRouter = IStakingRouter(_stakingRouter);
        validatorsExitBusOracle = IValidatorsExitBusOracle(_validatorsExitBusOracle);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to submit exit request hashes to the Validators Exit Bus Oracle
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded exit requests data: ExitRequestInput[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        ExitRequestInput[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(decodedCallData);

        bytes memory packedData;
        uint256 numberOfRequests = decodedCallData.length;

        for (uint256 i; i < numberOfRequests; ) {
            ExitRequestInput memory request = decodedCallData[i];
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

        bytes32 hashedExitRequests = keccak256(abi.encode(packedData, DATA_FORMAT_LIST));

        return
            EVMScriptCreator.createEVMScript(
                address(validatorsExitBusOracle),
                IValidatorsExitBusOracle.submitExitRequestsHash.selector,
                abi.encode(hashedExitRequests)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded exit requests data: ExitRequestInput[]
    /// @return Array of ExitRequestInput structs
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (ExitRequestInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------
    function _validateInputData(ExitRequestInput[] memory _exitRequests) private view {
        uint256 length = _exitRequests.length;

        // Validate the length of the exit requests array
        require(length > 0, ERROR_EMPTY_REQUESTS_LIST);
        require(length <= MAX_REQUESTS_PER_MOTION, ERROR_MAX_REQUESTS_PER_MOTION_EXCEEDED);

        // Retrieve the first request module details
        IStakingRouter.StakingModule memory module = stakingRouter.getStakingModule(
            _exitRequests[0].moduleId
        );

        // Check if the module is valid and matches the registry address. If this passes, all subsequent requests
        // will only have to be checked to have the same module ID
        require(
            module.stakingModuleAddress == address(nodeOperatorsRegistry),
            ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE
        );

        uint256 moduleId = module.id;
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        // Prepare array for deduplication hashes
        bytes32[] memory seenPubkeyHashes = new bytes32[](length);

        // Iterate through all exit requests to validate them
        for (uint256 i; i < length; ) {
            ExitRequestInput memory _input = _exitRequests[i];

            // Check that the module ID, node operator ID, are within the valid ranges as they are stored as uint256 but have smaller limits
            require(_input.moduleId <= type(uint24).max, ERROR_MODULE_ID_OVERFLOW);
            require(_input.nodeOpId <= type(uint40).max, ERROR_NODE_OP_ID_OVERFLOW);
            // Node operator ids are ordered from 0 to nodeOperatorsCount - 1, so we check that the id is less than the count
            require(_input.nodeOpId < nodeOperatorsCount, ERROR_NODE_OPERATOR_ID_DOES_NOT_EXIST);
            // Check that the validator public key is exactly 48 bytes long
            require(_input.valPubkey.length == PUBKEY_LENGTH, ERROR_INVALID_PUBKEY_LENGTH);
            // Check that all requests have the same module ID, which ensures that all requests are for the same staking module
            require(_input.moduleId == moduleId, ERROR_EXECUTOR_NOT_PERMISSIONED_ON_MODULE);

            // Fetch the registered signing key for this operator and pubkey index
            (bytes memory key, , ) = nodeOperatorsRegistry.getSigningKey(
                _input.nodeOpId,
                _input.valPubKeyIndex
            );

            // Duplicate check: linear scan over hashes so far
            bytes32 providedPubkeyHash = keccak256(_input.valPubkey);

            // Compare the keccak256 hash of the provided public key with the keccak256 hash of the signing key
            require(keccak256(key) == providedPubkeyHash, ERROR_INVALID_PUBKEY);

            for (uint256 j; j < i; ) {
                require(seenPubkeyHashes[j] != providedPubkeyHash, ERROR_DUPLICATE_EXIT_REQUESTS);

                unchecked {
                    ++j;
                }
            }

            seenPubkeyHashes[i] = providedPubkeyHash;

            unchecked {
                ++i;
            }
        }
    }

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (ExitRequestInput[] memory) {
        return abi.decode(_evmScriptCallData, (ExitRequestInput[]));
    }
}
