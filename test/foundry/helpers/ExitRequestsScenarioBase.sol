// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";
import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    ILidoLocator,
    INodeOperatorsRegistry,
    IStakingRouter,
    IValidatorsExitBusOracle
} from "test/foundry/interfaces/External.sol";
import {ISubmitExitRequestHashes} from "test/foundry/interfaces/Factories.sol";

/// @notice Harness for the exit request hash scenarios: an operator of a legacy module with
///         deposited keys has their exit requested through a motion, which submits the batch's
///         hash to the Validators Exit Bus Oracle, then the batch is delivered against the hash
///         and the oracle requests every exit. The helpers port
///         `utils/submit_exit_requests_test_helpers.py`.
abstract contract ExitRequestsScenarioBase is EasyTrackScenarioBase {
    /// @dev `SubmitExitRequestHashesUtils.ExitRequestInput`, an entry of the factories' calldata
    struct ExitRequestInput {
        uint256 moduleId;
        uint256 nodeOpId;
        uint64 valIndex;
        bytes valPubkey;
        uint256 valPubKeyIndex;
    }

    uint256 internal constant MAX_REQUESTS = 200;
    uint256 internal constant DATA_FORMAT_LIST = 1;
    uint256 internal constant PUBKEY_SIZE = 48;
    uint256 internal constant SIG_SIZE = 96;

    /// @dev Keys are added to an operator this many at a time
    uint256 private constant BATCH = 10;

    IValidatorsExitBusOracle internal oracle;
    IStakingRouter internal stakingRouter;
    INodeOperatorsRegistry internal registry;

    /// @dev The staking router id of the module under test, the first field of every request
    uint256 internal moduleId;

    // --- setup ---

    /// @dev Bind the oracle, the router and the registry of the module `id`
    function _bindModule(uint256 id) internal {
        ILidoLocator locator = ILidoLocator(config.locator);
        moduleId = id;
        oracle = IValidatorsExitBusOracle(locator.validatorsExitBusOracle());
        stakingRouter = IStakingRouter(locator.stakingRouter());
        registry = INodeOperatorsRegistry(stakingRouter.getStakingModule(id).stakingModuleAddress);

        vm.label(address(oracle), "ValidatorsExitBusOracle");
        vm.label(address(stakingRouter), "StakingRouter");
        vm.label(address(registry), string.concat("StakingModule", vm.toString(id)));
    }

    /// @dev python: the factory fixtures. The factory targets the module's registry and is
    ///      registered with the oracle's `submitExitRequestsHash`, unless it already is
    function _bindFactory(address factory, string memory key) internal {
        evmScriptFactory = factory;

        vm.label(factory, key);

        assertEq(
            ISubmitExitRequestHashes(factory).nodeOperatorsRegistry(),
            address(registry),
            string.concat("setup: ", key, " nodeOperatorsRegistry")
        );

        _registerFactoryIfMissing(
            factory,
            abi.encodePacked(oracle, IValidatorsExitBusOracle.submitExitRequestsHash.selector)
        );
    }

    /// @dev python: grant_submit_report_hash_role. The executor may submit hashes
    function _grantSubmitReportHashRole() internal {
        _grantRole(address(oracle), oracle.SUBMIT_REPORT_HASH_ROLE(), evmScriptExecutor);
    }

    // --- operators and keys ---

    /// @dev python: ensure_single_operator_with_keys. The first operator holding keys, topped up
    ///      to `minKeys` from its reward address
    function _ensureOperatorWithKeys(uint256 minKeys)
        internal
        returns (uint256 nodeOperatorId, address rewardAddress)
    {
        uint256 count = registry.getNodeOperatorsCount();
        uint64 totalSigningKeys;
        for (; nodeOperatorId < count; ++nodeOperatorId) {
            (,, rewardAddress,,, totalSigningKeys,) =
                registry.getNodeOperator(nodeOperatorId, false);
            if (totalSigningKeys != 0) {
                break;
            }
        }

        assertLt(nodeOperatorId, count, "setup: an operator with keys");

        for (uint256 keysCount = totalSigningKeys; keysCount < minKeys; keysCount += BATCH) {
            uint256 batch = _min(BATCH, minKeys - keysCount);
            (bytes memory keys, bytes memory signatures) = _testKeys(keysCount, batch);

            vm.prank(rewardAddress);
            registry.addSigningKeys(nodeOperatorId, batch, keys, signatures);
        }
    }

    /// @dev python: get_operator_keys. The operator's first `count` keys, each at its index
    function _operatorKeys(uint256 nodeOperatorId, uint256 count)
        internal
        view
        returns (bytes[] memory keys)
    {
        (bytes memory pubkeys,,) = registry.getSigningKeys(nodeOperatorId, 0, count);

        keys = new bytes[](count);
        for (uint256 i; i < count; ++i) {
            keys[i] = _slice(pubkeys, i * PUBKEY_SIZE, PUBKEY_SIZE);
        }
    }

    /// @dev A key the operator has not deposited, added from its reward address, as the request
    ///      the factory rejects
    function _addUnusedKey(uint256 nodeOperatorId, address rewardAddress)
        internal
        returns (ExitRequestInput memory)
    {
        (,,,,, uint64 totalSigningKeys,) = registry.getNodeOperator(nodeOperatorId, false);
        bytes memory newKey = _makeTestBytes(totalSigningKeys, PUBKEY_SIZE);
        bytes memory newSignature = _makeTestBytes(totalSigningKeys, SIG_SIZE);

        vm.prank(rewardAddress);
        registry.addSigningKeys(nodeOperatorId, 1, newKey, newSignature);

        (,, bool used) = registry.getSigningKey(nodeOperatorId, totalSigningKeys);

        assertFalse(used, "Test setup failure: expected the new key to be unused");

        return _request(nodeOperatorId, totalSigningKeys, newKey, totalSigningKeys);
    }

    // --- requests ---

    /// @dev python: build_exit_requests. One request per key, the key's index as both the
    ///      validator index and the pubkey index
    function _buildExitRequests(uint256 nodeOperatorId, bytes[] memory keys)
        internal
        view
        returns (ExitRequestInput[] memory requests)
    {
        requests = new ExitRequestInput[](keys.length);
        for (uint256 i; i < keys.length; ++i) {
            requests[i] = _request(nodeOperatorId, i, keys[i], i);
        }
    }

    /// @dev python: exit_request_input_factory, for the module under test
    function _request(
        uint256 nodeOpId,
        uint256 valIndex,
        bytes memory valPubkey,
        uint256 valPubKeyIndex
    ) internal view returns (ExitRequestInput memory) {
        return ExitRequestInput(moduleId, nodeOpId, uint64(valIndex), valPubkey, valPubKeyIndex);
    }

    /// @dev python: create_exit_request_data. 64 bytes per request: the module id as 3 bytes,
    ///      the operator id as 5, the validator index as 8, then the 48-byte pubkey
    function _packExitRequests(ExitRequestInput[] memory requests)
        internal
        pure
        returns (bytes memory data)
    {
        for (uint256 i; i < requests.length; ++i) {
            ExitRequestInput memory request = requests[i];
            data = abi.encodePacked(
                data,
                bytes3(uint24(request.moduleId)),
                bytes5(uint40(request.nodeOpId)),
                bytes8(request.valIndex),
                request.valPubkey
            );
        }
    }

    /// @dev python: create_exit_requests_hashes. `abi.encode`, not `encodePacked`
    function _exitRequestsHash(bytes memory packed) internal pure returns (bytes32) {
        return keccak256(abi.encode(packed, DATA_FORMAT_LIST));
    }

    // --- motion ---

    /// @dev python: run_motion_and_check_events. `motionCreator` creates the motion, the batch
    ///      cannot be delivered before it is enacted, the enactment submits the batch's hash,
    ///      then `submitter` delivers the batch and the oracle requests every exit
    function _runMotionAndCheckEvents(
        address motionCreator,
        address submitter,
        ExitRequestInput[] memory requests
    ) internal {
        bytes memory callData = abi.encode(requests);

        uint256 motionId = _createMotion(evmScriptFactory, motionCreator, callData);

        IValidatorsExitBusOracle.ExitRequestsData memory batch =
            IValidatorsExitBusOracle.ExitRequestsData(_packExitRequests(requests), DATA_FORMAT_LIST);

        vm.prank(submitter);
        vm.expectRevert(IValidatorsExitBusOracle.ExitHashNotSubmitted.selector);
        oracle.submitExitRequestsData(batch);

        _passMotionDuration();

        vm.expectEmit(address(oracle));
        emit IValidatorsExitBusOracle.RequestsHashSubmitted(_exitRequestsHash(batch.data));

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        vm.recordLogs();

        vm.prank(submitter);
        oracle.submitExitRequestsData(batch);

        _assertExitsRequested(vm.getRecordedLogs(), requests);
    }

    /// @dev python: validate_exit_events. One `ValidatorExitRequest` per request, in order, for
    ///      its module, operator, validator index and pubkey
    function _assertExitsRequested(Vm.Log[] memory logs, ExitRequestInput[] memory requests)
        private
        view
    {
        uint256 found;
        for (uint256 i; i < logs.length; ++i) {
            Vm.Log memory log = logs[i];
            if (
                log.emitter != address(oracle)
                    || log.topics[0] != IValidatorsExitBusOracle.ValidatorExitRequest.selector
            ) {
                continue;
            }

            assertLt(found, requests.length, "ValidatorExitRequest count");

            ExitRequestInput memory request = requests[found];
            (bytes memory validatorPubkey,) = abi.decode(log.data, (bytes, uint256));

            assertEq(uint256(log.topics[1]), moduleId, "stakingModuleId");
            assertEq(uint256(log.topics[2]), request.nodeOpId, "nodeOperatorId");
            assertEq(uint256(log.topics[3]), request.valIndex, "validatorIndex");
            assertEq(validatorPubkey, request.valPubkey, "validatorPubkey");

            ++found;
        }

        assertEq(found, requests.length, "ValidatorExitRequest count");
    }

    // --- bytes ---

    /// @dev python: make_test_bytes. `i` as 3 big-endian bytes, then `length - 3` copies of
    ///      `i % 256`
    function _makeTestBytes(uint256 i, uint256 length) internal pure returns (bytes memory result) {
        require(length >= 3, "Length must be at least 3 bytes");

        result = new bytes(length);

        bytes3 prefix = bytes3(uint24(i));
        result[0] = prefix[0];
        result[1] = prefix[1];
        result[2] = prefix[2];

        bytes1 filler = bytes1(uint8(i % 256));
        for (uint256 j = 3; j < length; ++j) {
            result[j] = filler;
        }
    }

    /// @dev `count` keys with their signatures, the test bytes of the indices from `first`
    function _testKeys(uint256 first, uint256 count)
        private
        pure
        returns (bytes memory keys, bytes memory signatures)
    {
        for (uint256 i; i < count; ++i) {
            keys = bytes.concat(keys, _makeTestBytes(first + i, PUBKEY_SIZE));
            signatures = bytes.concat(signatures, _makeTestBytes(first + i, SIG_SIZE));
        }
    }

    function _slice(bytes memory data, uint256 start, uint256 length)
        private
        pure
        returns (bytes memory result)
    {
        result = new bytes(length);
        for (uint256 i; i < length; ++i) {
            result[i] = data[start + i];
        }
    }

    function _min(uint256 a, uint256 b) private pure returns (uint256) {
        return a < b ? a : b;
    }
}
