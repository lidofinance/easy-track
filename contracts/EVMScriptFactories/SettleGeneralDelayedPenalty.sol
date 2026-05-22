// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IBaseModule.sol";
import "../interfaces/IAccounting.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to settle general delayed penalty for a specific node operators
contract SettleGeneralDelayedPenalty is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_NODE_OPERATORS_IDS =
        "EMPTY_NODE_OPERATORS_IDS";
    string private constant ERROR_OUT_OF_RANGE_NODE_OPERATOR_ID =
        "OUT_OF_RANGE_NODE_OPERATOR_ID";
    string private constant ERROR_NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH =
        "NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH";
    string private constant ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED =
        "MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED";
    string private constant ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO =
        "MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Alias for factory (e.g. "CSMv3")
    string public name;

    /// @notice Address of Module Contract
    IBaseModule public immutable module;
    IAccounting public immutable accounting;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, string memory _name, address _module)
        TrustedCaller(_trustedCaller)
    {
        name = _name;
        module = IBaseModule(_module);
        accounting = IAccounting(IBaseModule(_module).ACCOUNTING());
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to settle general delayed penalty for the specific node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(nodeOperatorIds, maxAmounts);

        return
            EVMScriptCreator.createEVMScript(
                address(module),
                IBaseModule.settleGeneralDelayedPenalty.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts
    /// @return Node operator IDs and max amounts to settle general delayed penalty
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (uint256[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (uint256[], uint256[]));
    }

    function _validateInputData(
        uint256[] memory nodeOperatorsIds,
        uint256[] memory maxAmounts
    ) private view {
        require(nodeOperatorsIds.length > 0, ERROR_EMPTY_NODE_OPERATORS_IDS);
        require(
            nodeOperatorsIds.length == maxAmounts.length,
            ERROR_NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH
        );
        uint256 nodeOperatorsCount = module.getNodeOperatorsCount();
        for (uint256 i = 0; i < nodeOperatorsIds.length; ++i) {
            (uint256 nodeOperatorId, uint256 maxAmount) = (nodeOperatorsIds[i], maxAmounts[i]);
            require(nodeOperatorId < nodeOperatorsCount, ERROR_OUT_OF_RANGE_NODE_OPERATOR_ID);
            uint256 locked = accounting.getLockedBond(
                nodeOperatorId
            );
            require(maxAmount > 0, ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO);
            require(maxAmount >= locked, ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED);
        }
    }
}
