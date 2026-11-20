// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Script} from "forge-std/Script.sol";
import {Lido} from "script/helpers/Lido.sol";
import {ITokenManager, IVoting} from "test/foundry/interfaces/External.sol";

/// @notice Base of the Foundry scripts, the counterpart of `utils/` for the Brownie ones. A script
///         keeps its actions in public functions the scenario tests call on a fork, and `run`
///         reads their inputs from the environment, broadcasts them and records the result. The
///         base deploys the contracts of `contracts/` from the `forge build` artifacts, opens DAO
///         votes through the TokenManager and appends deployments to `deployed-<chain>.json`.
abstract contract EasyTrackScript is Script {
    /// @dev Id of the Aragon CallsScript executor
    bytes4 internal constant SPEC_ID = 0x00000001;

    // --- deployments ---

    /// @dev Deploy a contract of `contracts/` from the artifact `forge build` writes to `out/`
    function _deployArtifact(string memory name, bytes memory constructorArgs)
        internal
        returns (address deployed)
    {
        string memory artifact = string.concat("out/", name, ".sol/", name, ".json");
        require(vm.exists(artifact), string.concat(artifact, " is missing, run forge build"));

        deployed = deployCode(artifact, constructorArgs);
        vm.label(deployed, name);
    }

    /// @dev Add the contract to the chain's deployment record under its name
    function _recordDeployment(
        Lido.DAO memory dao,
        string memory contractName,
        address deployed,
        string memory constructorArgs
    ) internal {
        _recordDeployment(dao, contractName, contractName, deployed, constructorArgs);
    }

    /// @dev Add `key` to the chain's deployment record, the entry the Brownie scripts write:
    ///      the contract name, its address and `constructorArgs`, a JSON array of `_args`
    function _recordDeployment(
        Lido.DAO memory dao,
        string memory key,
        string memory contractName,
        address deployed,
        string memory constructorArgs
    ) internal {
        string memory path = dao.deployedArtifact;
        string memory entry = string.concat(
            '{"contract": "',
            contractName,
            '", "address": "',
            vm.toString(deployed),
            '", "constructorArgs": ',
            constructorArgs,
            "}"
        );

        string memory record = vm.serializeJson(path, vm.exists(path) ? vm.readFile(path) : "{}");
        record = vm.serializeString(path, key, entry);
        vm.writeJson(record, path);
    }

    // --- constructor arguments as the deployment record lists them ---

    function _arg(address value) internal pure returns (string memory) {
        return string.concat('"', vm.toString(value), '"');
    }

    function _arg(uint256 value) internal pure returns (string memory) {
        return vm.toString(value);
    }

    function _arg(address[] memory values) internal pure returns (string memory list) {
        for (uint256 i; i < values.length; ++i) {
            list = string.concat(list, i == 0 ? "" : ", ", _arg(values[i]));
        }

        return string.concat("[", list, "]");
    }

    function _args(string memory a) internal pure returns (string memory) {
        return string.concat("[", a, "]");
    }

    function _args(string memory a, string memory b) internal pure returns (string memory) {
        return string.concat("[", a, ", ", b, "]");
    }

    function _args(string memory a, string memory b, string memory c)
        internal
        pure
        returns (string memory)
    {
        return string.concat("[", a, ", ", b, ", ", c, "]");
    }

    function _args(string memory a, string memory b, string memory c, string memory d)
        internal
        pure
        returns (string memory)
    {
        return string.concat("[", a, ", ", b, ", ", c, ", ", d, "]");
    }

    function _args(
        string memory a,
        string memory b,
        string memory c,
        string memory d,
        string memory e
    ) internal pure returns (string memory) {
        return string.concat("[", a, ", ", b, ", ", c, ", ", d, ", ", e, "]");
    }

    // --- DAO votes ---

    /// @dev `encode_call_script`: an Aragon CallsScript of one call
    function _encodeCallScript(address target, bytes memory callData)
        internal
        pure
        returns (bytes memory)
    {
        return abi.encodePacked(SPEC_ID, target, uint32(callData.length), callData);
    }

    /// @dev `encode_call_script`: an Aragon CallsScript of `callDatas` on one target
    function _encodeCallScript(address target, bytes[] memory callDatas)
        internal
        pure
        returns (bytes memory script)
    {
        script = abi.encodePacked(SPEC_ID);
        for (uint256 i; i < callDatas.length; ++i) {
            script = abi.encodePacked(script, target, uint32(callDatas[i].length), callDatas[i]);
        }
    }

    /// @dev The script of a vote calling the ACL's `selector` for `entity` on each permission
    function _encodePermissionsScript(
        Lido.DAO memory dao,
        bytes4 selector,
        address entity,
        Lido.Permission[] memory permissions
    ) internal view returns (bytes memory) {
        bytes[] memory callDatas = new bytes[](permissions.length);
        for (uint256 i; i < callDatas.length; ++i) {
            callDatas[i] = abi.encodeWithSelector(
                selector, entity, permissions[i].app, Lido.roleId(permissions[i])
            );
        }

        return _encodeCallScript(address(Lido.acl(dao)), callDatas);
    }

    /// @dev `create_voting`: open a vote on `evmScript` through the TokenManager, from an account
    ///      that holds LDO
    function _createVote(Lido.DAO memory dao, bytes memory evmScript, string memory description)
        internal
        returns (uint256 voteId)
    {
        IVoting voting = IVoting(dao.voting);
        voteId = voting.votesLength();

        ITokenManager(dao.tokenManager)
            .forward(
                _encodeCallScript(
                    dao.voting, abi.encodeCall(IVoting.newVote, (evmScript, description))
                )
            );

        require(voting.votesLength() == voteId + 1, "vote not opened");
    }
}
