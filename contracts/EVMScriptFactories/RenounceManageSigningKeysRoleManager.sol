// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

interface IACL {
    function removePermissionManager(address _app, bytes32 _role) external;

    function getPermissionManager(address _app, bytes32 _role) external view returns (address);
}

/// @notice Creates EVMScript to set node operators reward address
contract RenounceManageSigningKeysRoleManager is TrustedCaller, IEVMScriptFactory {
    // -------------
    // CONSTANTS
    // -------------
    /// @notice keccak256("MANAGE_SIGNING_KEYS")
    bytes32 private constant MANAGE_SIGNING_KEYS_ROLE =
        0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee;

    // -------------
    // ERRORS
    // -------------

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of NodeOperatorsRegistry contract
    address public immutable nodeOperatorsRegistry;
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
        nodeOperatorsRegistry = _nodeOperatorsRegistry;
        acl = IACL(_acl);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    function createEVMScript(
        address _creator,
        bytes memory _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        return
            EVMScriptCreator.createEVMScript(
                address(acl),
                acl.removePermissionManager.selector,
                abi.encode(nodeOperatorsRegistry, MANAGE_SIGNING_KEYS_ROLE)
            );
    }

    // function decodeEVMScriptCallData(
    //     bytes memory _evmScriptCallData
    // ) external pure returns (PermissionData[] memory) {
    //     return _decodeEVMScriptCallData(_evmScriptCallData);
    // }

    // // ------------------
    // // PRIVATE METHODS
    // // ------------------

    // function _decodeEVMScriptCallData(
    //     bytes memory _evmScriptCallData
    // ) private pure returns (PermissionData[] memory) {
    //     return abi.decode(_evmScriptCallData, (PermissionData[]));
    // }
}