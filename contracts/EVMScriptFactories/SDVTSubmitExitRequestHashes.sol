// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../libraries/SubmitExitRequestHashesUtils.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IStakingRouter.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IValidatorsExitBusOracle.sol";

/// @author swissarmytowel
/// @notice Creates EVMScript to submit exit hashes to the Validators Exit Bus Oracle for SDVT module.
contract SDVTSubmitExitRequestHashes is TrustedCaller, IEVMScriptFactory {
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
    /// @param _evmScriptCallData Encoded exit requests data: SubmitExitRequestHashesUtils.ExitRequestInput[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        SubmitExitRequestHashesUtils.ExitRequestInput[]
            memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        require(decodedCallData.length > 0, SubmitExitRequestHashesUtils.ERROR_EMPTY_REQUESTS_LIST);

        // Validate the input data, set creator to zero as this function is only called by the trusted caller
        // and does not require checks for the creator being node operator.
        SubmitExitRequestHashesUtils.validateExitRequests(
            decodedCallData,
            nodeOperatorsRegistry,
            stakingRouter,
            address(0)
        );

        bytes32 hashedExitRequests = SubmitExitRequestHashesUtils.hashExitRequests(decodedCallData);

        return
            EVMScriptCreator.createEVMScript(
                address(validatorsExitBusOracle),
                IValidatorsExitBusOracle.submitExitRequestsHash.selector,
                abi.encode(hashedExitRequests)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded exit requests data: SubmitExitRequestHashesUtils.ExitRequestInput[]
    /// @return Array of SubmitExitRequestHashesUtils.ExitRequestInput structs
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------
    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory) {
        return abi.decode(_evmScriptCallData, (SubmitExitRequestHashesUtils.ExitRequestInput[]));
    }
}
