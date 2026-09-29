// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IAccessControlEnumerable, IMerkleGate} from "test/foundry/interfaces/External.sol";
import {ISetMerkleGateTree} from "test/foundry/interfaces/Factories.sol";

/// @notice The deployed `SetMerkleGateTree` factories of `deployed-sm-<chain>.json`: a motion sets
///         the Merkle tree root & CID of a module's gate. The gate is discovered on-chain, see
///         `_managedGate`.
abstract contract SetMerkleGateTreeTest is EasyTrackScenarioBase {
    bytes32 internal constant SET_TREE_ROLE = keccak256("SET_TREE_ROLE");

    IMerkleGate internal gate;

    function _factoryKey() internal pure virtual returns (string memory);

    /// @dev The staking module of `NetworkConfig` whose gate the factory manages
    function _stakingModule() internal view virtual returns (address);

    function setUp() public {
        _forkAndInitialize();

        ISetMerkleGateTree factory =
            ISetMerkleGateTree(_factoryAddress(config.smArtifact, _factoryKey()));
        gate = IMerkleGate(_managedGate(_stakingModule()));

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    function testFork_SetsGateTree() external {
        (bytes32 newTreeRoot, string memory newTreeCid, bytes memory callData) =
            _plannedTreeUpdate();

        _enact(callData);

        assertEq(gate.treeRoot(), newTreeRoot, "treeRoot");
        assertEq(gate.treeCid(), newTreeCid, "treeCid");
    }

    function testFork_RevertWhen_CurrentTreeChangesBeforeEnact() external {
        // the planned motion commits the current root and CID
        (,, bytes memory callData) = _plannedTreeUpdate();
        uint256 motionId = _createMotion(callData);

        // Change the gate's tree so the committed current root/cid no longer match
        vm.prank(evmScriptExecutor);
        gate.setTreeParams(keccak256("interfering-root"), "interfering-cid");

        _givenMotionDurationPassed();

        vm.prank(stranger);
        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        easyTrack.enactMotion(motionId, callData);
    }

    /// @dev The module's `CREATE_NODE_OPERATOR_ROLE` holder on which the executor may set the tree
    function _managedGate(address stakingModule) private view returns (address) {
        IAccessControlEnumerable accessControl = IAccessControlEnumerable(stakingModule);
        uint256 count = accessControl.getRoleMemberCount(CREATE_NODE_OPERATOR_ROLE);

        for (uint256 i; i < count; ++i) {
            address candidate = accessControl.getRoleMember(CREATE_NODE_OPERATOR_ROLE, i);
            (bool ok, bytes memory returnData) = candidate.staticcall(
                abi.encodeCall(IAccessControlEnumerable.hasRole, (SET_TREE_ROLE, evmScriptExecutor))
            );
            if (ok && returnData.length == 32 && abi.decode(returnData, (bool))) {
                return candidate;
            }
        }

        revert(
            "no gate managed by the executor among the module's CREATE_NODE_OPERATOR_ROLE holders"
        );
    }

    /// @dev A new root and CID derived from the current ones, and the call data committing to both
    function _plannedTreeUpdate()
        private
        view
        returns (bytes32 newTreeRoot, string memory newTreeCid, bytes memory callData)
    {
        bytes32 treeRoot = gate.treeRoot();
        string memory treeCid = gate.treeCid();
        newTreeRoot = keccak256(abi.encodePacked("scenario-root", treeRoot));
        newTreeCid = string.concat("scenario-cid-", treeCid);

        callData = abi.encode(address(gate), treeRoot, treeCid, newTreeRoot, newTreeCid);
    }
}

contract SetMerkleGateTreeCSMTest is SetMerkleGateTreeTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CSM";
    }

    function _stakingModule() internal view override returns (address) {
        return config.csmModule;
    }
}

contract SetMerkleGateTreeCMTest is SetMerkleGateTreeTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CM";
    }

    function _stakingModule() internal view override returns (address) {
        return config.cmModule;
    }
}
