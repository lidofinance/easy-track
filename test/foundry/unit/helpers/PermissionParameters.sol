// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @dev python: Op, the aragonOS ACL comparison operators
enum Op {
    NONE,
    EQ,
    NEQ,
    GT,
    LT,
    GTE,
    LTE,
    RET,
    NOT,
    AND,
    OR,
    XOR,
    IF_ELSE
}

/// @dev python: Param, one aragonOS ACL permission parameter. `id` is the index of the guarded
/// call's argument that `value` is compared with, the ids from 200 up are the ACL's special ones
struct Param {
    uint8 id;
    Op op;
    uint256 value;
}

/// @notice Ports of `utils/permission_parameters.py`
library PermissionParameters {
    /// @dev python: Param.to_uint256. `id`, `op` and `value` packed as 8, 8 and 240 bits
    function toUint256(Param memory param) internal pure returns (uint256) {
        return
            (uint256(param.id) << 248) + (uint256(param.op) << 240)
                + (param.value & type(uint240).max);
    }

    /// @dev python: encode_permission_params
    function encodePermissionParams(Param[] memory params)
        internal
        pure
        returns (uint256[] memory encoded)
    {
        encoded = new uint256[](params.length);
        for (uint256 i; i < params.length; ++i) {
            encoded[i] = toUint256(params[i]);
        }
    }

    /// @dev `encodePermissionParams` of a single parameter
    function encodePermissionParams(Param memory param)
        internal
        pure
        returns (uint256[] memory encoded)
    {
        encoded = new uint256[](1);
        encoded[0] = toUint256(param);
    }
}
