// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorRegestry.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to set node operators reward address
contract TransferNodeOperatorManager is TrustedCaller, IEVMScriptFactory {
    struct PermissionInput {
        uint256 nodeOperatorId;
        address oldManagerAddress;
        address newManagerAddress;
    }

    // -------------
    // CONSTANTS
    // -------------

    /// @notice keccak256("MANAGE_SIGNING_KEYS")
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;
    bytes4 private constant GRANT_PERMISSION_P_SELECTOR =
        bytes4(keccak256("grantPermissionP(address,address,bytes32,uint256[])"));
    bytes4 private constant REVOKE_PERMISSION_SELECTOR =
        bytes4(keccak256("revokePermission(address,address,bytes32)"));

    // -------------
    // ERRORS
    // -------------

    string private constant NODE_OPERATOR_INDEX_OUT_OF_RANGE = "NODE_OPERATOR_INDEX_OUT_OF_RANGE";
    string private constant OLD_MANAGER_HAS_NO_ROLE = "OLD_MANAGER_HAS_NO_ROLE";
    string private constant MANAGER_ALREADY_HAS_ROLE = "MANAGER_ALREADY_HAS_ROLE";
    string private constant MANAGER_ADDRESSES_HAS_DUPLICATE = "MANAGER_ADDRESSES_HAS_DUPLICATE";

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

    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        PermissionInput[] memory decodedCallData = _decodeEVMScriptCallData(_evmScriptCallData);

        address[] memory toAddresses = new address[](decodedCallData.length * 2);
        bytes4[] memory methodIds = new bytes4[](decodedCallData.length * 2);
        bytes[] memory encodedCalldata = new bytes[](decodedCallData.length * 2);

        _validateInputData(decodedCallData);

        for (uint i = 0; i < decodedCallData.length; i++) {
            toAddresses[i * 2] = address(acl);
            methodIds[i * 2] = REVOKE_PERMISSION_SELECTOR;
            encodedCalldata[i * 2] = abi.encode(
                decodedCallData[i].oldManagerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE
            );

            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + decodedCallData[i].nodeOperatorId;

            toAddresses[i * 2 + 1] = address(acl);
            methodIds[i * 2 + 1] = GRANT_PERMISSION_P_SELECTOR;
            encodedCalldata[i * 2 + 1] = abi.encode(
                decodedCallData[i].newManagerAddress,
                address(nodeOperatorsRegistry),
                MANAGE_SIGNING_KEYS_ROLE,
                permissionParams
            );
        }

        return EVMScriptCreator.createEVMScript(toAddresses, methodIds, encodedCalldata);
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (PermissionInput[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (PermissionInput[] memory) {
        return abi.decode(_evmScriptCallData, (PermissionInput[]));
    }

    function _validateInputData(PermissionInput[] memory _permissionInputs) private view {
        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();

        for (uint i = 0; i < _permissionInputs.length; i++) {
            require(
                _permissionInputs[i].nodeOperatorId < nodeOperatorsCount,
                NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );

            for (uint test_index = i + 1; test_index < _permissionInputs.length; test_index++) {
                require(
                    _permissionInputs[i].newManagerAddress !=
                        _permissionInputs[test_index].newManagerAddress,
                    MANAGER_ADDRESSES_HAS_DUPLICATE
                );
            }

            uint256[] memory permissionParams = new uint256[](1);
            permissionParams[0] = (1 << 240) + _permissionInputs[i].nodeOperatorId;
            require(
                acl.hasPermission(
                    _permissionInputs[i].oldManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE,
                    permissionParams
                ) == true,
                OLD_MANAGER_HAS_NO_ROLE
            );

            require(
                acl.hasPermission(
                    _permissionInputs[i].newManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == false,
                MANAGER_ALREADY_HAS_ROLE
            );
            require(
                acl.getPermissionParamsLength(
                    _permissionInputs[i].newManagerAddress,
                    address(nodeOperatorsRegistry),
                    MANAGE_SIGNING_KEYS_ROLE
                ) == 0,
                MANAGER_ALREADY_HAS_ROLE
            );
        }
    }
}
