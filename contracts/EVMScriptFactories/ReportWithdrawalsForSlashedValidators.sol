// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {TrustedCaller} from "../TrustedCaller.sol";
import {EVMScriptCreator} from "../libraries/EVMScriptCreator.sol";
import {IEVMScriptFactory} from "../interfaces/IEVMScriptFactory.sol";
import {IBaseModule, WithdrawnValidatorInfo} from "../interfaces/IBaseModule.sol";

/// @notice Creates an EVMScript to report slashed validators as withdrawn to a CSM-like module.
contract ReportWithdrawalsForSlashedValidators is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_VALIDATOR_INFO_LIST = "EMPTY_VALIDATOR_INFO_LIST";
    string private constant ERROR_OPERATOR_DOES_NOT_EXIST = "OPERATOR_DOES_NOT_EXIST";
    string private constant ERROR_VALIDATOR_NOT_SLASHED = "VALIDATOR_NOT_SLASHED";
    string private constant ERROR_ZERO_EXIT_BALANCE = "ZERO_EXIT_BALANCE";
    string private constant ERROR_INVALID_SLASHING_PENALTY = "INVALID_SLASHING_PENALTY";

    // -------------
    // VARIABLES
    // -------------

    // @notice Alias for the factory.
    string public name;

    /// @notice Address of the module.
    IBaseModule public immutable module;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        string memory _name,
        address _module
    ) TrustedCaller(_trustedCaller) {
        name = _name;
        module = IBaseModule(_module);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript to report slashed validators as withdrawn to a CSM-like module.
    /// @param _creator Address who creates EVMScript.
    /// @param _evmScriptCallData Encoded (WithdrawnValidatorInfo[]).
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        WithdrawnValidatorInfo[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        _validateInputData(decodedCallData);

        return
            EVMScriptCreator.createEVMScript(
                address(module),
                module.reportSlashedWithdrawnValidators.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (WithdrawnValidatorInfo[])
    /// @return WithdrawnValidatorInfo[]
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (WithdrawnValidatorInfo[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (WithdrawnValidatorInfo[] memory)
    {
        return abi.decode(_evmScriptCallData, (WithdrawnValidatorInfo[]));
    }

    function _validateInputData(WithdrawnValidatorInfo[] memory _decodedCallData) private view {
        require(_decodedCallData.length > 0, ERROR_EMPTY_VALIDATOR_INFO_LIST);

        uint256 nosCount = module.getNodeOperatorsCount();
        for (uint256 i; i < _decodedCallData.length; ++i) {
            require(_decodedCallData[i].nodeOperatorId < nosCount, ERROR_OPERATOR_DOES_NOT_EXIST);
            require(_decodedCallData[i].exitBalance > 0, ERROR_ZERO_EXIT_BALANCE);
            require(_decodedCallData[i].isSlashed, ERROR_VALIDATOR_NOT_SLASHED);
            require(_decodedCallData[i].slashingPenalty > 0, ERROR_INVALID_SLASHING_PENALTY);
        }
    }
}
