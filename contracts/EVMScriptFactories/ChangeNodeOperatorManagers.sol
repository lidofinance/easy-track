// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to change signing keys manager for several node operators
contract ChangeNodeOperatorManagers is TrustedCaller, IEVMScriptFactory {
    struct ChangeNodeOperatorManagersInput {
        uint256 nodeOperatorId;
        address oldManagerAddress;
        address newManagerAddress;
    }

    // -------------
    // CONSTANTS
    // -------------

    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE = keccak256("MANAGE_SIGNING_KEYS");
    bytes4 private constant GRANT_PERMISSION_P_SELECTOR =
        bytes4(keccak256("grantPermissionP(address,address,bytes32,uint256[])"));
    bytes4 private constant REVOKE_PERMISSION_SELECTOR =
        bytes4(keccak256("revokePermission(address,address,bytes32)"));

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant ERROR_OLD_MANAGER_HAS_NO_ROLE = "OLD_MANAGER_HAS_NO_ROLE";
    string private constant ERROR_MANAGER_ALREADY_HAS_ROLE = "MANAGER_ALREADY_HAS_ROLE";
    string private constant ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE =
        "MANAGER_ADDRESSES_HAS_DUPLICATE";
    string private constant ERROR_NODE_OPERATORS_IS_NOT_SORTED = "NODE_OPERATORS_IS_NOT_SORTED";
    string private constant ERROR_ZERO_MANAGER_ADDRESS = "ZERO_MANAGER_ADDRESS";
    string private constant ERROR_EMPTY_CALLDATA = "EMPTY_CALLDATA";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    INodeOperatorsRegistry public immutable nodeOperatorsRegistry;
    /// @notice Address of Aragon ACL contract
    IACL public immutable acl;

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

    /// @notice Creates EVMScript to change managers of several node operators
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (ChangeNodeOperatorManagersInput[])
    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        ChangeNodeOperatorManagersInput[] memory decodedCallData = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        bytes4[] memory methodIds = new bytes4[](decodedCallData.length * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length * 2);

        _validateInputData(decodedCallData);

        for (uint256 i = 0; i < decodedCallData.length; ++i) {
            methodIds[i * 2] = REVOKE_PERMISSION_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(
                decodedCallData[i].oldManagerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE
            );

            // See https://legacy-docs.aragon.org/developers/tools/aragonos/reference-aragonos-3#parameter-interpretation for details
            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + decodedCallData[i].nodeOperatorId;
            methodIds[i * 2 + 1] = GRANT_PERMISSION_P_SELECTOR;
            encodedCalldata[i * 2 + 1] = abi.encode(
                decodedCallData[i].newManagerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                permissionParams
            );
        }

        return EVMScriptCreator.createEVMScript(address(acl), methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (ChangeNodeOperatorManagersInput[])
    /// @return ChangeNodeOperatorManagersInput[]
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (ChangeNodeOperatorManagersInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (ChangeNodeOperatorManagersInput[] memory) {
        return abi.decode(_evmScriptCallData, (ChangeNodeOperatorManagersInput[]));
    }

    function _validateInputData(
        ChangeNodeOperatorManagersInput[] memory _decodedCallData
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

            address managerAddress = _decodedCallData[i].newManagerAddress;
            for (uint256 testIndex = i + 1; testIndex < _decodedCallData.length; ++testIndex) {
                require(
                    managerAddress != _decodedCallData[testIndex].newManagerAddress,
                    ERROR_MANAGER_ADDRESSES_HAS_DUPLICATE
                );
            }
            require(
                acl.getPermissionParamsLength(
                    _decodedCallData[i].oldManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 1,
                ERROR_OLD_MANAGER_HAS_NO_ROLE
            );

            // See https://legacy-docs.aragon.org/developers/tools/aragonos/reference-aragonos-3#parameter-interpretation for details
            (uint8 paramIndex, uint8 paramOp, uint240 param) = acl.getPermissionParam(
                _decodedCallData[i].oldManagerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                0
            );

            require(paramIndex == 0, ERROR_OLD_MANAGER_HAS_NO_ROLE);
            require(paramOp == 1, ERROR_OLD_MANAGER_HAS_NO_ROLE);
            require(param == _decodedCallData[i].nodeOperatorId, ERROR_OLD_MANAGER_HAS_NO_ROLE);

            require(
                _decodedCallData[i].newManagerAddress != address(0),
                ERROR_ZERO_MANAGER_ADDRESS
            );

            require(
                acl.hasPermission(
                    _decodedCallData[i].newManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == false,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );
            require(
                acl.getPermissionParamsLength(
                    _decodedCallData[i].newManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 0,
                ERROR_MANAGER_ALREADY_HAS_ROLE
            );
        }
    }
}
