// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Vm} from "forge-std/Vm.sol";

/// @notice Ports of `utils/test_helpers.py`
library TestHelpers {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    /// @dev python: access_revert_message. The OpenZeppelin v4 AccessControl reason. The account
    /// is lowercased because `vm.toString` checksums it and `Strings.toHexString` does not
    function accessRevertMessage(address sender, bytes32 role)
        internal
        pure
        returns (bytes memory)
    {
        return
            abi.encodePacked(
                "AccessControl: account ",
                vm.toLowercase(vm.toString(sender)),
                " is missing role ",
                vm.toString(role)
            );
    }
}
