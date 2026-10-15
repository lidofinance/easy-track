// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {ExitRequestsScenarioBase} from "test/foundry/helpers/ExitRequestsScenarioBase.sol";
import {ISDVTSubmitExitRequestHashes} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `SDVTSubmitExitRequestHashes` over the SimpleDVT module: the committee
///         it trusts requests the exit of an operator's deposited keys and delivers the batch.
contract SDVTSubmitExitRequestHashesTest is ExitRequestsScenarioBase {
    string internal constant FACTORY_KEY = "SDVTSubmitExitRequestHashes";
    uint256 internal constant MODULE_ID = 2;

    /// @dev python: batch_size, not MAX_REQUESTS
    uint256 internal constant BATCH_SIZE = 60;

    function setUp() public {
        _forkAndInitialize();
        _bindModule(MODULE_ID);

        address factory = _factoryAddress(config.artifact, FACTORY_KEY);
        creator = ISDVTSubmitExitRequestHashes(factory).trustedCaller();

        _bindFactory(factory, FACTORY_KEY);
    }

    // python: test_sdvt_single_exit_request_happy_path
    function testFork_SingleExitRequest() external {
        _requestExits(1);
    }

    // python: test_sdvt_batch_exit_requests_happy_path
    function testFork_BatchExitRequests() external {
        _requestExits(BATCH_SIZE);
    }

    // python: test_sdvt_reverts_on_unused_key
    function testFork_RevertWhen_KeyIsUnused() external {
        _grantSubmitReportHashRole();
        (uint256 nodeOperatorId, address rewardAddress) = _ensureOperatorWithKeys(1);

        ExitRequestInput[] memory requests = new ExitRequestInput[](1);
        requests[0] = _addUnusedKey(nodeOperatorId, rewardAddress);

        vm.prank(creator);
        vm.expectRevert("UNUSED_PUBKEY");
        easyTrack.createMotion(evmScriptFactory, abi.encode(requests));
    }

    /// @dev The trusted committee both creates the motion and delivers the batch
    function _requestExits(uint256 count) private {
        _grantSubmitReportHashRole();
        (uint256 nodeOperatorId,) = _ensureOperatorWithKeys(count);

        ExitRequestInput[] memory requests =
            _buildExitRequests(nodeOperatorId, _operatorKeys(nodeOperatorId, count));

        assertEq(requests.length, count, "requests");

        _runMotionAndCheckEvents(creator, creator, requests);
    }
}
