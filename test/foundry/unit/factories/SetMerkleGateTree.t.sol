// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SetMerkleGateTree,
    ISetMerkleGateTree
} from "contracts/EVMScriptFactories/SetMerkleGateTree.sol";
import {IMerkleGate} from "contracts/interfaces/IMerkleGate.sol";
import {MerkleGateStub} from "contracts/test/MerkleGateStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SetMerkleGateTreeTest is Test {
    string internal constant FACTORY_NAME = "CSM v3";
    bytes32 internal constant TREE_ROOT =
        0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef;
    bytes32 internal constant ANOTHER_TREE_ROOT =
        0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890;
    /// @dev python: bytes.fromhex("ff" * 32)
    bytes32 internal constant WRONG_TREE_ROOT =
        0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff;
    /// @dev python: bytes.fromhex("ab" * 32)
    bytes32 internal constant CHANGED_TREE_ROOT =
        0xabababababababababababababababababababababababababababababababab;
    /// @dev python: bytes.fromhex("aabbccdd" * 8)
    bytes32 internal constant CURRENT_TREE_ROOT =
        0xaabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccddaabbccdd;
    string internal constant TREE_CID = "QmTest123456789";
    string internal constant NEW_TREE_CID = "QmNewCid";

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    MerkleGateStub internal merkleGateStub;
    SetMerkleGateTree internal setMerkleGateTree;

    function setUp() public {
        // the stub grants its roles to the deployer, so the owner deploys it
        vm.startPrank(owner);
        merkleGateStub = new MerkleGateStub();
        setMerkleGateTree = new SetMerkleGateTree(owner, FACTORY_NAME);
        vm.stopPrank();

        vm.label(address(merkleGateStub), "merkleGateStub");
        vm.label(address(setMerkleGateTree), "setMerkleGateTree");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setMerkleGateTree.trustedCaller(), owner, "trustedCaller");
        assertEq(setMerkleGateTree.name(), FACTORY_NAME, "name");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setMerkleGateTree.createEVMScript(stranger, "");
    }

    // python: test_empty_tree_root
    function test_RevertWhen_TreeRootIsEmpty() external {
        vm.expectRevert("EMPTY_TREE_ROOT");
        setMerkleGateTree.createEVMScript(owner, _callData(bytes32(0), "", bytes32(0), "test_cid"));
    }

    // python: test_empty_tree_cid
    function test_RevertWhen_TreeCidIsEmpty() external {
        vm.expectRevert("EMPTY_TREE_CID");
        setMerkleGateTree.createEVMScript(owner, _callData(bytes32(0), "", TREE_ROOT, ""));
    }

    // python: test_same_tree_root
    function test_RevertWhen_TreeRootIsSame() external {
        _setTreeParams(TREE_ROOT, TREE_CID);

        vm.expectRevert("SAME_TREE_ROOT");
        setMerkleGateTree.createEVMScript(
            owner, _callData(TREE_ROOT, TREE_CID, TREE_ROOT, "QmTest1234567890")
        );
    }

    // python: test_same_tree_cid
    function test_RevertWhen_TreeCidIsSame() external {
        _setTreeParams(TREE_ROOT, TREE_CID);

        vm.expectRevert("SAME_TREE_CID");
        setMerkleGateTree.createEVMScript(
            owner, _callData(TREE_ROOT, TREE_CID, ANOTHER_TREE_ROOT, TREE_CID)
        );
    }

    // python: test_current_tree_root_mismatch
    function test_RevertWhen_CurrentTreeRootMismatches() external {
        _setTreeParams(TREE_ROOT, TREE_CID);

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        setMerkleGateTree.createEVMScript(
            owner, _callData(WRONG_TREE_ROOT, TREE_CID, ANOTHER_TREE_ROOT, NEW_TREE_CID)
        );
    }

    // python: test_current_tree_cid_mismatch
    function test_RevertWhen_CurrentTreeCidMismatches() external {
        _setTreeParams(TREE_ROOT, TREE_CID);

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        setMerkleGateTree.createEVMScript(
            owner, _callData(TREE_ROOT, "QmWrongCid", ANOTHER_TREE_ROOT, NEW_TREE_CID)
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        bytes32 currentTreeRoot = merkleGateStub.treeRoot();
        string memory currentTreeCid = merkleGateStub.treeCid();

        bytes memory evmScript = setMerkleGateTree.createEVMScript(
            owner, _callData(currentTreeRoot, currentTreeCid, TREE_ROOT, TREE_CID)
        );

        assertEq(
            evmScript,
            _setTreeParamsScript(currentTreeRoot, currentTreeCid, TREE_ROOT, TREE_CID),
            "evmScript"
        );
    }

    // python: test_validate_input_data_reverts_if_tree_state_changed
    function test_RevertWhen_ValidatingInputDataAfterTreeStateChanged() external {
        bytes32 oldTreeRoot = merkleGateStub.treeRoot();
        string memory oldTreeCid = merkleGateStub.treeCid();

        _setTreeParams(CHANGED_TREE_ROOT, "QmChangedCid");

        vm.expectRevert("CURRENT_VALUES_MISMATCH");
        setMerkleGateTree.validateInputData(
            address(merkleGateStub), oldTreeRoot, oldTreeCid, TREE_ROOT, TREE_CID
        );
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        (
            address gate,
            bytes32 currentTreeRoot,
            string memory currentTreeCid,
            bytes32 newTreeRoot,
            string memory newTreeCid
        ) = setMerkleGateTree.decodeEVMScriptCallData(
            _callData(CURRENT_TREE_ROOT, "QmCurrentCid", TREE_ROOT, TREE_CID)
        );

        assertEq(gate, address(merkleGateStub), "gate");
        assertEq(currentTreeRoot, CURRENT_TREE_ROOT, "currentTreeRoot");
        assertEq(currentTreeCid, "QmCurrentCid", "currentTreeCid");
        assertEq(newTreeRoot, TREE_ROOT, "newTreeRoot");
        assertEq(newTreeCid, TREE_CID, "newTreeCid");
    }

    /// @dev python: merkle_gate_stub.setTreeParams(tree_root, tree_cid, {"from": owner})
    function _setTreeParams(bytes32 treeRoot, string memory treeCid) private {
        vm.prank(owner);
        merkleGateStub.setTreeParams(treeRoot, treeCid);
    }

    /// @dev python: C, always over merkle_gate_stub
    function _callData(
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) private view returns (bytes memory) {
        return abi.encode(
            address(merkleGateStub), currentTreeRoot, currentTreeCid, newTreeRoot, newTreeCid
        );
    }

    /// @dev python: encode_call_script of validateInputData with the original inputs, then
    /// merkle_gate_stub.setTreeParams
    function _setTreeParamsScript(
        bytes32 currentTreeRoot,
        string memory currentTreeCid,
        bytes32 newTreeRoot,
        string memory newTreeCid
    ) private view returns (bytes memory) {
        address[] memory targets = new address[](2);
        targets[0] = address(setMerkleGateTree);
        targets[1] = address(merkleGateStub);

        bytes[] memory datas = new bytes[](2);
        datas[0] = abi.encodeWithSelector(
            ISetMerkleGateTree.validateInputData.selector,
            address(merkleGateStub),
            currentTreeRoot,
            currentTreeCid,
            newTreeRoot,
            newTreeCid
        );
        datas[1] =
            abi.encodeWithSelector(IMerkleGate.setTreeParams.selector, newTreeRoot, newTreeCid);

        return EVMScripts.encodeCallScript(targets, datas);
    }
}
