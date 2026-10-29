// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Stands in for the deployed aragonOS v4 ACL the node operator factories read.
/// @dev Keeps what the factories depend on: the permission store with its parameters and the
/// three getters. There is no permission manager, anyone grants and revokes.
contract ACLStub {
    struct Permission {
        bool granted;
        uint256[] params;
    }

    mapping(bytes32 => Permission) private _permissions;

    function grantPermission(address _entity, address _app, bytes32 _role) external {
        _setPermission(_entity, _app, _role, new uint256[](0));
    }

    function grantPermissionP(
        address _entity,
        address _app,
        bytes32 _role,
        uint256[] memory _params
    ) external {
        _setPermission(_entity, _app, _role, _params);
    }

    function revokePermission(address _entity, address _app, bytes32 _role) external {
        delete _permissions[_permissionHash(_entity, _app, _role)];
    }

    /// @dev aragonOS evaluates the parameters against the guarded call's arguments and this
    /// overload passes none, so only an unparametrized permission holds
    function hasPermission(address _entity, address _app, bytes32 _role)
        external
        view
        returns (bool)
    {
        Permission storage permission = _permissions[_permissionHash(_entity, _app, _role)];
        return permission.granted && permission.params.length == 0;
    }

    function getPermissionParamsLength(address _entity, address _app, bytes32 _role)
        external
        view
        returns (uint256)
    {
        return _permissions[_permissionHash(_entity, _app, _role)].params.length;
    }

    function getPermissionParam(address _entity, address _app, bytes32 _role, uint256 _index)
        external
        view
        returns (uint8 id, uint8 op, uint240 value)
    {
        uint256 param = _permissions[_permissionHash(_entity, _app, _role)].params[_index];
        id = uint8(param >> 248);
        op = uint8(param >> 240);
        value = uint240(param);
    }

    function _setPermission(address _entity, address _app, bytes32 _role, uint256[] memory _params)
        private
    {
        _permissions[_permissionHash(_entity, _app, _role)] = Permission(true, _params);
    }

    /// @dev aragonOS: `keccak256(abi.encodePacked("PERMISSION", _who, _where, _what))`
    function _permissionHash(address _entity, address _app, bytes32 _role)
        private
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked("PERMISSION", _entity, _app, _role));
    }
}
