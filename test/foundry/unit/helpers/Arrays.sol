// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {IMEVBoostRelayAllowedList} from "contracts/interfaces/IMEVBoostRelayAllowedList.sol";
import {TierParams} from "contracts/interfaces/IOperatorGrid.sol";

/// @notice Memory arrays of one to three elements, the `[a, b]` literals of the Python tests
library Arrays {
    function list(address a) internal pure returns (address[] memory result) {
        result = new address[](1);
        result[0] = a;
    }

    function list(address a, address b) internal pure returns (address[] memory result) {
        result = new address[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(address a, address b, address c) internal pure returns (address[] memory result) {
        result = new address[](3);
        result[0] = a;
        result[1] = b;
        result[2] = c;
    }

    function list(uint256 a) internal pure returns (uint256[] memory result) {
        result = new uint256[](1);
        result[0] = a;
    }

    function list(uint256 a, uint256 b) internal pure returns (uint256[] memory result) {
        result = new uint256[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(uint256 a, uint256 b, uint256 c) internal pure returns (uint256[] memory result) {
        result = new uint256[](3);
        result[0] = a;
        result[1] = b;
        result[2] = c;
    }

    function list(bool a, bool b) internal pure returns (bool[] memory result) {
        result = new bool[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(bytes4 a) internal pure returns (bytes4[] memory result) {
        result = new bytes4[](1);
        result[0] = a;
    }

    function list(bytes4 a, bytes4 b) internal pure returns (bytes4[] memory result) {
        result = new bytes4[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(bytes4 a, bytes4 b, bytes4 c) internal pure returns (bytes4[] memory result) {
        result = new bytes4[](3);
        result[0] = a;
        result[1] = b;
        result[2] = c;
    }

    function list(bytes memory a) internal pure returns (bytes[] memory result) {
        result = new bytes[](1);
        result[0] = a;
    }

    function list(bytes memory a, bytes memory b) internal pure returns (bytes[] memory result) {
        result = new bytes[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(bytes memory a, bytes memory b, bytes memory c)
        internal
        pure
        returns (bytes[] memory result)
    {
        result = new bytes[](3);
        result[0] = a;
        result[1] = b;
        result[2] = c;
    }

    function list(string memory a) internal pure returns (string[] memory result) {
        result = new string[](1);
        result[0] = a;
    }

    function list(string memory a, string memory b) internal pure returns (string[] memory result) {
        result = new string[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(IMEVBoostRelayAllowedList.Relay memory a)
        internal
        pure
        returns (IMEVBoostRelayAllowedList.Relay[] memory result)
    {
        result = new IMEVBoostRelayAllowedList.Relay[](1);
        result[0] = a;
    }

    function list(
        IMEVBoostRelayAllowedList.Relay memory a,
        IMEVBoostRelayAllowedList.Relay memory b
    ) internal pure returns (IMEVBoostRelayAllowedList.Relay[] memory result) {
        result = new IMEVBoostRelayAllowedList.Relay[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(TierParams memory a) internal pure returns (TierParams[] memory result) {
        result = new TierParams[](1);
        result[0] = a;
    }

    function list(TierParams memory a, TierParams memory b)
        internal
        pure
        returns (TierParams[] memory result)
    {
        result = new TierParams[](2);
        result[0] = a;
        result[1] = b;
    }

    function list(TierParams[] memory a) internal pure returns (TierParams[][] memory result) {
        result = new TierParams[][](1);
        result[0] = a;
    }

    function list(TierParams[] memory a, TierParams[] memory b)
        internal
        pure
        returns (TierParams[][] memory result)
    {
        result = new TierParams[][](2);
        result[0] = a;
        result[1] = b;
    }
}
