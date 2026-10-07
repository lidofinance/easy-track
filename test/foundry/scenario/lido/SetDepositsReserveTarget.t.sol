// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {ILido} from "test/foundry/interfaces/External.sol";
import {ISetDepositsReserveTarget} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `SetDepositsReserveTarget` of `deployed-<chain>.json`: a motion sets the
///         deposits reserve target of Lido. Skipped on a chain without the factory.
contract SetDepositsReserveTargetTest is EasyTrackScenarioBase {
    string internal constant FACTORY_KEY = "SetDepositsReserveTarget";

    /// @dev How far a motion raises the target, within the factory's maximum
    uint256 internal constant TARGET_INCREASE = 1 ether;

    ISetDepositsReserveTarget internal factory;
    ILido internal lido;

    function setUp() public {
        _forkAndInitialize();

        vm.skip(
            !vm.keyExistsJson(
                vm.readFile(config.artifact), string.concat('.["', FACTORY_KEY, '"]')
            ),
            string.concat(FACTORY_KEY, " is not deployed in ", config.artifact)
        );

        factory = ISetDepositsReserveTarget(_factoryAddress(config.artifact, FACTORY_KEY));
        lido = ILido(factory.lido());

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    // python: test_set_deposits_reserve_target_via_motion
    function testFork_SetsDepositsReserveTarget() external {
        uint256 newTarget = lido.getDepositsReserveTarget() + TARGET_INCREASE;

        assertLe(
            newTarget,
            factory.MAX_DEPOSITS_RESERVE_TARGET(),
            "setup: room below MAX_DEPOSITS_RESERVE_TARGET"
        );

        _enact(abi.encode(newTarget));

        assertEq(lido.getDepositsReserveTarget(), newTarget, "getDepositsReserveTarget");
    }

    // python: test_reverts_on_motion_creation_if_target_is_unchanged
    function testFork_RevertWhen_TargetIsUnchanged() external {
        bytes memory callData = abi.encode(lido.getDepositsReserveTarget());

        vm.prank(creator);
        vm.expectRevert("SAME_DEPOSITS_RESERVE_TARGET");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    // python: test_reverts_on_motion_creation_if_target_is_too_high
    function testFork_RevertWhen_TargetIsTooHigh() external {
        bytes memory callData = abi.encode(factory.MAX_DEPOSITS_RESERVE_TARGET() + 1);

        vm.prank(creator);
        vm.expectRevert("DEPOSITS_RESERVE_TARGET_TOO_HIGH");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    // python: test_reverts_on_motion_creation_if_creator_is_not_trusted
    function testFork_RevertWhen_CreatorIsNotTrusted() external {
        // the target is valid, the caller is the only failing check
        bytes memory callData = abi.encode(factory.MAX_DEPOSITS_RESERVE_TARGET());

        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        easyTrack.createMotion(evmScriptFactory, callData);
    }
}
