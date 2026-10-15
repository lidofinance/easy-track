// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {ILido, ILidoLocator} from "test/foundry/interfaces/External.sol";
import {ISetDepositsReserveTarget} from "test/foundry/interfaces/Factories.sol";

/// @notice A fresh `SetDepositsReserveTarget` from the `contracts` profile artifacts over the
///         live Lido, registered in the deployed Easy Track with the executor holding
///         `BUFFER_RESERVE_MANAGER_ROLE`. Skipped on a chain whose Lido has no deposits reserve
///         target.
contract SetDepositsReserveTargetHappyPathTest is EasyTrackScenarioBase {
    string internal constant FACTORY_NAME = "SetDepositsReserveTarget";

    /// @dev How far the factory's maximum sits above the current target
    uint256 internal constant DEPOSITS_RESERVE_TARGET_INCREASE = 100e18;

    bytes32 internal constant BUFFER_RESERVE_MANAGER_ROLE =
        keccak256("BUFFER_RESERVE_MANAGER_ROLE");

    ISetDepositsReserveTarget internal factory;
    ILido internal lido;

    function setUp() public {
        _forkAndInitialize();

        lido = ILido(ILidoLocator(config.locator).lido());

        vm.skip(!_hasDepositsReserveTarget(), "Lido has no deposits reserve target on this chain");

        creator = makeAddr("trustedCaller");

        vm.label(address(lido), "Lido");

        factory = ISetDepositsReserveTarget(
            _deployArtifact(
                FACTORY_NAME,
                abi.encode(
                    creator,
                    lido.getDepositsReserveTarget() + DEPOSITS_RESERVE_TARGET_INCREASE,
                    lido
                )
            )
        );
        evmScriptFactory = address(factory);

        if (!_acl().hasPermission(evmScriptExecutor, address(lido), BUFFER_RESERVE_MANAGER_ROLE)) {
            _grantPermission(evmScriptExecutor, address(lido), BUFFER_RESERVE_MANAGER_ROLE);
        }

        _registerFactory(
            evmScriptFactory, abi.encodePacked(lido, ILido.setDepositsReserveTarget.selector)
        );
    }

    // python: test_set_deposits_reserve_target_motion_happy_path
    function testFork_SetsTargetToMaxThenToZero() external {
        uint256 initialTarget = lido.getDepositsReserveTarget();
        uint256 maxTarget = factory.MAX_DEPOSITS_RESERVE_TARGET();

        _setTargetByMotion(maxTarget);
        _setTargetByMotion(0);

        assertNotEq(initialTarget, maxTarget, "the first target is a change");
    }

    // python: test_factory_permissions_restrict_lido_target
    function testFork_RevertWhen_PermissionsNameAnotherTarget() external {
        address second = _deployArtifact(
            FACTORY_NAME, abi.encode(creator, factory.MAX_DEPOSITS_RESERVE_TARGET(), lido)
        );

        // The right selector on the wrong target, the Agent instead of Lido
        _registerFactory(
            second, abi.encodePacked(config.agent, ILido.setDepositsReserveTarget.selector)
        );

        bytes memory callData = abi.encode(factory.MAX_DEPOSITS_RESERVE_TARGET());

        vm.prank(creator);
        vm.expectRevert("HAS_NO_PERMISSIONS");
        easyTrack.createMotion(second, callData);
    }

    /// @dev A motion sets the target, which stays as it was until the enactment
    function _setTargetByMotion(uint256 target) private {
        uint256 motionsBefore = easyTrack.getMotions().length;
        uint256 previousTarget = lido.getDepositsReserveTarget();
        bytes memory callData = abi.encode(target);

        uint256 motionId = _createMotion(callData);

        assertEq(easyTrack.getMotions().length, motionsBefore + 1, "motions after creation");
        assertEq(lido.getDepositsReserveTarget(), previousTarget, "target before enactment");

        _enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, motionsBefore, "motions after enactment");
        assertEq(lido.getDepositsReserveTarget(), target, "target after enactment");
    }

    /// @dev Whether Lido answers `getDepositsReserveTarget`, a v3 Lido
    function _hasDepositsReserveTarget() private view returns (bool) {
        (bool ok, bytes memory data) =
            address(lido).staticcall(abi.encodeCall(ILido.getDepositsReserveTarget, ()));

        return ok && data.length == 32;
    }
}
