// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {ExitRequestsScenarioBase} from "test/foundry/helpers/ExitRequestsScenarioBase.sol";

/// @notice `CuratedSubmitExitRequestHashes` over the curated module: an operator's reward
///         address requests the exit of the operator's deposited keys. The deployed factory of
///         `deployed-<chain>.json`, else a fresh one from the `contracts` profile artifacts.
contract CuratedSubmitExitRequestHashesTest is ExitRequestsScenarioBase {
    string internal constant FACTORY_KEY = "CuratedSubmitExitRequestHashes";
    uint256 internal constant MODULE_ID = 1;

    function setUp() public {
        _forkAndInitialize();
        _bindModule(MODULE_ID);

        address factory = _optionalFactoryAddress(config.artifact, FACTORY_KEY);
        if (factory == address(0)) {
            factory = _deployArtifact(FACTORY_KEY, abi.encode(registry, stakingRouter, oracle));
        }

        _bindFactory(factory, FACTORY_KEY);
    }

    // python: test_curated_single_exit_request_happy_path
    function testFork_SingleExitRequest() external {
        _requestExits(1);
    }

    // python: test_curated_batch_exit_requests_happy_path
    function testFork_BatchExitRequests() external {
        _requestExits(MAX_REQUESTS);
    }

    // python: test_curated_reverts_on_unused_key
    function testFork_RevertWhen_KeyIsUnused() external {
        _grantSubmitReportHashRole();
        (uint256 nodeOperatorId, address rewardAddress) = _ensureOperatorWithKeys(1);

        ExitRequestInput[] memory requests = new ExitRequestInput[](1);
        requests[0] = _addUnusedKey(nodeOperatorId, rewardAddress);

        vm.prank(rewardAddress);
        vm.expectRevert("UNUSED_PUBKEY");
        easyTrack.createMotion(evmScriptFactory, abi.encode(requests));
    }

    /// @dev The operator's reward address both creates the motion and delivers the batch
    function _requestExits(uint256 count) private {
        _grantSubmitReportHashRole();
        (uint256 nodeOperatorId, address rewardAddress) = _ensureOperatorWithKeys(count);

        ExitRequestInput[] memory requests =
            _buildExitRequests(nodeOperatorId, _operatorKeys(nodeOperatorId, count));

        assertEq(requests.length, count, "requests");

        _runMotionAndCheckEvents(rewardAddress, rewardAddress, requests);
    }
}
