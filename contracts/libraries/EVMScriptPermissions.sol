// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./BytesUtils.sol";

library EVMScriptPermissions {
    using BytesUtils for bytes;
    uint256 private constant PERMISSION_LENGTH = 24;

    function validatePermissions(bytes memory _permissions) external pure {
        _validatePermissions(_permissions);
    }

    function canExecuteEVMScript(bytes memory _permissions, bytes memory _evmScript)
        external
        pure
        returns (bool)
    {
        _validatePermissions(_permissions);
        require(_evmScript.length > 4, "EMPTY_EVM_SCRIPT");

        uint256 location = 4; // first 4 bytes reserved for SPEC_ID
        while (location < _evmScript.length) {
            (bytes24 methodToCall, uint32 callDataLength) = _getNextMethodId(_evmScript, location);
            if (!_hasPermission(_permissions, methodToCall)) {
                return false;
            }
            location += PERMISSION_LENGTH + callDataLength;
        }
        return true;
    }

    function _validatePermissions(bytes memory _permissions) private pure {
        require(_permissions.length > 0, "EMPTY_PERMISSIONS");
        require(_permissions.length % PERMISSION_LENGTH == 0, "INVALID_PERMISSIONS_LEGNTH");
    }

    function _getNextMethodId(bytes memory _evmScript, uint256 _location)
        public
        pure
        returns (bytes24, uint32)
    {
        address recipient = _evmScript.addressAt(_location);
        uint32 methodId = _evmScript.uint32At(_location + 24);
        uint32 callDataLength = _evmScript.uint32At(_location + 20);
        return (bytes24(uint192(methodId)) | bytes20(recipient), callDataLength);
    }

    function _hasPermission(bytes memory _permissions, bytes24 _methodToCall)
        public
        pure
        returns (bool)
    {
        uint256 location = 0;
        while (location < _permissions.length) {
            bytes24 permission = _permissions.bytes24At(location);
            if (permission == _methodToCall) {
                return true;
            }
            location += PERMISSION_LENGTH;
        }
        return false;
    }
}
