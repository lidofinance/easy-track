// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { EasyTrackScenarioBase } from "../../helpers/EasyTrackScenarioBase.sol";
import { IMerkleGate } from "../../interfaces/External.sol";
import { ISetMerkleGateTree } from "../../interfaces/Factories.sol";

/// @notice Deployed `SetMerkleGateTree` (deployed-sm-<chain>.json): a motion updates a module
///         gate's Merkle tree root & CID. The gate address is not in the easy-track sr/sm
///         artifacts, so each variant resolves it per chain (see the concrete contracts).
abstract contract SetMerkleGateTreeScenario is EasyTrackScenarioBase {
    IMerkleGate internal gate;

    function _factoryKey() internal pure virtual returns (string memory);

    /// @dev The module's Merkle gate for the selected chain.
    function _gate() internal view virtual returns (address);

    function setUp() public {
        _forkAndInitialize();
        if (!forked) return;
        ISetMerkleGateTree factory = ISetMerkleGateTree(_factoryAddress(cfg.smArtifact, _factoryKey()));
        gate = IMerkleGate(_gate());
        subject = address(factory);
        creator = factory.trustedCaller();
    }

    function test_setsGateTree() external onlyForked {
        (bytes32 newRoot, string memory newCid, bytes memory callData) = _plannedTreeUpdate();

        enact(callData);

        assertEq(gate.treeRoot(), newRoot, "treeRoot not updated");
        assertEq(keccak256(bytes(gate.treeCid())), keccak256(bytes(newCid)), "treeCid not updated");
    }

    function _plannedTreeUpdate() private view returns (bytes32 newRoot, string memory newCid, bytes memory callData) {
        bytes32 curRoot = gate.treeRoot();
        string memory curCid = gate.treeCid();
        newRoot = keccak256(abi.encodePacked("scenario-root", curRoot));
        newCid = string.concat("scenario-cid-", curCid);
        callData = abi.encode(address(gate), curRoot, curCid, newRoot, newCid);
    }

    function _chainConstant(address hoodi, address mainnet) internal view returns (address) {
        if (_eq(chainName, "hoodi")) return hoodi;
        if (_eq(chainName, "mainnet")) return mainnet;
        revert(string.concat("no gate configured for CHAIN=", chainName));
    }
}

contract SetMerkleGateTreeCSMScenario is SetMerkleGateTreeScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CSM";
    }

    /// @dev CSM ICS VettedGate — recorded in easy-track's own deployed-csm-<chain>.json.
    function _gate() internal view override returns (address) {
        string memory json = vm.readFile(string.concat("deployed-csm-", chainName, ".json"));
        return vm.parseJsonAddress(json, ".[\"CSMSetVettedGateTree\"].constructorArgs[2]");
    }
}

// CM CuratedGate[0] from lidofinance/staking-modules artifacts/<chain>/curated/deploy-<chain>.json
contract SetMerkleGateTreeCMScenario is SetMerkleGateTreeScenario {
    function _factoryKey() internal pure override returns (string memory) {
        return "SetMerkleGateTree:CM";
    }

    function _gate() internal view override returns (address) {
        return _chainConstant(
            0xF1862d120831eBE31f7202378Ff3Ae63A5658ae3, // hoodi
            0x6093EFA6B5E2FF3be54d1c895c9deA932805c49F // mainnet
        );
    }
}
