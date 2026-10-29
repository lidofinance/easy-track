// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Bytes} from "test/foundry/unit/helpers/Bytes.sol";

/// @notice Byte encoders the Python suite takes from `utils/evm_script.py` and `utils/deployment.py`
library EVMScripts {
    /// @dev Id of the Aragon CallsScript executor
    bytes4 internal constant SPEC_ID = hex"00000001";

    /// @dev An Aragon CallsScript: SPEC_ID, then per call `target ‖ uint32(data.length) ‖ data`
    function encodeCallScript(address[] memory targets, bytes[] memory datas)
        internal
        pure
        returns (bytes memory script)
    {
        require(targets.length == datas.length, "EVMScripts: LENGTH_MISMATCH");

        script = abi.encodePacked(SPEC_ID);
        for (uint256 i; i < targets.length; ++i) {
            script = bytes.concat(
                script, bytes20(targets[i]), Bytes.toBytes(datas[i].length, 4), datas[i]
            );
        }
    }

    /// @dev Single-call form of `encodeCallScript`
    function encodeCallScript(address target, bytes memory data)
        internal
        pure
        returns (bytes memory)
    {
        return bytes.concat(SPEC_ID, bytes20(target), Bytes.toBytes(data.length, 4), data);
    }

    /// @dev `encodeCallScript` with every call to one target
    function encodeCallScript(address target, bytes[] memory datas)
        internal
        pure
        returns (bytes memory script)
    {
        script = abi.encodePacked(SPEC_ID);
        for (uint256 i; i < datas.length; ++i) {
            script =
                bytes.concat(script, bytes20(target), Bytes.toBytes(datas[i].length, 4), datas[i]);
        }
    }

    /// @dev One `evmScriptFactoryPermissions` entry: `target ‖ selector`
    function createPermission(address target, bytes4 selector)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(target, selector);
    }
}
