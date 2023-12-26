// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to deactivate several node operators
contract DeactivateNodeOperators is TrustedCaller, IEVMScriptFactory {
    struct DeactivateNodeOperatorInput {
        uint256 nodeOperatorId;
        address managerAddress;
    }

    // -------------
    // CONSTANTS
    // -------------

    bytes4 private constant DEACTIVATE_NODE_OPERATOR_SELECTOR =
        bytes4(keccak256("deactivateNodeOperator(uint256)"));
    bytes4 private constant REVOKE_PERMISSION_SELECTOR =
        bytes4(keccak256("revokePermission(address,address,bytes32)"));
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;
    /// @notice Address of Aragon ACL contract
    IACL public immutable acl;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_WRONG_OPERATOR_ACTIVE_STATE = "WRONG_OPERATOR_ACTIVE_STATE";
    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_MANAGER_HAS_NO_ROLE = "MANAGER_HAS_NO_ROLE";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _nodeOperatorsRegistry,
        address _acl
    ) TrustedCaller(_trustedCaller) {
        nodeOperatorsRegistry = INodeOperatorsRegistry(_nodeOperatorsRegistry);
        acl = IACL(_acl);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to deactivate batch of node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (DeactivateNodeOperatorInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        DeactivateNodeOperatorInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        _validateInputData(decodedCallData);

        address[] memory toAddresses = new address[](decodedCallData.length * 2);
        bytes4[] memory methodIds = new bytes4[](decodedCallData.length * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length * 2);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            toAddresses[i * 2] = address(nodeOperatorsRegistry);
            methodIds[i * 2] = DEACTIVATE_NODE_OPERATOR_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(decodedCallData[i].nodeOperatorId);

            toAddresses[i * 2 + 1] = address(acl);
            methodIds[i * 2 + 1] = REVOKE_PERMISSION_SELECTOR;
            encodedCalldata[i * 2 + 1] = abi.encode(
                decodedCallData[i].managerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE
            );
        }

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (DeactivateNodeOperatorInput[])
    /// @return DeactivateNodeOperatorInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (DeactivateNodeOperatorInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (DeactivateNodeOperatorInput[] memory) {
        return abi.decode(_evmScriptCallData, (DeactivateNodeOperatorInput[]));
    }

    function _validateInputData(
        DeactivateNodeOperatorInput[] memory _decodedCallData
    ) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        require(_decodedCallData.length > 0, ERROR_EMPTY_CALLDATA);
        require(
            _decodedCallData[_decodedCallData.length - 1].nodeOperatorId < nodeOperatorsCount,
            ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
        );

        for (uint256 i = 0; i < _decodedCallData.length; ++i) {
            require(
                i == 0 ||
                    _decodedCallData[i].nodeOperatorId > _decodedCallData[i - 1].nodeOperatorId,
                ERROR_NODE_OPERATORS_IS_NOT_SORTED
            );
            require(
                nodeOperatorsRegistry.getNodeOperatorIsActive(_decodedCallData[i].nodeOperatorId) ==
                    true,
                ERROR_WRONG_OPERATOR_ACTIVE_STATE
            );

            require(
                acl.getPermissionParamsLength(
                    _decodedCallData[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 1,
                ERROR_MANAGER_HAS_NO_ROLE
            );

            // See https://legacy-docs.aragon.org/developers/tools/aragonos/reference-aragonos-3#parameter-interpretation for details
            (uint8 paramIndex, uint8 paramOp, uint240 param) = acl.getPermissionParam(
                _decodedCallData[i].managerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                0
            );

            require(paramIndex == 0, ERROR_MANAGER_HAS_NO_ROLE);
            require(paramOp == 1, ERROR_MANAGER_HAS_NO_ROLE);
            require(param == _decodedCallData[i].nodeOperatorId, ERROR_MANAGER_HAS_NO_ROLE);
        }
    }
}
