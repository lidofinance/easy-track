// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to activate several node operators
contract ActivateNodeOperators is TrustedCaller, IEVMScriptFactory {
    struct ActivateNodeOperatorInput {
        uint256 nodeOperatorId;
        address managerAddress;
    }

    // -------------
    // CONSTANTS
    // -------------

    bytes4 private constant ACTIVATE_NODE_OPERATOR_SELECTOR =
        bytes4(keccak256("activateNodeOperator(uint256)"));
    bytes4 private constant GRANT_PERMISSION_P_SELECTOR =
        bytes4(keccak256("grantPermissionP(address,address,bytes32,uint256[])"));
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;
    /// @notice Address of Argon ACL contract
    IACL public immutable acl;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_WRONG_OPERATOR_ACTIVE_STATE = "WRONG_OPERATOR_ACTIVE_STATE";
    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_MANAGER_ALREADY_HAS_ROLE = "MANAGER_ALREADY_HAS_ROLE";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_ZERO_MANAGER_ADDRESS = "ZERO_MANAGER_ADDRESS";
    string private constant ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE =
        "MANAGER_ADDRESSES_HAS_DUPLICATE";
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

    /// @notice Creates EVMScript to activate batch of node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (ActivateNodeOperatorInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        ActivateNodeOperatorInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        _validateInputData(decodedCallData);

        address[] memory toAddresses = new address[](decodedCallData.length * 2);
        bytes4[] memory methodIds = new bytes4[](decodedCallData.length * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length * 2);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            toAddresses[i * 2] = address(nodeOperatorsRegistry);
            methodIds[i * 2] = ACTIVATE_NODE_OPERATOR_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(decodedCallData[i].nodeOperatorId);

            // See https://legacy-docs.aragon.org/developers/tools/aragonos/reference-aragonos-3#parameter-interpretation for details
            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + decodedCallData[i].nodeOperatorId;

            toAddresses[i * 2 + 1] = address(acl);
            methodIds[i * 2 + 1] = GRANT_PERMISSION_P_SELECTOR;
            encodedCalldata[i * 2 + 1] = abi.encode(
                decodedCallData[i].managerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                permissionParams
            );
        }

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (ActivateNodeOperatorInput[])
    /// @return ActivateNodeOperatorInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (ActivateNodeOperatorInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (ActivateNodeOperatorInput[] memory) {
        return abi.decode(_evmScriptCallData, (ActivateNodeOperatorInput[]));
    }

    function _validateInputData(ActivateNodeOperatorInput[] memory _decodedCallData) private view {
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
                    false,
                ERROR_WRONG_OPERATOR_ACTIVE_STATE
            );

            require(_decodedCallData[i].managerAddress != address(0), ERROR_ZERO_MANAGER_ADDRESS);

            address managerAddress = _decodedCallData[i].managerAddress;
            for (uint256 testIndex = i + 1; testIndex < _decodedCallData.length; ++testIndex) {
                require(
                    managerAddress != _decodedCallData[testIndex].managerAddress,
                    ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE
                );
            }

            require(
                acl.hasPermission(
                    _decodedCallData[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == false,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );
            require(
                acl.getPermissionParamsLength(
                    _decodedCallData[i].managerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 0,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );
        }
    }
}
