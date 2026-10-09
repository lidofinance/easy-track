// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {TrustedCaller} from "contracts/TrustedCaller.sol";

contract TrustedCallerTest is Test {
    address internal owner = makeAddr("owner");
    address internal trustedCaller = makeAddr("trustedCaller");

    // python: test_deploy_zero_address
    function test_RevertWhen_TrustedCallerIsZeroAddress() external {
        vm.expectRevert("TRUSTED_CALLER_IS_ZERO_ADDRESS");
        new TrustedCaller(address(0));
    }

    // python: test_deploy
    function test_Deploy() external {
        vm.prank(owner);
        TrustedCaller trustedCallerContract = new TrustedCaller(trustedCaller);

        assertEq(trustedCallerContract.trustedCaller(), trustedCaller, "trustedCaller");
    }
}
