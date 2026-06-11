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
    struct LockInfo {
        uint256 nodeOperatorId;
        uint256 maxAmount;
        uint256 until;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_EMPTY_LOCK_INFO_LIST = "EMPTY_LOCK_INFO_LIST";
    string private constant ERROR_OUT_OF_RANGE_NODE_OPERATOR_ID = "OUT_OF_RANGE_NODE_OPERATOR_ID";
    string private constant ERROR_NODE_OPERATORS_OUT_OF_ORDER = "NODE_OPERATORS_OUT_OF_ORDER";
    string private constant ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED =
        "MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED";
    string private constant ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO =
        "MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO";
    string private constant ERROR_OUTDATED_LOCK_SETTLE = "OUTDATED_LOCK_SETTLE";

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

    constructor(
        address _trustedCaller,
        string memory _name,
        address _module
    ) TrustedCaller(_trustedCaller) {
        name = _name;
        module = IBaseModule(_module);
        accounting = IAccounting(IBaseModule(_module).ACCOUNTING());
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to settle general delayed penalty for the specific node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: LockInfo[]
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        LockInfo[] memory lockInfoList = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(lockInfoList);

        uint256[] memory nodeOperatorIds = new uint256[](lockInfoList.length);
        uint256[] memory maxAmounts = new uint256[](lockInfoList.length);

        for (uint256 i; i < lockInfoList.length; i++) {
            nodeOperatorIds[i] = lockInfoList[i].nodeOperatorId;
            maxAmounts[i] = lockInfoList[i].maxAmount;
        }

        return
            EVMScriptCreator.createEVMScript(
                address(module),
                IBaseModule.settleGeneralDelayedPenalty.selector,
                abi.encode(nodeOperatorIds, maxAmounts)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: uint256[] memory nodeOperatorIds, uint256[] memory maxAmounts
    /// @return Node operator IDs and max amounts to settle general delayed penalty
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (LockInfo[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (LockInfo[] memory)
    {
        return abi.decode(_evmScriptCallData, (LockInfo[]));
    }

    function _validateInputData(LockInfo[] memory lockInfoList) private view {
        require(lockInfoList.length > 0, ERROR_EMPTY_LOCK_INFO_LIST);
        uint256 nodeOperatorsCount = module.getNodeOperatorsCount();
        for (uint256 i = 0; i < lockInfoList.length; ++i) {
            LockInfo memory info = lockInfoList[i];
            require(
                i == 0 || info.nodeOperatorId > lockInfoList[i - 1].nodeOperatorId,
                ERROR_NODE_OPERATORS_OUT_OF_ORDER
            );
            require(info.nodeOperatorId < nodeOperatorsCount, ERROR_OUT_OF_RANGE_NODE_OPERATOR_ID);
            IAccounting.BondLockData memory lockData = accounting.getLockedBondInfo(
                info.nodeOperatorId
            );
            require(info.maxAmount > 0, ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO);
            require(
                info.maxAmount >= lockData.amount,
                ERROR_MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED
            );
            require(info.until == lockData.until, ERROR_OUTDATED_LOCK_SETTLE);
        }
    }
}
