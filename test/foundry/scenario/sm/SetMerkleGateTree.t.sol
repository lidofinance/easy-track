// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import { IMerkleGate, IAccessControlEnumerable } from "../../interfaces/External.sol";
import { ISetMerkleGateTree } from "../../interfaces/Factories.sol";

/// @notice Deployed `SetMerkleGateTree` (deployed-sm-<chain>.json): a motion updates a module gate's
///         Merkle tree root & CID. The gate is discovered on-chain (see `_managedGate`)
abstract contract SetMerkleGateTreeScenario is EasyTrackScenarioBase {
    IMerkleGate internal gate;

    function _factoryKey() internal pure virtual returns (string memory);

    /// @dev The staking module (from `_networkConfig`) whose gate this factory manages.
    function _module() internal view virtual returns (address);

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        ISetMerkleGateTree factory = ISetMerkleGateTree(_factoryAddress(cfg.smArtifact, _factoryKey()));
        gate = IMerkleGate(_managedGate(_module()));
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_setsGateTree() external onlyForked {
        (bytes32 newRoot, string memory newCid, bytes memory callData) = _plannedTreeUpdate();

        enact(callData);

        assertEq(gate.treeRoot(), newRoot, "treeRoot not updated");
        assertEq(keccak256(bytes(gate.treeCid())), keccak256(bytes(newCid)), "treeCid not updated");
    }

    function _managedGate(address module) private view returns (address) {
        IAccessControlEnumerable ac = IAccessControlEnumerable(module);
        bytes32 createRole = _role("CREATE_NODE_OPERATOR_ROLE");
        bytes32 setTreeRole = _role("SET_TREE_ROLE");
        uint256 count = ac.getRoleMemberCount(createRole);
        for (uint256 i; i < count; ++i) {
            address candidate = ac.getRoleMember(createRole, i);
            (bool ok, bytes memory ret) =
                candidate.staticcall(abi.encodeWithSignature("hasRole(bytes32,address)", setTreeRole, executor));
            if (ok && ret.length == 32 && abi.decode(ret, (bool))) return candidate;
        }
        revert("no executor-managed merkle gate among module CREATE_NODE_OPERATOR_ROLE holders");
    }

    function _plannedTreeUpdate() private view returns (bytes32 newRoot, string memory newCid, bytes memory callData) {
        bytes32 curRoot = gate.treeRoot();
        string memory curCid = gate.treeCid();
        newRoot = keccak256(abi.encodePacked("scenario-root", curRoot));
        newCid = string.concat("scenario-cid-", curCid);
        callData = abi.encode(address(gate), curRoot, curCid, newRoot, newCid);
    }
}

contract SetMerkleGateTreeCSMScenario is SetMerkleGateTreeScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CSM";
    }

    function _module() internal view override returns (address) {
        return cfg.csmModule;
    }
}

contract SetMerkleGateTreeCMScenario is SetMerkleGateTreeScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CM";
    }

    function _module() internal view override returns (address) {
        return cfg.cmModule;
    }
}
