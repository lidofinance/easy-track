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
/// @notice Creates EVMScript to submit exit hashes to the Validators Exit Bus Oracle for Curated module.
contract CuratedSubmitExitRequestHashes is IEVMScriptFactory {
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
        address _nodeOperatorsRegistry,
        address _stakingRouter,
        address _validatorsExitBusOracle
    ) {
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
    ) external view override returns (bytes memory) {
        SubmitExitRequestHashesUtils.ExitRequestInput[]
            memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        // Validate the input data
        SubmitExitRequestHashesUtils.validateExitRequests(
            decodedCallData,
            nodeOperatorsRegistry,
            stakingRouter,
            _creator
        );

        // validate that the first exit request is for the node operator that is creating the EVMScript
        // the rest of the exit requests can be for that one node operator, which is checked in the validateExitRequests method above
        (, , address rewardAddress, , , , ) = nodeOperatorsRegistry.getNodeOperator(
            decodedCallData[0].nodeOpId,
            false
        );

        require(
            rewardAddress == _creator,
            SubmitExitRequestHashesUtils.ERROR_EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR
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
