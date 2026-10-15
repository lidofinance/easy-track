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

    /// @dev The trees of the stub gates the permission tests deploy
    bytes32 internal constant NEW_GATE_INITIAL_ROOT =
        0x4444444444444444444444444444444444444444444444444444444444444444;
    string internal constant NEW_GATE_INITIAL_CID = "QmNewGateInitial";
    bytes32 internal constant NEW_GATE_UPDATED_ROOT =
        0x5555555555555555555555555555555555555555555555555555555555555555;
    string internal constant NEW_GATE_UPDATED_CID = "QmNewGateUpdated";
    bytes32 internal constant REMOVABLE_GATE_INITIAL_ROOT =
        0x6666666666666666666666666666666666666666666666666666666666666666;
    string internal constant REMOVABLE_GATE_INITIAL_CID = "QmRemovableGateInitial";
    bytes32 internal constant REMOVABLE_GATE_NEW_ROOT =
        0x7777777777777777777777777777777777777777777777777777777777777777;
    string internal constant REMOVABLE_GATE_NEW_CID = "QmRemovableGateNew";

    IMerkleGate internal gate;

    function _factoryKey() internal pure virtual returns (string memory);

    /// @dev The staking module of `NetworkConfig` whose gate the factory manages
    function _stakingModule() internal view virtual returns (address);

    /// @dev The other module of `NetworkConfig`, whose gate is outside the factory's permissions
    function _otherStakingModule() internal view virtual returns (address);

    function setUp() public {
        _forkAndInitialize();

        ISetMerkleGateTree factory =
            ISetMerkleGateTree(_factoryAddress(config.smArtifact, _factoryKey()));
        gate = IMerkleGate(_managedGate(_stakingModule()));

        evmScriptFactory = address(factory);
        creator = factory.trustedCaller();
    }

    // python: test_merkle_gate_scenario
    function testFork_SetsGateTree() external {
        (bytes32 newTreeRoot, string memory newTreeCid, bytes memory callData) =
            _plannedTreeUpdate(gate);

        _enact(callData);

        assertEq(gate.treeRoot(), newTreeRoot, "treeRoot");
        assertEq(gate.treeCid(), newTreeCid, "treeCid");
    }

    // python: test_merkle_gate_reverts_with_same_tree_root_on_motion_creation
    function testFork_RevertWhen_NewTreeRootIsCurrent() external {
        (, string memory newTreeCid,) = _plannedTreeUpdate(gate);
        bytes32 treeRoot = gate.treeRoot();
        bytes memory callData =
            abi.encode(address(gate), treeRoot, gate.treeCid(), treeRoot, newTreeCid);

        vm.prank(creator);
        vm.expectRevert("SAME_TREE_ROOT");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    // python: test_merkle_gate_reverts_with_same_tree_cid_on_motion_creation
    function testFork_RevertWhen_NewTreeCidIsCurrent() external {
        (bytes32 newTreeRoot,,) = _plannedTreeUpdate(gate);
        string memory treeCid = gate.treeCid();
        bytes memory callData =
            abi.encode(address(gate), gate.treeRoot(), treeCid, newTreeRoot, treeCid);

        vm.prank(creator);
        vm.expectRevert("SAME_TREE_CID");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    // python: test_merkle_gate_reverts_for_gate_not_in_permissions
    function testFork_RevertWhen_GateIsNotInPermissions() external {
        // A real gate the executor may set, outside this factory's permissions
        IMerkleGate otherGate = IMerkleGate(_managedGate(_otherStakingModule()));
        (,, bytes memory callData) = _plannedTreeUpdate(otherGate);

        vm.prank(creator);
        vm.expectRevert("HAS_NO_PERMISSIONS");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    // python: test_merkle_gate_permissions_update_adds_new_gate
    function testFork_SetsTreeOfGateAddedToPermissions() external {
        IMerkleGate newGate = _deployGate(NEW_GATE_INITIAL_ROOT, NEW_GATE_INITIAL_CID);
        IAccessControlEnumerable(address(newGate)).grantRole(SET_TREE_ROLE, evmScriptExecutor);
        _replaceFactoryPermissions(_permissionsForGates(address(gate), address(newGate)));
        bytes memory callData = abi.encode(
            address(newGate),
            NEW_GATE_INITIAL_ROOT,
            NEW_GATE_INITIAL_CID,
            NEW_GATE_UPDATED_ROOT,
            NEW_GATE_UPDATED_CID
        );

        _enact(callData);

        assertEq(newGate.treeRoot(), NEW_GATE_UPDATED_ROOT, "treeRoot");
        assertEq(newGate.treeCid(), NEW_GATE_UPDATED_CID, "treeCid");
    }

    // python: test_merkle_gate_permissions_update_removes_gate
    function testFork_RevertWhen_GateIsRemovedFromPermissions() external {
        IMerkleGate removableGate =
            _deployGate(REMOVABLE_GATE_INITIAL_ROOT, REMOVABLE_GATE_INITIAL_CID);
        _replaceFactoryPermissions(_permissionsForGates(address(gate), address(removableGate)));
        _replaceFactoryPermissions(_permissionsForGate(address(gate)));
        bytes memory callData = abi.encode(
            address(removableGate),
            REMOVABLE_GATE_INITIAL_ROOT,
            REMOVABLE_GATE_INITIAL_CID,
            REMOVABLE_GATE_NEW_ROOT,
            REMOVABLE_GATE_NEW_CID
        );

        vm.prank(creator);
        vm.expectRevert("HAS_NO_PERMISSIONS");
        easyTrack.createMotion(evmScriptFactory, callData);
    }

    function testFork_RevertWhen_CurrentTreeChangesBeforeEnact() external {
        // the planned motion commits the current root and CID
        (,, bytes memory callData) = _plannedTreeUpdate(gate);
        uint256 motionId = _createMotion(callData);

        // Change the gate's tree so the committed current root/cid no longer match
        vm.prank(evmScriptExecutor);
        gate.setTreeParams(keccak256("interfering-root"), "interfering-cid");

        _passMotionDuration();

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

    /// @dev A `MerkleGateStub` with the test as its admin, set to the given tree
    function _deployGate(bytes32 treeRoot, string memory treeCid)
        private
        returns (IMerkleGate stub)
    {
        stub = IMerkleGate(_deployArtifact("MerkleGateStub", ""));
        stub.setTreeParams(treeRoot, treeCid);
    }

    /// @dev The factory's permissions: its own `validateInputData`, then `setTreeParams` on the
    ///      gate
    function _permissionsForGate(address onlyGate) private view returns (bytes memory) {
        return abi.encodePacked(
            evmScriptFactory,
            ISetMerkleGateTree.validateInputData.selector,
            onlyGate,
            IMerkleGate.setTreeParams.selector
        );
    }

    function _permissionsForGates(address firstGate, address secondGate)
        private
        view
        returns (bytes memory)
    {
        return abi.encodePacked(
            _permissionsForGate(firstGate), secondGate, IMerkleGate.setTreeParams.selector
        );
    }

    /// @dev A new root and CID derived from the target gate's current ones, and the call data
    ///      committing to both
    function _plannedTreeUpdate(IMerkleGate target)
        private
        view
        returns (bytes32 newTreeRoot, string memory newTreeCid, bytes memory callData)
    {
        bytes32 treeRoot = target.treeRoot();
        string memory treeCid = target.treeCid();
        newTreeRoot = keccak256(abi.encodePacked("scenario-root", treeRoot));
        newTreeCid = string.concat("scenario-cid-", treeCid);

        callData = abi.encode(address(target), treeRoot, treeCid, newTreeRoot, newTreeCid);
    }
}

contract SetMerkleGateTreeCSMTest is SetMerkleGateTreeTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CSM";
    }

    function _stakingModule() internal view override returns (address) {
        return config.csmModule;
    }

    function _otherStakingModule() internal view override returns (address) {
        return config.cmModule;
    }
}

contract SetMerkleGateTreeCMTest is SetMerkleGateTreeTest {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CM";
    }

    function _stakingModule() internal view override returns (address) {
        return config.cmModule;
    }

    function _otherStakingModule() internal view override returns (address) {
        return config.csmModule;
    }
}
