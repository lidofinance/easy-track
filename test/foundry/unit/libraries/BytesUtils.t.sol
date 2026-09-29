// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {BytesUtilsWrapper} from "contracts/test/BytesUtilsWrapper.sol";

/// @dev Every case reads a full 32-byte word past the end of the source, so the calls go through the
/// external wrapper, whose fresh call frame guarantees zeroed memory after the decoded argument.
contract BytesUtilsTest is Test {
    bytes internal constant SHORT_WORD = hex"00112233445566778899aabbccddeeff";
    bytes internal constant WORD =
        hex"00112233445566778899aabbccddeeff0102030405060708090a0b0c0d0f";

    address internal owner = makeAddr("owner");

    // python: test_bytes24_at[0]
    function test_Bytes24AtShortWordFromZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(SHORT_WORD, 0),
            bytes24(hex"00112233445566778899aabbccddeeff0000000000000000"),
            "bytes24At"
        );
    }

    // python: test_bytes24_at[1]
    function test_Bytes24AtShortWordFromNonZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(SHORT_WORD, 4),
            bytes24(hex"445566778899aabbccddeeff000000000000000000000000"),
            "bytes24At"
        );
    }

    // python: test_bytes24_at[2]
    function test_Bytes24AtLongWordFromZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(WORD, 0),
            bytes24(hex"00112233445566778899aabbccddeeff0102030405060708"),
            "bytes24At"
        );
    }

    // python: test_bytes24_at[3]
    function test_Bytes24AtLongWordFromNonZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(WORD, 6),
            bytes24(hex"66778899aabbccddeeff0102030405060708090a0b0c0d0f"),
            "bytes24At"
        );
    }

    // python: test_address_at[0]
    function test_AddressAtBareAddress() external view {
        assertEq(BytesUtilsWrapper.addressAt(abi.encodePacked(owner), 0), owner, "addressAt");
    }

    // python: test_address_at[1]
    function test_AddressAtWrappedAddress() external view {
        bytes memory wordWithBytes = abi.encodePacked(hex"00112233", owner, hex"ddeeff");

        assertEq(BytesUtilsWrapper.addressAt(wordWithBytes, 4), owner, "addressAt");
    }

    // python: test_uint32_at[0]
    function test_Uint32AtOne() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"00000001", 0), 1, "uint32At");
    }

    // python: test_uint32_at[1]
    function test_Uint32AtZero() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"00000000", 0), 0, "uint32At");
    }

    // python: test_uint32_at[2]
    function test_Uint32AtEmptyBytes() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"", 0), 0, "uint32At");
    }

    // python: test_uint32_at[3]
    function test_Uint32AtMaxValue() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"ffffffff", 0), type(uint32).max, "uint32At");
    }

    // python: test_uint32_at[4]
    function test_Uint32AtNonZeroPosition() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"ffffff00000010eeee", 3), 16, "uint32At");
    }

    // python: test_uint256_at[0]
    function test_Uint256AtOne() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"0000000000000000000000000000000000000000000000000000000000000001", 0
            ),
            1,
            "uint256At"
        );
    }

    // python: test_uint256_at[1]
    function test_Uint256AtZero() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"0000000000000000000000000000000000000000000000000000000000000000", 0
            ),
            0,
            "uint256At"
        );
    }

    // python: test_uint256_at[2]
    function test_Uint256AtEmptyBytes() external pure {
        assertEq(BytesUtilsWrapper.uint256At(hex"", 0), 0, "uint256At");
    }

    // python: test_uint256_at[3]
    function test_Uint256AtMaxValue() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 0
            ),
            type(uint256).max,
            "uint256At"
        );
    }

    // python: test_uint256_at[4]
    function test_Uint256AtLongWordFromNonZeroPosition() external pure {
        bytes memory longWord = abi.encodePacked(
            hex"aabbccdd", hex"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        );

        assertEq(BytesUtilsWrapper.uint256At(longWord, 4), type(uint256).max, "uint256At");
    }
}
