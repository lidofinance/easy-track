// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/ICSModule.sol";

/// @notice Creates an EVMScript to report withdrawals to a CSM-like module.
contract SubmitWithdrawals is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_WITHDRAWAL_LIST = "EMPTY_WITHDRAWAL_LIST";
    string private constant ERROR_ZERO_EXIT_BALANCE = "ZERO_EXIT_BALANCE";
    string private constant ERROR_OPERATOR_DOES_NOT_EXIST = "OPERATOR_DOES_NOT_EXIST";

    // -------------
    // VARIABLES
    // -------------

    // @notice Alias for the factory.
    string public name;

    /// @notice Address of the module.
    ICSModule public immutable module;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        string memory _name,
        address _module
    ) TrustedCaller(_trustedCaller) {
        name = _name;
        module = ICSModule(_module);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript to report withdrawals to a CSM-like module.
    /// @param _creator Address who creates EVMScript.
    /// @param _evmScriptCallData Encoded (ValidatorWithdrawalInfo[]).
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        ValidatorWithdrawalInfo[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        _validateInputData(decodedCallData);

        return
            EVMScriptCreator.createEVMScript(
                address(module),
                module.submitWithdrawals.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (ValidatorWithdrawalInfo[])
    /// @return ValidatorWithdrawalInfo[]
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (ValidatorWithdrawalInfo[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (ValidatorWithdrawalInfo[] memory)
    {
        return abi.decode(_evmScriptCallData, (ValidatorWithdrawalInfo[]));
    }

    function _validateInputData(ValidatorWithdrawalInfo[] memory _decodedCallData) private view {
        require(_decodedCallData.length > 0, ERROR_EMPTY_WITHDRAWAL_LIST);

        uint256 nosCount = module.getNodeOperatorsCount();
        for (uint256 i; i < _decodedCallData.length; ++i) {
            require(_decodedCallData[i].nodeOperatorId < nosCount, ERROR_OPERATOR_DOES_NOT_EXIST);
            require(_decodedCallData[i].exitBalance > 0, ERROR_ZERO_EXIT_BALANCE);
        }
    }
}
