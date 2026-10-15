// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {IEasyTrack, IEVMScriptExecutor} from "test/foundry/interfaces/EasyTrack.sol";
import {
    IACL,
    IAccessControlEnumerable,
    IAccounting,
    IAragonApp,
    IBaseModule,
    IKernel,
    ILidoLocator,
    IMetaRegistry,
    NodeOperatorManagementProperties
} from "test/foundry/interfaces/External.sol";

/// @notice Fork harness for the scenario tests of the deployed Easy Track factories. A test
///         builds the on-chain data a motion needs, runs the motion and asserts its effect. The
///         harness forks the chain, resolves factories from `deployed-*.json` and drives the
///         motion lifecycle, create -> warp -> enact. The deployed factories run as the omnibus
///         registered them, and the executor's protocol roles are real on-chain state. Role
///         grants here only build data preconditions. Where a scenario needs a factory or stub
///         that is not deployed, `_deployArtifact` creates it from the `contracts` profile build,
///         `_registerFactory` registers it as the DAO Voting and `_grantPermission` grants it an
///         Aragon permission as the permission's manager, what a DAO vote enacts. The
///         state-construction recipes follow lidofinance/staking-modules `Fixtures.sol`.
abstract contract EasyTrackScenarioBase is Test {
    struct NetworkConfig {
        uint256 chainId;
        string rpcEnvVar;
        /// @dev the main Easy Track deployment, `deployed-<chain>.json`
        string artifact;
        string srArtifact;
        string smArtifact;
        /// @dev the payout deployments the Brownie suite parametrizes its payouts fixtures over,
        ///      `integration-test-addresses-<chain>.yaml`
        string addresses;
        address easyTrack;
        /// @dev admin of most protocol roles
        address agent;
        /// @dev the Aragon Finance app
        address finance;
        address csmModule;
        address cmModule;
        /// @dev the Lido locator, the root of the protocol contracts
        address locator;
        /// @dev the BokkyPooBahsDateTimeContract the payouts registries compute periods with
        address dateTime;
        address dai;
        address usdc;
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

    /// @dev `tests/constants.py`, the settings of every Easy Track a scenario deploys fresh
    uint256 internal constant MIN_MOTION_DURATION = 48 hours;
    uint256 internal constant MAX_MOTIONS_LIMIT = 24;
    uint256 internal constant DEFAULT_OBJECTIONS_THRESHOLD = 50;

    /// @dev Three deposit keys with their signatures, added to a legacy registry's operator in
    ///      one call
    uint256 internal constant SIGNING_KEYS_COUNT = 3;
    bytes internal constant SIGNING_KEYS_PUBKEYS = hex"8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7"
        hex"884b147305bcd9fce3a1cc12e8f893c6356c1780688286277656e1ba724a3fde49262c98503141c0925b344a8ccea9ca"
        hex"952ff22cf4a5f9708d536acb2170f83c137301515df5829adc28c265373487937cc45e8f91743caba0b9ebd02b3b664f";
    bytes internal constant SIGNING_KEYS_SIGNATURES = hex"ad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660"
        hex"9794e7871dc766c2139f9476234bc29784e13b51e859445044d2a5a9df8bc072d9c51c51ee69490ce37bdfc7cf899af2166b0710d620a87398d5ec7da06c9f7eb27f1d729973efd60052dbd4cb7f43ff6b141af4d0a0a980b60f663f39bf7844"
        hex"90111fb6944ff8b56eb0858c1deb91f41c8c631573f4c821663d7079e5e78903d67fa1c4a4ed358378f16a2b7ec524c5196b1a1eae35b01dca1df74535f45d6bd1960164a41425b2a289d4bb5c837049acf5871a0ed23598df42f6234276f6e2";

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
            return NetworkConfig({
                chainId: 560048,
                rpcEnvVar: "HOODI_RPC_URL",
                artifact: "deployed-hoodi.json",
                srArtifact: "deployed-sr-hoodi.json",
                smArtifact: "deployed-sm-hoodi.json",
                addresses: "integration-test-addresses-hoodi.yaml",
                easyTrack: 0x284D91a7D47850d21A6DEaaC6E538AC7E5E6fc2a,
                agent: 0x0534aA41907c9631fae990960bCC72d75fA7cfeD,
                finance: 0x254Ae22bEEba64127F0e59fe8593082F3cd13f6b,
                csmModule: 0x79CEf36D84743222f37765204Bec41E92a93E59d,
                cmModule: 0x87EB69Ae51317405FD285efD2326a4a11f6173b9,
                locator: 0xe2EF9536DAAAEBFf5b1c130957AB3E80056b06D8,
                dateTime: 0xd1df0cF660D531Fad9EAabD3e7b4E8881E28ae2F,
                dai: 0x17fc691f6EF57D2CA719d30b8fe040123d4ee319,
                usdc: 0x97bb030B93faF4684eAC76bA0bf3be5ec7140F36
            });
        }

        if (_equals(chain, "mainnet")) {
            return NetworkConfig({
                chainId: 1,
                rpcEnvVar: "MAINNET_RPC_URL",
                artifact: "deployed-mainnet.json",
                srArtifact: "deployed-sr-mainnet.json",
                smArtifact: "deployed-sm-mainnet.json",
                addresses: "integration-test-addresses-mainnet.yaml",
                easyTrack: 0xF0211b7660680B49De1A7E9f25C65660F0a13Fea,
                agent: 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c,
                finance: 0xB9E5CBB9CA5b0d659238807E84D0176930753d86,
                csmModule: 0xdA7dE2ECdDfccC6c3AF10108Db212ACBBf9EA83F,
                cmModule: 0xDa5F930cE326EB5205085D66c72A4E79d60cB8C1,
                locator: 0xC1d0b3DE6792Bf6b4b37EccdcC24e45978Cfd2Eb,
                dateTime: 0x75100bd564415731B5936A4A94D0dC29DdE5dB3C,
                dai: 0x6B175474E89094C44Da98b954EedeAC495271d0F,
                usdc: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
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

    /// @dev `_factoryAddress`, or zero when the artifact has no such key
    function _optionalFactoryAddress(string memory artifact, string memory key)
        internal
        view
        returns (address)
    {
        string memory json = vm.readFile(artifact);
        string memory path = string.concat('.["', key, '"]');

        return vm.keyExistsJson(json, path)
            ? vm.parseJsonAddress(json, string.concat(path, ".address"))
            : address(0);
    }

    // --- motion lifecycle ---

    /// @dev Create a motion for the factory under test and enact it once its duration has passed
    function _enact(bytes memory callData) internal {
        _enact(evmScriptFactory, creator, callData);
    }

    /// @dev Create a motion for `factory` from `motionCreator` and enact it once its duration has
    ///      passed
    function _enact(address factory, address motionCreator, bytes memory callData) internal {
        uint256 motionId = _createMotion(factory, motionCreator, callData);

        _enactMotion(motionId, callData);
    }

    function _createMotion(bytes memory callData) internal returns (uint256) {
        return _createMotion(evmScriptFactory, creator, callData);
    }

    function _createMotion(address factory, address motionCreator, bytes memory callData)
        internal
        returns (uint256 motionId)
    {
        vm.prank(motionCreator);
        motionId = easyTrack.createMotion(factory, callData);
    }

    function _enactMotion(uint256 motionId, bytes memory callData) internal {
        _passMotionDuration();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);
    }

    function _passMotionDuration() internal {
        vm.warp(vm.getBlockTimestamp() + easyTrack.motionDuration() + 1);
    }

    // --- DAO actions: factory registration and deployments a vote would make ---

    /// @dev The DAO Voting: the executor's owner and Easy Track's admin
    function _voting() internal view returns (address) {
        return IEVMScriptExecutor(evmScriptExecutor).owner();
    }

    /// @dev Register `factory` with `permissions`, as a DAO vote does
    function _registerFactory(address factory, bytes memory permissions) internal {
        vm.prank(_voting());
        easyTrack.addEVMScriptFactory(factory, permissions);

        assertTrue(easyTrack.isEVMScriptFactory(factory), "setup: isEVMScriptFactory");
    }

    /// @dev Register `factory` with `permissions` unless Easy Track already lists it
    function _registerFactoryIfMissing(address factory, bytes memory permissions) internal {
        if (easyTrack.isEVMScriptFactory(factory)) {
            return;
        }

        _registerFactory(factory, permissions);
    }

    /// @dev Re-register the factory under test with `permissions`, as a DAO vote does
    function _replaceFactoryPermissions(bytes memory permissions) internal {
        vm.startPrank(_voting());
        easyTrack.removeEVMScriptFactory(evmScriptFactory);
        easyTrack.addEVMScriptFactory(evmScriptFactory, permissions);
        vm.stopPrank();
    }

    /// @dev A fresh Easy Track with `admin` and an executor owned by Voting, both from the
    ///      `contracts` profile artifacts. The base helpers drive this pair from here on instead
    ///      of the deployed one.
    function _deployEasyTrack(address admin) internal {
        _deployEasyTrack(
            admin, MIN_MOTION_DURATION, MAX_MOTIONS_LIMIT, DEFAULT_OBJECTIONS_THRESHOLD
        );
    }

    /// @dev The same with the motion settings given
    function _deployEasyTrack(
        address admin,
        uint256 motionDuration,
        uint256 motionsCountLimit,
        uint256 objectionsThreshold
    ) internal {
        address ldo = easyTrack.governanceToken();
        address callsScript = IEVMScriptExecutor(evmScriptExecutor).callsScript();
        address voting = _voting();

        easyTrack = IEasyTrack(
            _deployArtifact(
                "EasyTrack",
                abi.encode(ldo, admin, motionDuration, motionsCountLimit, objectionsThreshold)
            )
        );
        evmScriptExecutor = _deployArtifact("EVMScriptExecutor", abi.encode(callsScript, easyTrack));

        IEVMScriptExecutor(evmScriptExecutor).transferOwnership(voting);

        assertEq(IEVMScriptExecutor(evmScriptExecutor).owner(), voting, "setup: executor owner");

        vm.prank(admin);
        easyTrack.setEVMScriptExecutor(evmScriptExecutor);
    }

    /// @dev Voting becomes the admin of the fresh Easy Track and the test stops being one
    function _handAdminToVoting() internal {
        bytes32 adminRole = easyTrack.DEFAULT_ADMIN_ROLE();
        address voting = _voting();

        easyTrack.grantRole(adminRole, voting);

        assertTrue(easyTrack.hasRole(adminRole, voting), "setup: Voting is admin");

        easyTrack.revokeRole(adminRole, address(this));

        assertFalse(easyTrack.hasRole(adminRole, address(this)), "setup: deployer is not admin");
    }

    /// @dev The DAO ACL, through the Agent's kernel
    function _acl() internal view returns (IACL) {
        return IACL(IKernel(IAragonApp(config.agent).kernel()).acl());
    }

    /// @dev Grant `entity` the Aragon permission `role` on `app` as the permission's manager, what
    ///      a DAO vote enacts
    function _grantPermission(address entity, address app, bytes32 role) internal {
        IACL acl = _acl();
        address manager = acl.getPermissionManager(app, role);

        vm.prank(manager);
        acl.grantPermission(entity, app, role);
    }

    /// @dev Deploy a contract of `contracts/` from the artifact `FOUNDRY_PROFILE=contracts forge
    ///      build` writes, with the test as the deployer
    function _deployArtifact(string memory name, bytes memory constructorArgs)
        internal
        returns (address deployed)
    {
        string memory artifact = string.concat("out/", name, ".sol/", name, ".json");
        require(
            vm.exists(artifact),
            string.concat(artifact, " is missing, run FOUNDRY_PROFILE=contracts forge build")
        );

        deployed = deployCode(artifact, constructorArgs);
        vm.label(deployed, name);
    }

    // --- roles, granted only to build data preconditions, never to authorize the motion ---

    /// @dev Grant `role` on `target` to `account` through the role's admin, unless already held
    function _grantRole(address target, bytes32 role, address account) internal {
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

        return accessControl.getRoleMemberCount(adminRole) > 0
            ? accessControl.getRoleMember(adminRole, 0)
            : config.agent;
    }

    // --- module state construction ---

    /// @dev A node operator with one bonded, deposited key. Curated modules first need the
    ///      MetaRegistry setup of `_prepareCuratedOperator`.
    function _createDepositedOperator(IBaseModule module)
        internal
        returns (uint256 nodeOperatorId)
    {
        _resumeModule(module);
        _grantRole(address(module), CREATE_NODE_OPERATOR_ROLE, address(this));

        ++_operatorsCreated;
        address operator =
            makeAddr(string.concat("scenarioOperator", vm.toString(_operatorsCreated)));
        nodeOperatorId = module.createNodeOperator(
            operator, NodeOperatorManagementProperties(operator, operator, false), address(0)
        );

        _prepareCuratedOperator(module, nodeOperatorId);

        IAccounting accounting = IAccounting(module.ACCOUNTING());
        uint256 bond = accounting.getBondAmountByKeysCount(
            KEYS_PER_OPERATOR, accounting.getBondCurveId(nodeOperatorId)
        );
        (bytes memory keys, bytes memory signatures) = _keysSignatures(KEYS_PER_OPERATOR);

        vm.deal(operator, bond);

        vm.prank(operator);
        module.addValidatorKeysETH{value: bond}(
            operator, nodeOperatorId, KEYS_PER_OPERATOR, keys, signatures
        );

        _depositDepositableKeys(module);
    }

    /// @dev No-op for CSM. Curated variants override it with `_makeCuratedOperatorDepositable`.
    function _prepareCuratedOperator(IBaseModule module, uint256 nodeOperatorId) internal virtual {}

    /// @dev Put a curated operator in a MetaRegistry group with a non-zero bond-curve weight so it
    ///      is depositable
    function _makeCuratedOperatorDepositable(IBaseModule module, uint256 nodeOperatorId) internal {
        IMetaRegistry metaRegistry = IMetaRegistry(module.META_REGISTRY());
        _grantRole(address(metaRegistry), MANAGE_OPERATOR_GROUPS_ROLE, address(this));
        _grantRole(address(metaRegistry), SET_BOND_CURVE_WEIGHT_ROLE, address(this));

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
        subNodeOperators[0] =
            IMetaRegistry.SubNodeOperator({nodeOperatorId: nodeOperatorId, share: FULL_SHARE});
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
        return IMetaRegistry.ExternalOperator({
            data: abi.encodePacked(EXT_OPERATOR_TYPE_NOR, uint8(moduleId), nodeOperatorId)
        });
    }

    function _resumeModule(IBaseModule module) private {
        if (!module.isPaused()) {
            return;
        }

        _grantRole(address(module), RESUME_ROLE, address(this));
        module.resume();
    }

    /// @dev Mark every depositable key as deposited, impersonating the staking router, so freshly
    ///      added keys count toward the deposited total
    function _depositDepositableKeys(IBaseModule module) private {
        (,, uint256 depositable) = module.getStakingModuleSummary();
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
            signatures = bytes.concat(signatures, new bytes(SIGNATURE_LENGTH - index.length), index);
        }
    }

    function _equals(string memory a, string memory b) private pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
