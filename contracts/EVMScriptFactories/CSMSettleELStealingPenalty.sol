// SPDX-FileCopyrightText: 2024 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/ICSModule.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to settle EL stealing penalty for a specific node operators on CSM
contract CSMSettleElStealingPenalty is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATORS_IDS_IS_EMPTY =
        "NODE_OPERATORS_IDS_IS_EMPTY";
    string private constant ERROR_NODE_OPERATOR_ID_IS_OUT_OF_RANGE =
        "NODE_OPERATOR_ID_IS_OUT_OF_RANGE";
    string private constant ERROR_NODE_OPERATORS_IDS_ARE_NOT_SORTED =
        "NODE_OPERATORS_IDS_ARE_NOT_SORTED";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of CSModule
    ICSModule public immutable csm;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _csm)
        TrustedCaller(_trustedCaller)
    {
        csm = ICSModule(_csm);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to settle EL stealing penalty for a specific node operators on CSM
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        uint256[] memory nodeOperatorIds = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(nodeOperatorIds);

        return
            EVMScriptCreator.createEVMScript(
                address(csm),
                ICSModule.settleELRewardsStealingPenalty.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds
    /// @return Node operator IDs to settle EL stealing penalty
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (uint256[]));
    }

    function _validateInputData(
        uint256[] memory _decodedCallData
    ) private view {
        uint256 nodeOperatorsCount = csm.getNodeOperatorsCount();
        require(_decodedCallData.length > 0, ERROR_NODE_OPERATORS_IDS_IS_EMPTY);
        require(
            _decodedCallData[_decodedCallData.length - 1] < nodeOperatorsCount,
            ERROR_NODE_OPERATOR_ID_IS_OUT_OF_RANGE
        );
        for (uint256 i = 0; i < _decodedCallData.length; ++i) {
            require(
                i == 0 ||
                    _decodedCallData[i] > _decodedCallData[i - 1],
                ERROR_NODE_OPERATORS_IDS_ARE_NOT_SORTED
            );
        }
    }
}
