// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

import { Test } from "forge-std/Test.sol";
import { IEasyTrack, IEVMScriptFactory } from "../interfaces/EasyTrack.sol";
import {
    IAccessControlEnumerable,
    IStakingRouter,
    ILidoLocator,
    IBaseModule,
    IAccounting,
    IMetaRegistry,
    NodeOperatorManagementProperties
} from "../interfaces/External.sol";

/// @title EasyTrackScenarioBase
/// @notice Fork harness for happy-path scenario tests of the deployed Easy Track factories. Fork
///         raising and the state-construction recipes follow lidofinance/staking-modules `Fixtures.sol`.
///         A test builds calldata + preconditions and asserts the effect; the base forks, requires the
///         factory to be registered in Easy Track, and runs the motion (create -> warp -> enact). It
///         does NOT authorize the motion: the factory registration and the executor's protocol roles
///         must be real (post-omnibus) state — role grants here only build data preconditions.
abstract contract EasyTrackScenarioBase is Test {
    struct NetworkConfig {
        uint256 chainId;
        string rpcEnvVar;
        string srArtifact;
        string smArtifact;
        address easyTrack;
        address agent; // admin of most protocol roles
    }

    struct Env {
        string chain;
        string rpcUrl;
    }

    string internal chainName;
    NetworkConfig internal cfg;
    IEasyTrack internal easyTrack;
    address internal executor;
    bool internal forked;

    bytes32 private _seed = keccak256("easy-track-scenario");

    // Set by a scenario's setUp so its tests can just call `enact(callData)`.
    address internal subject;
    address internal creator;

    // --- fork + config ---

    function envVars() internal returns (Env memory env) {
        env.chain = vm.envOr("CHAIN", string("hoodi"));
        cfg = _networkConfig(env.chain);
        env.rpcUrl = vm.envOr(cfg.rpcEnvVar, string(""));
    }

    function _forkAndInitialize() internal {
        Env memory env = envVars();
        chainName = env.chain;

        // Reuse an already-active fork (`forge test --fork-url …`); otherwise fork <CHAIN>_RPC_URL.
        if (cfg.easyTrack.code.length == 0) {
            if (bytes(env.rpcUrl).length == 0) {
                vm.skip(true, string.concat("no active fork and ", cfg.rpcEnvVar, " is not set"));
                return;
            }
            vm.createSelectFork(env.rpcUrl);
            require(block.chainid == cfg.chainId, "CHAIN/chainid mismatch");
        }
        forked = true;
        initializeFromDeployment();
    }

    function initializeFromDeployment() internal {
        easyTrack = IEasyTrack(cfg.easyTrack);
        executor = easyTrack.evmScriptExecutor();
        vm.label(cfg.easyTrack, "EasyTrack");
        vm.label(executor, "EVMScriptExecutor");
        vm.label(cfg.agent, "Agent");
    }

    function _networkConfig(string memory name) internal pure returns (NetworkConfig memory) {
        if (_eq(name, "hoodi")) {
            return NetworkConfig({
                chainId: 560048,
                rpcEnvVar: "HOODI_RPC_URL",
                srArtifact: "deployed-sr-hoodi.json",
                smArtifact: "deployed-sm-hoodi.json",
                easyTrack: 0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a,
                agent: 0x0534aA41907c9631fae990960bCC72d75fA7cfeD
            });
        }
        if (_eq(name, "mainnet")) {
            return NetworkConfig({
                chainId: 1,
                rpcEnvVar: "MAINNET_RPC_URL",
                srArtifact: "deployed-sr-mainnet.json",
                smArtifact: "deployed-sm-mainnet.json",
                easyTrack: 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea,
                agent: 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c
            });
        }
        revert(string.concat("unknown CHAIN: ", name));
    }

    /// @notice Read a factory address from a `deployed-*.json` by its key (keys contain ":").
    function _factoryAddress(string memory artifact, string memory key) internal view returns (address) {
        return vm.parseJsonAddress(vm.readFile(artifact), string.concat(".[\"", key, "\"].address"));
    }

    // --- motion lifecycle ---

    // Run the body only on a live fork, snapshotting/reverting so a reused fork is left unspoiled.
    modifier onlyForked() {
        if (!forked) return;
        uint256 snapshotId = vm.snapshotState();
        _;
        vm.revertToState(snapshotId);
    }

    function enact(bytes memory callData) internal returns (uint256) {
        return _runMotion(subject, creator, callData);
    }

    function _runMotion(address factory, address theCreator, bytes memory callData) internal returns (uint256 motionId) {
        bytes memory script = IEVMScriptFactory(factory).createEVMScript(theCreator, callData);
        (address[] memory targets, bytes[] memory datas) = _parseScriptCalls(script);

        _requireFactoryRegistered(factory, targets, datas);

        vm.prank(theCreator);
        motionId = easyTrack.createMotion(factory, callData);

        vm.warp(block.timestamp + easyTrack.motionDuration() + 1);

        vm.prank(makeAddr("stranger"));
        easyTrack.enactMotion(motionId, callData);
    }

    /// @notice Fail unless the factory is registered in Easy Track with permissions covering every
    ///         (target, selector) its script calls — i.e. the omnibus added it (no auto-registration).
    function _requireFactoryRegistered(address factory, address[] memory targets, bytes[] memory datas) private view {
        require(easyTrack.isEVMScriptFactory(factory), "factory not registered in EasyTrack");
        bytes memory granted = easyTrack.evmScriptFactoryPermissions(factory);
        require(
            _permissionsCover(granted, _permissionsFromCalls(targets, datas)),
            "factory missing permissions in EasyTrack"
        );
    }

    // --- roles: granted ONLY to build data preconditions (never to authorize the motion itself) ---
    // OZ AccessControl ids are keccak256(name); grants go through the target's own admin.

    function _role(string memory name) internal pure returns (bytes32) {
        return keccak256(bytes(name));
    }

    /// @notice Grant a named role on `target` to `account` (idempotent); logs the name.
    function _grantRole(address target, string memory roleName, address account) internal {
        IAccessControlEnumerable ac = IAccessControlEnumerable(target);
        bytes32 role = _role(roleName);
        if (ac.hasRole(role, account)) return;
        vm.prank(_roleAdmin(ac, role));
        ac.grantRole(role, account);
        assertTrue(ac.hasRole(role, account), "role grant failed");
        emit log_named_string("[setup] granted role for data prep", roleName);
        emit log_named_address("[setup]   on target", target);
        emit log_named_address("[setup]   to account", account);
    }

    // A current holder of the role's admin role, or the DAO Agent as a fallback.
    function _roleAdmin(IAccessControlEnumerable ac, bytes32 role) private view returns (address) {
        bytes32 adminRole = ac.getRoleAdmin(role);
        return ac.getRoleMemberCount(adminRole) > 0 ? ac.getRoleMember(adminRole, 0) : cfg.agent;
    }

    // --- module state construction (deterministic recipes, ported from staking-modules) ---

    function _keysSignatures(uint256 keysCount) internal pure returns (bytes memory keys, bytes memory signatures) {
        for (uint256 i; i < keysCount; ++i) {
            bytes memory index = abi.encodePacked(i + 1);
            keys = bytes.concat(keys, bytes.concat(new bytes(48 - index.length), index));
            signatures = bytes.concat(signatures, bytes.concat(new bytes(96 - index.length), index));
        }
    }

    function nextAddress(string memory label) internal returns (address a) {
        _seed = keccak256(abi.encodePacked(_seed));
        a = address(uint160(uint256(_seed)));
        vm.label(a, label);
    }

    // Mark all depositable keys as deposited (impersonating the staking router) so freshly added keys
    // count toward `totalDepositedKeys`.
    function _depositAllDepositable(IBaseModule module) internal {
        (,, uint256 depositable) = module.getStakingModuleSummary();
        if (depositable == 0) return;
        address sr = ILidoLocator(module.LIDO_LOCATOR()).stakingRouter();
        vm.prank(sr);
        module.obtainDepositData(depositable, "");
    }

    /// @notice Create a node operator with one bonded, deposited key. Curated modules need MetaRegistry
    ///         setup first — see `_prepareCuratedOperator`.
    function _createDepositedOperator(IBaseModule module) internal returns (uint256 nodeOperatorId) {
        _ensureResumed(module);
        _grantRole(address(module), "CREATE_NODE_OPERATOR_ROLE", address(this));
        address from = nextAddress("scenario-operator");
        nodeOperatorId =
            module.createNodeOperator(from, NodeOperatorManagementProperties(from, from, false), address(0));

        _prepareCuratedOperator(module, nodeOperatorId);

        IAccounting accounting = IAccounting(module.ACCOUNTING());
        (bytes memory keys, bytes memory signatures) = _keysSignatures(1);
        uint256 bond = accounting.getBondAmountByKeysCount(1, accounting.getBondCurveId(nodeOperatorId));
        vm.deal(from, bond);
        vm.prank(from);
        module.addValidatorKeysETH{ value: bond }(from, nodeOperatorId, 1, keys, signatures);

        _depositAllDepositable(module);
    }

    function _ensureResumed(IBaseModule module) internal {
        if (!module.isPaused()) return;
        _grantRole(address(module), "RESUME_ROLE", address(this));
        module.resume();
    }

    // No-op for CSM; curated variants override to call `_setupCuratedGroupAndCurve`.
    function _prepareCuratedOperator(IBaseModule module, uint256 nodeOperatorId) internal virtual {}

    // Put a curated operator in a MetaRegistry group with a non-zero bond-curve weight so it is depositable.
    function _setupCuratedGroupAndCurve(IBaseModule module, uint256 nodeOperatorId) internal {
        IMetaRegistry r = IMetaRegistry(module.META_REGISTRY());
        _grantRole(address(r), "MANAGE_OPERATOR_GROUPS_ROLE", address(this));
        _grantRole(address(r), "SET_BOND_CURVE_WEIGHT_ROLE", address(this));

        if (r.getNodeOperatorGroupId(nodeOperatorId) == r.NO_GROUP_ID()) {
            IMetaRegistry.SubNodeOperator[] memory subs = new IMetaRegistry.SubNodeOperator[](1);
            subs[0] = IMetaRegistry.SubNodeOperator({ nodeOperatorId: uint64(nodeOperatorId), share: 10000 });
            r.createOrUpdateOperatorGroup(
                r.NO_GROUP_ID(),
                IMetaRegistry.OperatorGroup("Group", subs, new IMetaRegistry.ExternalOperator[](0))
            );
        }

        uint256 curveId = IAccounting(module.ACCOUNTING()).getBondCurveId(nodeOperatorId);
        if (r.getBondCurveWeight(curveId) == 0) {
            r.setBondCurveWeight(curveId, 10000);
            module.batchDepositInfoUpdate(module.getNodeOperatorsCount());
        }
    }

    // --- EVMScript / permissions parsing ---
    // Script layout (contracts/libraries/EVMScriptCreator.sol): [4-byte SPEC_ID] then repeated
    // [20-byte target][4-byte uint32 calldataLen (incl. selector)][calldata]. A permission entry is
    // the 24-byte `target ++ selector`.

    function _parseScriptCalls(bytes memory s) private pure returns (address[] memory targets, bytes[] memory datas) {
        uint256 count;
        for (uint256 loc = 4; loc < s.length;) {
            loc += 24 + _uint32At(s, loc + 20);
            ++count;
        }
        targets = new address[](count);
        datas = new bytes[](count);
        uint256 i;
        for (uint256 loc = 4; loc < s.length; ++i) {
            uint32 clen = _uint32At(s, loc + 20);
            targets[i] = _addressAt(s, loc);
            datas[i] = _slice(s, loc + 24, clen);
            loc += 24 + clen;
        }
    }

    function _permissionsFromCalls(address[] memory targets, bytes[] memory datas) private pure returns (bytes memory perms) {
        for (uint256 i; i < targets.length; ++i) {
            perms = bytes.concat(perms, bytes20(targets[i]), bytes4(datas[i]));
        }
    }

    // Every 24-byte (target ++ selector) entry in `needed` must appear in `granted`.
    function _permissionsCover(bytes memory granted, bytes memory needed) private pure returns (bool) {
        for (uint256 n; n + 24 <= needed.length; n += 24) {
            bool found;
            for (uint256 g; g + 24 <= granted.length && !found; g += 24) {
                found = true;
                for (uint256 k; k < 24; ++k) {
                    if (needed[n + k] != granted[g + k]) {
                        found = false;
                        break;
                    }
                }
            }
            if (!found) return false;
        }
        return true;
    }

    function _slice(bytes memory data, uint256 offset, uint256 len) private pure returns (bytes memory out) {
        out = new bytes(len);
        for (uint256 i; i < len; ++i) out[i] = data[offset + i];
    }

    function _addressAt(bytes memory data, uint256 offset) private pure returns (address addr) {
        assembly {
            addr := shr(96, mload(add(add(data, 0x20), offset)))
        }
    }

    function _uint32At(bytes memory data, uint256 offset) private pure returns (uint32 v) {
        assembly {
            v := shr(224, mload(add(add(data, 0x20), offset)))
        }
    }

    function _eq(string memory a, string memory b) internal pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
