// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {INodeOperatorsRegistry} from "contracts/interfaces/INodeOperatorsRegistry.sol";
import {SubmitExitRequestHashesUtils} from "contracts/libraries/SubmitExitRequestHashesUtils.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {
    SubmitExitRequestHashesUtilsWrapper
} from "contracts/test/SubmitExitRequestHashesUtilsWrapper.sol";
import {ExitRequests} from "test/foundry/unit/helpers/ExitRequests.sol";

contract SubmitExitRequestHashesUtilsTest is Test {
    uint256 internal constant MAX_REQUESTS = 200;
    uint256 internal constant DATA_FORMAT = 1;
    uint256 internal constant CURATED_MODULE_ID = 1;
    uint256 internal constant SDVT_MODULE_ID = 2;
    bytes32 internal constant SINGLE_REQUEST_HASH =
        0xa558e9158881b1a46615df4ea220487bafca3a314f4ea4f7d18f7676de92b6dd;
    bytes32 internal constant MULTIPLE_REQUESTS_HASH =
        0xe42cdd024f268f7d6532aed85ca39c1174b4c777e550f020f882fba0ae67cab3;
    bytes32 internal constant EMPTY_REQUESTS_HASH =
        0x2f422f1f6594b9085330a4f37103dcf460337ecef4b6ae7d86f8ccce0b44e717;

    address internal owner = makeAddr("owner");
    address internal nodeOperator = makeAddr("nodeOperator");

    SubmitExitRequestHashesUtilsWrapper internal wrapper;
    StakingRouterStub internal stakingRouterStub;
    NodeOperatorsRegistryStub internal sdvtRegistryStub;
    NodeOperatorsRegistryStub internal curatedRegistryStub;

    function setUp() public {
        bytes memory keysConcat;
        for (uint256 i; i < MAX_REQUESTS; ++i) {
            keysConcat = bytes.concat(keysConcat, _pubkey(i));
        }

        vm.startPrank(owner);
        wrapper = new SubmitExitRequestHashesUtilsWrapper();
        stakingRouterStub = new StakingRouterStub();

        sdvtRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        stakingRouterStub.setStakingModule(SDVT_MODULE_ID, address(sdvtRegistryStub));
        sdvtRegistryStub.setSigningKeys(0, keysConcat);

        curatedRegistryStub = new NodeOperatorsRegistryStub(nodeOperator);
        stakingRouterStub.setStakingModule(CURATED_MODULE_ID, address(curatedRegistryStub));
        curatedRegistryStub.setSigningKeys(0, keysConcat);
        vm.stopPrank();
    }

    // python: test_validation_passes_on_correct_request
    function test_ValidationPassesOnCorrectRequest() external view {
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_passes_on_correct_request_multiple
    function test_ValidationPassesOnCorrectRequestMultiple() external {
        uint256 nodeOpId2 = ExitRequests.addNodeOperator(sdvtRegistryStub, _pubkey(1), owner);

        _validate(
            _requests(
                _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0),
                _request(SDVT_MODULE_ID, nodeOpId2, 0 + 1, _pubkey(1), 0)
            ),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_passes_on_valid_requests_with_creator
    function test_ValidationPassesOnValidRequestsWithCreator() external view {
        _validate(
            _requests(_request(CURATED_MODULE_ID, 0, 0, _pubkey(0), 0)),
            curatedRegistryStub,
            nodeOperator
        );
    }

    // python: test_validation_reverts_if_creator_not_node_operator_multiple
    function test_RevertWhen_CreatorIsNotNodeOperatorMultiple() external {
        uint256 nodeOpId = ExitRequests.addNodeOperator(curatedRegistryStub, _pubkey(1), owner);

        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_NODE_OPERATOR");
        _validate(
            _requests(
                _request(CURATED_MODULE_ID, 0, 0, _pubkey(0), 0),
                _request(CURATED_MODULE_ID, nodeOpId, 0 + 1, _pubkey(1), 0)
            ),
            curatedRegistryStub,
            owner
        );
    }

    // python: test_validation_reverts_on_empty_requests
    function test_RevertWhen_RequestsAreEmpty() external {
        vm.expectRevert("EMPTY_REQUESTS_LIST");
        _validate(
            new SubmitExitRequestHashesUtils.ExitRequestInput[](0),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_too_many_requests
    function test_RevertWhen_TooManyRequests() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[]
            memory requests = new SubmitExitRequestHashesUtils.ExitRequestInput[](MAX_REQUESTS);
        for (uint256 i; i < MAX_REQUESTS; ++i) {
            requests[i] = _request(SDVT_MODULE_ID, 0, uint64(i), _pubkey(i), i);
        }

        _validate(requests, sdvtRegistryStub, address(0));

        SubmitExitRequestHashesUtils.ExitRequestInput[]
            memory tooManyRequests = new SubmitExitRequestHashesUtils.ExitRequestInput[](
                MAX_REQUESTS + 1
            );
        for (uint256 i; i < MAX_REQUESTS; ++i) {
            tooManyRequests[i] = requests[i];
        }

        tooManyRequests[MAX_REQUESTS] = _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 200);

        vm.expectRevert("MAX_REQUESTS_PER_MOTION_EXCEEDED");
        _validate(tooManyRequests, sdvtRegistryStub, address(0));
    }

    // python: test_validation_reverts_on_wrong_staking_module
    function test_RevertWhen_StakingModuleIsWrong() external {
        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        _validate(
            _requests(_request(CURATED_MODULE_ID, 0, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_wrong_staking_module_multiple
    function test_RevertWhen_StakingModuleIsWrongMultiple() external {
        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        _validate(
            _requests(
                _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0),
                _request(CURATED_MODULE_ID, 0, 0, _pubkey(1), 0)
            ),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_empty_pubkey
    function test_RevertWhen_PubkeyIsEmpty() external {
        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, hex"", 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_pubkey_too_short
    function test_RevertWhen_PubkeyIsTooShort() external {
        bytes memory shortPubkey = _repeat(0xaa, ExitRequests.PUBKEY_SIZE - 1);

        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, shortPubkey, 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_pubkey_too_long
    function test_RevertWhen_PubkeyIsTooLong() external {
        bytes memory longPubkey = _repeat(0xaa, ExitRequests.PUBKEY_SIZE + 1);

        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, longPubkey, 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_wrong_pubkey
    function test_RevertWhen_PubkeyIsWrong() external {
        vm.expectRevert("INVALID_PUBKEY");
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, _pubkey(1), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_unused_pubkey
    function test_RevertWhen_PubkeyIsUnused() external {
        vm.prank(owner);
        sdvtRegistryStub.setSigningKeyUsed(0, 0, false);

        vm.expectRevert("UNUSED_PUBKEY");
        _validate(
            _requests(_request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_wrong_node_op_id
    function test_RevertWhen_NodeOpIdIsWrong() external {
        uint256 lastNodeOpId = sdvtRegistryStub.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        _validate(
            _requests(_request(SDVT_MODULE_ID, lastNodeOpId + 1, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_wrong_node_op_id_multiple
    function test_RevertWhen_NodeOpIdIsWrongMultiple() external {
        uint256 lastNodeOpId = sdvtRegistryStub.getNodeOperatorsCount();

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        _validate(
            _requests(
                _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0),
                _request(SDVT_MODULE_ID, lastNodeOpId + 1, 0, _pubkey(1), 0)
            ),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_duplicate_exit_requests
    function test_RevertWhen_ExitRequestsAreDuplicated() external {
        SubmitExitRequestHashesUtils.ExitRequestInput memory request = _request(
            SDVT_MODULE_ID,
            0,
            0,
            _pubkey(0),
            0
        );

        vm.expectRevert("INVALID_EXIT_REQUESTS_SORT_ORDER");
        _validate(_requests(request, request), sdvtRegistryStub, address(0));
    }

    // python: test_validation_reverts_on_wrong_requests_index_sort_order
    function test_RevertWhen_RequestsSortOrderIsWrong() external {
        uint256 nodeOpId1 = ExitRequests.addNodeOperator(sdvtRegistryStub, _pubkey(1), owner);

        // nodeOpId outranks valIndex in the packed sort key
        vm.expectRevert("INVALID_EXIT_REQUESTS_SORT_ORDER");
        _validate(
            _requests(
                _request(SDVT_MODULE_ID, nodeOpId1, 5, _pubkey(1), 0),
                _request(SDVT_MODULE_ID, 0, 10, _pubkey(0), 0)
            ),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_module_id_overflow
    function test_RevertWhen_ModuleIdOverflows() external {
        uint256 invalidModuleId = 2 ** 24;

        // the stub stores the id as uint24, so the registered module reports id 0
        stakingRouterStub.setStakingModule(invalidModuleId, address(sdvtRegistryStub));

        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        _validate(
            _requests(_request(invalidModuleId, 0, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_validation_reverts_on_node_op_id_overflow
    function test_RevertWhen_NodeOpIdOverflows() external {
        uint256 invalidNodeOpId = 2 ** 40;

        // the stub stores the count as uint40, so it stays at 1
        sdvtRegistryStub.setDesiredNodeOperatorCount(invalidNodeOpId + 1);

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        _validate(
            _requests(_request(SDVT_MODULE_ID, invalidNodeOpId, 0, _pubkey(0), 0)),
            sdvtRegistryStub,
            address(0)
        );
    }

    // python: test_hash_requests
    function test_HashesRequests() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0)
        );

        bytes32 actualHash = wrapper.hashExitRequests(requests);

        assertEq(
            actualHash,
            ExitRequests.createExitRequestsHashes(requests, DATA_FORMAT),
            "hash vs helper"
        );
        assertEq(actualHash, SINGLE_REQUEST_HASH, "hash");
    }

    // python: test_hash_requests_multiple
    function test_HashesRequestsMultiple() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(SDVT_MODULE_ID, 0, 0, _pubkey(0), 0),
            _request(SDVT_MODULE_ID, 0, 0, _pubkey(1), 0)
        );

        bytes32 actualHash = wrapper.hashExitRequests(requests);

        assertEq(
            actualHash,
            ExitRequests.createExitRequestsHashes(requests, DATA_FORMAT),
            "hash vs helper"
        );
        assertEq(actualHash, MULTIPLE_REQUESTS_HASH, "hash");
    }

    // python: test_hash_requests_empty
    function test_HashesEmptyRequests() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[]
            memory requests = new SubmitExitRequestHashesUtils.ExitRequestInput[](0);

        bytes32 actualHash = wrapper.hashExitRequests(requests);

        assertEq(
            actualHash,
            ExitRequests.createExitRequestsHashes(requests, DATA_FORMAT),
            "hash vs helper"
        );
        assertEq(actualHash, EMPTY_REQUESTS_HASH, "hash");
    }

    function _validate(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests,
        NodeOperatorsRegistryStub registry,
        address creator
    ) private view {
        wrapper.validateExitRequests(
            requests,
            INodeOperatorsRegistry(address(registry)),
            stakingRouterStub,
            creator
        );
    }

    // python: submit_exit_hashes_factory_config["pubkeys"][index]
    function _pubkey(uint256 index) private pure returns (bytes memory) {
        return ExitRequests.makeTestBytes(index + 1);
    }

    // python: exit_request_input_factory
    function _request(
        uint256 moduleId,
        uint256 nodeOpId,
        uint64 valIndex,
        bytes memory valPubkey,
        uint256 valPubKeyIndex
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput memory) {
        return
            SubmitExitRequestHashesUtils.ExitRequestInput({
                moduleId: moduleId,
                nodeOpId: nodeOpId,
                valIndex: valIndex,
                valPubkey: valPubkey,
                valPubKeyIndex: valPubKeyIndex
            });
    }

    function _requests(
        SubmitExitRequestHashesUtils.ExitRequestInput memory request
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests) {
        requests = new SubmitExitRequestHashesUtils.ExitRequestInput[](1);
        requests[0] = request;
    }

    function _requests(
        SubmitExitRequestHashesUtils.ExitRequestInput memory first,
        SubmitExitRequestHashesUtils.ExitRequestInput memory second
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests) {
        requests = new SubmitExitRequestHashesUtils.ExitRequestInput[](2);
        requests[0] = first;
        requests[1] = second;
    }

    function _repeat(bytes1 value, uint256 count) private pure returns (bytes memory result) {
        result = new bytes(count);
        for (uint256 i; i < count; ++i) {
            result[i] = value;
        }
    }
}
