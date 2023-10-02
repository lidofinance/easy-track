// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IACL.sol";

/// @notice Creates EVMScript to renounce manager of MANAGE_SIGNING_KEYS role
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
}