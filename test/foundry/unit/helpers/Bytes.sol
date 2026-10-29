// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice python: `int.to_bytes`
library Bytes {
    /// @dev python: `value.to_bytes(size, "big")`, which raises when the value does not fit
    function toBytes(uint256 value, uint256 size) internal pure returns (bytes memory result) {
        require(size <= 32 && value >> (8 * size) == 0, "value does not fit the size");

        result = new bytes(size);
        bytes32 word = bytes32(value);
        for (uint256 i; i < size; ++i) {
            result[i] = word[32 - size + i];
        }
    }
}
