// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/ICSModule.sol";
import "../interfaces/ICSAccounting.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to settle EL stealing penalty for a specific node operators on CSM
contract CSMSettleElStealingPenalty is TrustedCaller, IEVMScriptFactory {

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

    /// @notice Address of CSModule
    ICSModule public immutable csm;
    ICSAccounting public immutable accounting;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _csm)
        TrustedCaller(_trustedCaller)
    {
        csm = ICSModule(_csm);
        accounting = ICSAccounting(ICSModule(_csm).ACCOUNTING());
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to settle EL stealing penalty for the specific node operators on CSM
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
                address(csm),
                ICSModule.settleELRewardsStealingPenalty.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts
    /// @return Node operator IDs and max amounts to settle EL stealing penalty
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
        uint256 nodeOperatorsCount = csm.getNodeOperatorsCount();
        for (uint256 i = 0; i < nodeOperatorsIds.length; ++i) {
            (uint256 nodeOperatorId, uint256 maxAmount) = (nodeOperatorsIds[i], maxAmounts[i]);
            require(nodeOperatorId < nodeOperatorsCount, ERROR_OUT_OF_RANGE_NODE_OPERATOR_ID);
            uint256 actualLocked = accounting.getActualLockedBond(
                nodeOperatorId
            );
            require(maxAmount > 0, ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO);
            require(maxAmount >= actualLocked, ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED);
        }
    }
}
