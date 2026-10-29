// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    CuratedSubmitExitRequestHashes
} from "contracts/EVMScriptFactories/CuratedSubmitExitRequestHashes.sol";
import {
    SDVTSubmitExitRequestHashes
} from "contracts/EVMScriptFactories/SDVTSubmitExitRequestHashes.sol";
import {SubmitExitRequestHashesUtils} from "contracts/libraries/SubmitExitRequestHashesUtils.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {StakingRouterStub} from "contracts/test/StakingRouterStub.sol";
import {ValidatorExitBusOracleStub} from "contracts/test/ValidatorExitBusOracleStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {ExitRequests} from "test/foundry/unit/helpers/ExitRequests.sol";

/// @dev The surface the two factories share. No project interface declares `decodeEVMScriptCallData`
interface ISubmitExitRequestHashes {
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        returns (bytes memory);

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory);
}

/// @dev Parametrized by module, each concrete contract binds one variant in `_setUpVariant`
abstract contract SubmitExitRequestHashesTest is Test {
    uint256 internal constant CURATED_MODULE_ID = 1;
    uint256 internal constant SDVT_MODULE_ID = 2;
    uint256 internal constant NODE_OPERATOR_ID = 0;
    uint64 internal constant VALIDATOR_INDEX = 0;
    uint256 internal constant INVALID_PUBKEY_INDEX = 1;
    uint256 internal constant OVERFLOWED_MODULE_ID = 2 ** 24;
    uint256 internal constant OVERFLOWED_NODE_OPERATOR_ID = 2 ** 40;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");

    StakingRouterStub internal stakingRouterStub;
    ValidatorExitBusOracleStub internal validatorsExitBusOracleStub;
    NodeOperatorsRegistryStub internal curatedRegistryStub;
    NodeOperatorsRegistryStub internal sdvtRegistryStub;

    NodeOperatorsRegistryStub internal registry;
    uint256 internal moduleId;
    uint256 internal wrongModuleId;
    address internal creator;
    ISubmitExitRequestHashes internal submitExitRequestHashes;

    function setUp() public {
        stakingRouterStub = new StakingRouterStub();
        validatorsExitBusOracleStub = new ValidatorExitBusOracleStub();
        curatedRegistryStub = _deployRegistryStub(CURATED_MODULE_ID);
        sdvtRegistryStub = _deployRegistryStub(SDVT_MODULE_ID);

        _setUpVariant();

        vm.label(address(stakingRouterStub), "stakingRouterStub");
        vm.label(address(validatorsExitBusOracleStub), "validatorsExitBusOracleStub");
        vm.label(address(curatedRegistryStub), "curatedRegistryStub");
        vm.label(address(sdvtRegistryStub), "sdvtRegistryStub");
        vm.label(address(submitExitRequestHashes), "submitExitRequestHashes");
    }

    /// @dev Binds `registry`, `moduleId`, `wrongModuleId`, `creator` and deploys
    /// `submitExitRequestHashes`
    function _setUpVariant() internal virtual;

    function test_DecodesEVMScriptCallData() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0),
            _request(
                moduleId, NODE_OPERATOR_ID + 1, VALIDATOR_INDEX + 1, ExitRequests.pubkeyAt(1), 0
            )
        );

        SubmitExitRequestHashesUtils.ExitRequestInput[] memory decoded =
            submitExitRequestHashes.decodeEVMScriptCallData(abi.encode(requests));

        _assertRequestsEq(decoded, requests);
    }

    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        submitExitRequestHashes.decodeEVMScriptCallData("");
    }

    function test_DecodesEVMScriptCallDataFromAnyCaller() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId, _missingNodeOperatorId(), VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0
            )
        );

        vm.prank(stranger);
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory decoded =
            submitExitRequestHashes.decodeEVMScriptCallData(abi.encode(requests));

        _assertRequestsEq(decoded, requests);
    }

    function test_CreatesEVMScript() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0)
        );

        bytes memory evmScript =
            submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));

        assertEq(evmScript, _expectedEVMScript(requests), "evmScript");
    }

    function test_CreatesEVMScriptWithMaxRequests() external view {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            new SubmitExitRequestHashesUtils.ExitRequestInput[](ExitRequests.MAX_REQUESTS);

        for (uint256 i; i < requests.length; ++i) {
            requests[i] =
                _request(moduleId, NODE_OPERATOR_ID, uint64(i), ExitRequests.pubkeyAt(i), i);
        }

        bytes memory evmScript =
            submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));

        assertEq(evmScript, _expectedEVMScript(requests), "evmScript");
    }

    function test_CreatesEVMScriptWithLatestNodeOperator() external view {
        uint256 latestNodeOperatorId = registry.getNodeOperatorsCount() - 1;

        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, latestNodeOperatorId, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0)
        );

        bytes memory evmScript =
            submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));

        assertEq(evmScript, _expectedEVMScript(requests), "evmScript");
    }

    function test_RevertWhen_RequestsExceedMax() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            new SubmitExitRequestHashesUtils.ExitRequestInput[](ExitRequests.MAX_REQUESTS + 1);

        for (uint256 i; i < requests.length; ++i) {
            requests[i] =
                _request(moduleId, NODE_OPERATOR_ID, uint64(i + 1), ExitRequests.pubkeyAt(0), 0);
        }

        vm.expectRevert("MAX_REQUESTS_PER_MOTION_EXCEEDED");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_RequestsAreEmpty() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            new SubmitExitRequestHashesUtils.ExitRequestInput[](0);

        vm.expectRevert("EMPTY_REQUESTS_LIST");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_StakingModuleIsWrong() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(wrongModuleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0)
        );

        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_StakingModuleIsWrongInMultipleRequests() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, 4, ExitRequests.pubkeyAt(0), 0),
            _request(wrongModuleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0),
            _request(moduleId, NODE_OPERATOR_ID, 5, ExitRequests.pubkeyAt(0), 0)
        );

        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIsEmpty() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            _requests(_request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, "", 0));

        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIsTooShort() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId,
                NODE_OPERATOR_ID,
                VALIDATOR_INDEX,
                _pubkeyOfLength(ExitRequests.PUBKEY_SIZE - 1),
                0
            )
        );

        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIsTooLong() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId,
                NODE_OPERATOR_ID,
                VALIDATOR_INDEX,
                _pubkeyOfLength(ExitRequests.PUBKEY_SIZE + 1),
                0
            )
        );

        vm.expectRevert("INVALID_PUBKEY_LENGTH");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIsWrong() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, _unregisteredPubkey(), 0)
        );

        vm.expectRevert("INVALID_PUBKEY");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIsWrongInMultipleRequests() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, _unregisteredPubkey(), 0),
            _request(
                moduleId, NODE_OPERATOR_ID + 1, VALIDATOR_INDEX + 1, ExitRequests.pubkeyAt(0), 0
            )
        );

        vm.expectRevert("INVALID_PUBKEY");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_NodeOperatorDoesNotExist() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId, _missingNodeOperatorId(), VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0
            )
        );

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_NodeOperatorDoesNotExistInMultipleRequests() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId, _missingNodeOperatorId(), VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0
            ),
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX + 1, ExitRequests.pubkeyAt(1), 0)
        );

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_PubkeyIndexIsWrong() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId,
                NODE_OPERATOR_ID,
                VALIDATOR_INDEX,
                ExitRequests.pubkeyAt(0),
                INVALID_PUBKEY_INDEX
            )
        );

        vm.expectRevert("INVALID_PUBKEY");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_ModuleIdOverflows() external {
        // the router stub keeps uint24(id), so the module registers as id 0 and the request's id
        // never matches it
        stakingRouterStub.setStakingModule(OVERFLOWED_MODULE_ID, address(registry));

        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                OVERFLOWED_MODULE_ID, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0
            )
        );

        vm.expectRevert("EXECUTOR_NOT_PERMISSIONED_ON_MODULE");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_NodeOperatorIdOverflows() external {
        // the registry stub keeps uint40(count), so the count stays 1
        registry.setDesiredNodeOperatorCount(OVERFLOWED_NODE_OPERATOR_ID + 1);

        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(
                moduleId, OVERFLOWED_NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0
            )
        );

        vm.expectRevert("NODE_OPERATOR_ID_DOES_NOT_EXIST");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_RequestsAreDuplicated() external {
        SubmitExitRequestHashesUtils.ExitRequestInput memory request =
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(0), 0);

        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests =
            _requests(request, request);

        vm.expectRevert("INVALID_EXIT_REQUESTS_SORT_ORDER");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    function test_RevertWhen_RequestsAreNotSorted() external {
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests = _requests(
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX + 1, ExitRequests.pubkeyAt(0), 0),
            _request(moduleId, NODE_OPERATOR_ID, VALIDATOR_INDEX, ExitRequests.pubkeyAt(1), 0)
        );

        vm.expectRevert("INVALID_EXIT_REQUESTS_SORT_ORDER");
        submitExitRequestHashes.createEVMScript(creator, abi.encode(requests));
    }

    /// @dev Deploys a registry stub with one operator holding the 200 keys, registered in the
    /// router as `stakingModuleId`
    function _deployRegistryStub(uint256 stakingModuleId)
        private
        returns (NodeOperatorsRegistryStub registryStub)
    {
        registryStub = new NodeOperatorsRegistryStub(nodeOperator);
        stakingRouterStub.setStakingModule(stakingModuleId, address(registryStub));
        registryStub.setSigningKeys(NODE_OPERATOR_ID, ExitRequests.concatenatedPubkeys());
    }

    function _missingNodeOperatorId() private view returns (uint256) {
        return registry.getNodeOperatorsCount() + 1;
    }

    /// @dev The key after the last one the registry holds
    function _unregisteredPubkey() private pure returns (bytes memory) {
        return ExitRequests.pubkeyAt(ExitRequests.MAX_REQUESTS);
    }

    function _pubkeyOfLength(uint256 length) private pure returns (bytes memory pubkey) {
        pubkey = new bytes(length);

        for (uint256 i; i < length; ++i) {
            pubkey[i] = 0xaa;
        }
    }

    function _request(
        uint256 moduleId_,
        uint256 nodeOpId,
        uint64 valIndex,
        bytes memory valPubkey,
        uint256 valPubKeyIndex
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput memory) {
        return SubmitExitRequestHashesUtils.ExitRequestInput({
            moduleId: moduleId_,
            nodeOpId: nodeOpId,
            valIndex: valIndex,
            valPubkey: valPubkey,
            valPubKeyIndex: valPubKeyIndex
        });
    }

    function _requests(SubmitExitRequestHashesUtils.ExitRequestInput memory request)
        private
        pure
        returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests)
    {
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

    function _requests(
        SubmitExitRequestHashesUtils.ExitRequestInput memory first,
        SubmitExitRequestHashesUtils.ExitRequestInput memory second,
        SubmitExitRequestHashesUtils.ExitRequestInput memory third
    ) private pure returns (SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests) {
        requests = new SubmitExitRequestHashesUtils.ExitRequestInput[](3);
        requests[0] = first;
        requests[1] = second;
        requests[2] = third;
    }

    function _expectedEVMScript(SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests)
        private
        view
        returns (bytes memory)
    {
        return EVMScripts.encodeCallScript(
            address(validatorsExitBusOracleStub),
            abi.encodeWithSelector(
                ValidatorExitBusOracleStub.submitExitRequestsHash.selector,
                ExitRequests.createExitRequestsHashes(requests, ExitRequests.DATA_FORMAT_LIST)
            )
        );
    }

    function _assertRequestsEq(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory actual,
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory expected
    ) private pure {
        assertEq(actual.length, expected.length, "requests.length");

        for (uint256 i; i < expected.length; ++i) {
            assertEq(actual[i].moduleId, expected[i].moduleId, "moduleId");
            assertEq(actual[i].nodeOpId, expected[i].nodeOpId, "nodeOpId");
            assertEq(actual[i].valIndex, expected[i].valIndex, "valIndex");
            assertEq(actual[i].valPubkey, expected[i].valPubkey, "valPubkey");
            assertEq(actual[i].valPubKeyIndex, expected[i].valPubKeyIndex, "valPubKeyIndex");
        }
    }
}

contract SubmitExitRequestHashesCuratedTest is SubmitExitRequestHashesTest {
    function _setUpVariant() internal override {
        registry = curatedRegistryStub;
        moduleId = CURATED_MODULE_ID;
        wrongModuleId = SDVT_MODULE_ID;
        creator = nodeOperator;

        vm.prank(creator);
        submitExitRequestHashes = ISubmitExitRequestHashes(
            address(
                new CuratedSubmitExitRequestHashes(
                    address(registry),
                    address(stakingRouterStub),
                    address(validatorsExitBusOracleStub)
                )
            )
        );
    }
}

contract SubmitExitRequestHashesSDVTTest is SubmitExitRequestHashesTest {
    function _setUpVariant() internal override {
        registry = sdvtRegistryStub;
        moduleId = SDVT_MODULE_ID;
        wrongModuleId = CURATED_MODULE_ID;
        creator = owner;

        vm.prank(creator);
        submitExitRequestHashes = ISubmitExitRequestHashes(
            address(
                new SDVTSubmitExitRequestHashes(
                    creator,
                    address(registry),
                    address(stakingRouterStub),
                    address(validatorsExitBusOracleStub)
                )
            )
        );
    }
}
