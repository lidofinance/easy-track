// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../libraries/ValidatorSubmitExitHashesUtils.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IStakingRouter.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IValidatorsExitBusOracle.sol";

/// @author swissarmytowel
/// @notice Creates EVMScript to submit exit requests to the Validators Exit Bus Oracle (SDVT module).
contract SDVTModuleSubmitExitRequestHashes is TrustedCaller, IEVMScriptFactory {
    // -------------
    // IMMUTABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable sdvtNodeOperatorsRegistry;

    /// @notice Address of Lido's Staking Router contract
    IStakingRouter public immutable stakingRouter;

    /// @notice Address of ValidatorsExitBusOracle contract
    IValidatorsExitBusOracle public immutable validatorsExitBusOracle;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _stakingRouter,
        address _sdvtNodeOperatorsRegistry,
        address _validatorsExitBusOracle
    ) TrustedCaller(_trustedCaller) {
        sdvtNodeOperatorsRegistry = INodeOperatorsRegistry(_sdvtNodeOperatorsRegistry);
        stakingRouter = IStakingRouter(_stakingRouter);
        validatorsExitBusOracle = IValidatorsExitBusOracle(_validatorsExitBusOracle);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to submit exit requests to the Validators Exit Bus Oracle (SDVT module).
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded relays data: ValidatorSubmitExitHashesUtils.ExitRequestInput[]
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        ValidatorSubmitExitHashesUtils.ExitRequestInput[]
            memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        ValidatorSubmitExitHashesUtils.validateExitRequests(
            decodedCallData,
            sdvtNodeOperatorsRegistry,
            stakingRouter
        );

        return
            EVMScriptCreator.createEVMScript(
                address(validatorsExitBusOracle),
                IValidatorsExitBusOracle.submitExitRequestsHash.selector,
                abi.encode(ValidatorSubmitExitHashesUtils.hashExitRequests(decodedCallData))
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded relays data: ValidatorSubmitExitHashesUtils.ExitRequestInput[]
    /// @return Array of ExitRequestInput structs
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (ValidatorSubmitExitHashesUtils.ExitRequestInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (ValidatorSubmitExitHashesUtils.ExitRequestInput[] memory) {
        return abi.decode(_evmScriptCallData, (ValidatorSubmitExitHashesUtils.ExitRequestInput[]));
    }
}
