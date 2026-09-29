// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {IEasyTrack} from "test/foundry/interfaces/EasyTrack.sol";
import {IAccessControlEnumerable, IAccounting, IBaseModule, ILidoLocator, IMetaRegistry, NodeOperatorManagementProperties} from "test/foundry/interfaces/External.sol";

/// @notice Fork harness for the scenario tests of the deployed Easy Track factories. A test
///         builds the on-chain data a motion needs, runs the motion and asserts its effect. The
///         harness forks the chain, resolves factories from `deployed-*.json` and drives the
///         motion lifecycle, create -> warp -> enact. It never authorizes the
///         motion: Easy Track itself rejects a factory the omnibus has not registered, and the
///         executor's protocol roles must be real on-chain state. Role grants here only build
///         data preconditions. The state-construction recipes follow lidofinance/staking-modules
///         `Fixtures.sol`.
abstract contract EasyTrackScenarioBase is Test {
    struct NetworkConfig {
        uint256 chainId;
        string rpcEnvVar;
        string srArtifact;
        string smArtifact;
        address easyTrack;
        /// @dev admin of most protocol roles
        address agent;
        address csmModule;
        address cmModule;
    }

    /// @dev OZ AccessControl role ids: keccak256 of the role name
    bytes32 internal constant CREATE_NODE_OPERATOR_ROLE = keccak256("CREATE_NODE_OPERATOR_ROLE");
    bytes32 internal constant RESUME_ROLE = keccak256("RESUME_ROLE");
    bytes32 internal constant MANAGE_OPERATOR_GROUPS_ROLE =
        keccak256("MANAGE_OPERATOR_GROUPS_ROLE");
    bytes32 internal constant SET_BOND_CURVE_WEIGHT_ROLE = keccak256("SET_BOND_CURVE_WEIGHT_ROLE");

    /// @dev A sub node operator's share of its MetaRegistry group, in basis points
    uint16 internal constant FULL_SHARE = 10000;

    /// @dev Any non-zero bond-curve weight makes a curated operator depositable
    uint256 internal constant BOND_CURVE_WEIGHT = 10000;

    /// @dev `ExternalOperatorLib.OperatorType.NOR`, the first byte of `ExternalOperator.data`
    bytes1 internal constant EXT_OPERATOR_TYPE_NOR = 0x00;

    uint256 internal constant KEYS_PER_OPERATOR = 1;
    uint256 private constant PUBKEY_LENGTH = 48;
    uint256 private constant SIGNATURE_LENGTH = 96;

    string private constant CURATED_GROUP_NAME = "scenario-curated-group";

    NetworkConfig internal config;
    IEasyTrack internal easyTrack;
    address internal evmScriptExecutor;

    /// @dev Set by a scenario's setUp: the deployed factory under test and the account allowed to
    ///      create its motions
    address internal evmScriptFactory;
    address internal creator;
    address internal stranger = makeAddr("stranger");

    uint256 private _operatorsCreated;

    // --- fork + config ---

    /// @dev Fork `CHAIN` (default hoodi) from `<CHAIN>_RPC_URL`, or reuse an already-active fork
    ///      (`forge test --fork-url …`). Skips the suite when neither is available.
    function _forkAndInitialize() internal {
        config = _networkConfig(vm.envOr("CHAIN", string("hoodi")));

        if (config.easyTrack.code.length == 0) {
            string memory rpcUrl = vm.envOr(config.rpcEnvVar, string(""));
            vm.skip(
                bytes(rpcUrl).length == 0,
                string.concat("no active fork and ", config.rpcEnvVar, " is not set")
            );

            vm.createSelectFork(rpcUrl);
            require(block.chainid == config.chainId, "CHAIN/chainid mismatch");
        }

        easyTrack = IEasyTrack(config.easyTrack);
        evmScriptExecutor = easyTrack.evmScriptExecutor();

        vm.label(config.easyTrack, "EasyTrack");
        vm.label(evmScriptExecutor, "EVMScriptExecutor");
        vm.label(config.agent, "Agent");
    }

    function _networkConfig(string memory chain) private pure returns (NetworkConfig memory) {
        if (_equals(chain, "hoodi")) {
            return
                NetworkConfig({
                    chainId: 560048,
                    rpcEnvVar: "HOODI_RPC_URL",
                    srArtifact: "deployed-sr-hoodi.json",
                    smArtifact: "deployed-sm-hoodi.json",
                    easyTrack: 0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a,
                    agent: 0x0534aA41907c9631fae990960bCC72d75fA7cfeD,
                    csmModule: 0x79CEf36D84743222f37765204Bec41E92a93E59d,
                    cmModule: 0x87EB69Ae51317405FD285efD2326a4a11f6173b9
                });
        }

        if (_equals(chain, "mainnet")) {
            return
                NetworkConfig({
                    chainId: 1,
                    rpcEnvVar: "MAINNET_RPC_URL",
                    srArtifact: "deployed-sr-mainnet.json",
                    smArtifact: "deployed-sm-mainnet.json",
                    easyTrack: 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea,
                    agent: 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c,
                    csmModule: 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F,
                    cmModule: 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1
                });
        }

        revert(string.concat("unknown CHAIN: ", chain));
    }

    /// @dev A factory address of a `deployed-*.json` by its key (keys contain ":")
    function _factoryAddress(string memory artifact, string memory key)
        internal
        view
        returns (address)
    {
        return vm.parseJsonAddress(vm.readFile(artifact), string.concat('.["', key, '"].address'));
    }

    // --- motion lifecycle ---

    /// @dev Create a motion for the factory under test and enact it once its duration has passed
    function _enact(bytes memory callData) internal {
        uint256 motionId = _createMotion(callData);

        _enactMotion(motionId, callData);
    }

    function _createMotion(bytes memory callData) internal returns (uint256 motionId) {
        vm.prank(creator);
        motionId = easyTrack.createMotion(evmScriptFactory, callData);
    }

    function _enactMotion(uint256 motionId, bytes memory callData) internal {
        _givenMotionDurationPassed();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);
    }

    function _givenMotionDurationPassed() internal {
        vm.warp(vm.getBlockTimestamp() + easyTrack.motionDuration() + 1);
    }

    // --- roles, granted only to build data preconditions, never to authorize the motion ---

    /// @dev Grant `role` on `target` to `account` through the role's admin, unless already held
    function _givenRole(
        address target,
        bytes32 role,
        address account
    ) internal {
        IAccessControlEnumerable accessControl = IAccessControlEnumerable(target);
        if (accessControl.hasRole(role, account)) {
            return;
        }

        vm.prank(_roleAdmin(accessControl, role));
        accessControl.grantRole(role, account);
    }

    /// @dev A current holder of the role's admin role, or the DAO Agent as a fallback
    function _roleAdmin(IAccessControlEnumerable accessControl, bytes32 role)
        private
        view
        returns (address)
    {
        bytes32 adminRole = accessControl.getRoleAdmin(role);

        return
            accessControl.getRoleMemberCount(adminRole) > 0
                ? accessControl.getRoleMember(adminRole, 0)
                : config.agent;
    }

    // --- module state construction ---

    /// @dev A node operator with one bonded, deposited key. Curated modules first need the
    ///      MetaRegistry setup of `_prepareCuratedOperator`.
    function _givenDepositedOperator(IBaseModule module) internal returns (uint256 nodeOperatorId) {
        _givenModuleResumed(module);
        _givenRole(address(module), CREATE_NODE_OPERATOR_ROLE, address(this));

        ++_operatorsCreated;
        address operator = makeAddr(
            string.concat("scenarioOperator", vm.toString(_operatorsCreated))
        );
        nodeOperatorId = module.createNodeOperator(
            operator,
            NodeOperatorManagementProperties(operator, operator, false),
            address(0)
        );

        _prepareCuratedOperator(module, nodeOperatorId);

        IAccounting accounting = IAccounting(module.ACCOUNTING());
        uint256 bond = accounting.getBondAmountByKeysCount(
            KEYS_PER_OPERATOR,
            accounting.getBondCurveId(nodeOperatorId)
        );
        (bytes memory keys, bytes memory signatures) = _keysSignatures(KEYS_PER_OPERATOR);

        vm.deal(operator, bond);

        vm.prank(operator);
        module.addValidatorKeysETH{value: bond}(
            operator,
            nodeOperatorId,
            KEYS_PER_OPERATOR,
            keys,
            signatures
        );

        _givenDepositableKeysDeposited(module);
    }

    /// @dev No-op for CSM. Curated variants override it with `_givenCuratedOperatorDepositable`.
    function _prepareCuratedOperator(IBaseModule module, uint256 nodeOperatorId) internal virtual {}

    /// @dev Put a curated operator in a MetaRegistry group with a non-zero bond-curve weight so it
    ///      is depositable
    function _givenCuratedOperatorDepositable(IBaseModule module, uint256 nodeOperatorId) internal {
        IMetaRegistry metaRegistry = IMetaRegistry(module.META_REGISTRY());
        _givenRole(address(metaRegistry), MANAGE_OPERATOR_GROUPS_ROLE, address(this));
        _givenRole(address(metaRegistry), SET_BOND_CURVE_WEIGHT_ROLE, address(this));

        if (metaRegistry.getNodeOperatorGroupId(nodeOperatorId) == metaRegistry.NO_GROUP_ID()) {
            metaRegistry.createOrUpdateOperatorGroup(
                metaRegistry.NO_GROUP_ID(),
                IMetaRegistry.OperatorGroup(
                    CURATED_GROUP_NAME,
                    _subNodeOperators(uint64(nodeOperatorId)),
                    new IMetaRegistry.ExternalOperator[](0)
                )
            );
        }

        uint256 curveId = IAccounting(module.ACCOUNTING()).getBondCurveId(nodeOperatorId);
        if (metaRegistry.getBondCurveWeight(curveId) == 0) {
            metaRegistry.setBondCurveWeight(curveId, BOND_CURVE_WEIGHT);
            module.batchDepositInfoUpdate(module.getNodeOperatorsCount());
        }
    }

    /// @dev A group's sub node operator list holding one operator with the full share
    function _subNodeOperators(uint64 nodeOperatorId)
        internal
        pure
        returns (IMetaRegistry.SubNodeOperator[] memory subNodeOperators)
    {
        subNodeOperators = new IMetaRegistry.SubNodeOperator[](1);
        subNodeOperators[0] = IMetaRegistry.SubNodeOperator({
            nodeOperatorId: nodeOperatorId,
            share: FULL_SHARE
        });
    }

    /// @dev A group's external operator list holding one legacy NOR operator
    function _externalOperators(uint256 moduleId, uint64 nodeOperatorId)
        internal
        pure
        returns (IMetaRegistry.ExternalOperator[] memory externalOperators)
    {
        externalOperators = new IMetaRegistry.ExternalOperator[](1);
        externalOperators[0] = _externalOperator(moduleId, nodeOperatorId);
    }

    /// @dev A legacy NOR operator as a MetaRegistry external operator:
    ///      `[operatorType:1 byte][moduleId:1 byte][nodeOperatorId:8 bytes]`
    function _externalOperator(uint256 moduleId, uint64 nodeOperatorId)
        internal
        pure
        returns (IMetaRegistry.ExternalOperator memory)
    {
        return
            IMetaRegistry.ExternalOperator({
                data: abi.encodePacked(EXT_OPERATOR_TYPE_NOR, uint8(moduleId), nodeOperatorId)
            });
    }

    function _givenModuleResumed(IBaseModule module) private {
        if (!module.isPaused()) {
            return;
        }

        _givenRole(address(module), RESUME_ROLE, address(this));
        module.resume();
    }

    /// @dev Mark every depositable key as deposited, impersonating the staking router, so freshly
    ///      added keys count toward the deposited total
    function _givenDepositableKeysDeposited(IBaseModule module) private {
        (, , uint256 depositable) = module.getStakingModuleSummary();
        if (depositable == 0) {
            return;
        }

        vm.prank(ILidoLocator(module.LIDO_LOCATOR()).stakingRouter());
        module.obtainDepositData(depositable, "");
    }

    /// @dev Deterministic keys and signatures: the 1-based key index, right-aligned in zero-padded
    ///      bytes of the pubkey and signature lengths
    function _keysSignatures(uint256 keysCount)
        private
        pure
        returns (bytes memory keys, bytes memory signatures)
    {
        for (uint256 i; i < keysCount; ++i) {
            bytes memory index = abi.encodePacked(i + 1);
            keys = bytes.concat(keys, new bytes(PUBKEY_LENGTH - index.length), index);
            signatures = bytes.concat(
                signatures,
                new bytes(SIGNATURE_LENGTH - index.length),
                index
            );
        }
    }

    function _equals(string memory a, string memory b) private pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
