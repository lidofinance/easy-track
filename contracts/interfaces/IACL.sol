// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

interface IACL {
    function grantPermissionP(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external;

    function revokePermission(address _entity, address _app, bytes32 _role) external;

    function hasPermission(
        address _entity,
        address _app,
        bytes32 _role
    ) external view returns (bool);

    function hasPermission(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external view returns (bool);

    function getPermissionParamsLength(
        address _entity,
        address _app,
        bytes32 _role
    ) external view returns (uint256);

    function getPermissionParam(
        address _entity,
        address _app,
        bytes32 _role,
        uint256 _index
    ) external view returns (uint8, uint8, uint240);

    function getPermissionManager(address _app, bytes32 _role) external view returns (address);

    function removePermissionManager(address _app, bytes32 _role) external;
}
