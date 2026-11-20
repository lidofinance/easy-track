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

    function test_ReadsBytes24AtShortWordFromZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(SHORT_WORD, 0),
            bytes24(hex"00112233445566778899aabbccddeeff0000000000000000"),
            "bytes24At"
        );
    }

    function test_ReadsBytes24AtShortWordFromNonZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(SHORT_WORD, 4),
            bytes24(hex"445566778899aabbccddeeff000000000000000000000000"),
            "bytes24At"
        );
    }

    function test_ReadsBytes24AtLongWordFromZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(WORD, 0),
            bytes24(hex"00112233445566778899aabbccddeeff0102030405060708"),
            "bytes24At"
        );
    }

    function test_ReadsBytes24AtLongWordFromNonZeroPosition() external pure {
        assertEq(
            BytesUtilsWrapper.bytes24At(WORD, 6),
            bytes24(hex"66778899aabbccddeeff0102030405060708090a0b0c0d0f"),
            "bytes24At"
        );
    }

    function test_ReadsAddressAtBareAddress() external view {
        assertEq(BytesUtilsWrapper.addressAt(abi.encodePacked(owner), 0), owner, "addressAt");
    }

    function test_ReadsAddressAtWrappedAddress() external view {
        bytes memory wordWithBytes = abi.encodePacked(hex"00112233", owner, hex"ddeeff");

        assertEq(BytesUtilsWrapper.addressAt(wordWithBytes, 4), owner, "addressAt");
    }

    function test_ReadsUint32AtOne() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"00000001", 0), 1, "uint32At");
    }

    function test_ReadsUint32AtZero() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"00000000", 0), 0, "uint32At");
    }

    function test_ReadsUint32AtEmptyBytes() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"", 0), 0, "uint32At");
    }

    function test_ReadsUint32AtMaxValue() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"ffffffff", 0), type(uint32).max, "uint32At");
    }

    function test_ReadsUint32AtNonZeroPosition() external pure {
        assertEq(BytesUtilsWrapper.uint32At(hex"ffffff00000010eeee", 3), 16, "uint32At");
    }

    function test_ReadsUint256AtOne() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"0000000000000000000000000000000000000000000000000000000000000001", 0
            ),
            1,
            "uint256At"
        );
    }

    function test_ReadsUint256AtZero() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"0000000000000000000000000000000000000000000000000000000000000000", 0
            ),
            0,
            "uint256At"
        );
    }

    function test_ReadsUint256AtEmptyBytes() external pure {
        assertEq(BytesUtilsWrapper.uint256At(hex"", 0), 0, "uint256At");
    }

    function test_ReadsUint256AtMaxValue() external pure {
        assertEq(
            BytesUtilsWrapper.uint256At(
                hex"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", 0
            ),
            type(uint256).max,
            "uint256At"
        );
    }

    function test_ReadsUint256AtLongWordFromNonZeroPosition() external pure {
        bytes memory longWord = abi.encodePacked(
            hex"aabbccdd", hex"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        );

        assertEq(BytesUtilsWrapper.uint256At(longWord, 4), type(uint256).max, "uint256At");
    }
}
