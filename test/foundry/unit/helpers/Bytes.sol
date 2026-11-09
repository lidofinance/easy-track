// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

library Bytes {
    /// @dev Big-endian encoding of `value` in `size` bytes, reverting when it does not fit
    function toBytes(uint256 value, uint256 size) internal pure returns (bytes memory result) {
        require(size <= 32 && value >> (8 * size) == 0, "value does not fit the size");

        result = new bytes(size);
        bytes32 word = bytes32(value);
        for (uint256 i; i < size; ++i) {
            result[i] = word[32 - size + i];
        }
    }
}
