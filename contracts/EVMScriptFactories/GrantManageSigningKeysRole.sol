// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface INodeOperatorsRegistry {
    function getNodeOperatorsCount() external view returns (uint256);
}

interface IACL {
    function grantPermissionP(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external;
}

/// @notice Creates EVMScript to set node operators reward address
contract GrantManageSigningKeysRole is TrustedCaller, IEVMScriptFactory {
    struct PermissionData {
        uint256 nodeOperatorId;
        address manager;
    }

    struct PermissionParam {
        uint8 id;
        uint8 op;
        uint240 value;
    }

    // -------------
    // CONSTANTS
    // -------------
    /// @notice keccak256("MANAGE_SIGNING_KEYS")
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE =
        "NODE_OPERATOR_INDEX_OUT_OF_RANGE";

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
        PermissionData[] memory decodedCallData = abi.decode(
            _evmScriptCallData,
            (PermissionData[])
        );
        bytes[] memory permissionsCallData = new bytes[](decodedCallData.length);

        uint256 nodeOperatorsCount = nodeOperatorsRegistry.getNodeOperatorsCount();
        for (uint i = 0; i < decodedCallData.length; i++) {
            require(
                decodedCallData[i].nodeOperatorId < nodeOperatorsCount,
                ERROR_NODE_OPERATOR_INDEX_OUT_OF_RANGE
            );
            uint256[] memory params = new uint256[](1);
            params[0] = (1 << 240) + decodedCallData[i].nodeOperatorId;

            permissionsCallData[i] = abi.encode(
                decodedCallData[i].manager,
                nodeOperatorsRegistry,
                MANAGE_SIGNING_KEYS_ROLE,
                params
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(acl),
                acl.grantPermissionP.selector,
                permissionsCallData
            );
    }

    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (PermissionData[] memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (PermissionData[] memory) {
        return abi.decode(_evmScriptCallData, (PermissionData[]));
    }
}
