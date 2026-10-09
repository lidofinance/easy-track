// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IEVMScriptExecutor, IRewardProgramsRegistry} from "test/foundry/interfaces/EasyTrack.sol";
import {
    IFinance,
    ILidoLocator,
    INodeOperatorsRegistry,
    IStakingRouter
} from "test/foundry/interfaces/External.sol";
import {
    IIncreaseNodeOperatorStakingLimit,
    IRewardProgramsFactory,
    ITopUpLegoProgram,
    ITopUpRewardPrograms
} from "test/foundry/interfaces/Factories.sol";

/// @notice The wiring `scripts/deploy.py` leaves behind, replayed from the `contracts` profile
///         artifacts over the live Aragon apps and the curated registry: Easy Track with the
///         initial settings and its roles on Voting, the executor, the five factories registered
///         with their permissions and the reward programs registry with its roles. The test reads
///         the deployment back.
contract DeployScriptTest is EasyTrackScenarioBase {
    /// @dev `utils/constants.py`, the settings the deploy script starts Easy Track with
    uint256 private constant INITIAL_MOTION_DURATION = 72 hours;
    uint256 private constant INITIAL_MOTIONS_COUNT_LIMIT = 12;
    uint256 private constant INITIAL_OBJECTIONS_THRESHOLD = 50;

    uint256 private constant CURATED_MODULE_ID = 1;

    address internal legoProgramVault = makeAddr("legoProgramVault");
    address internal legoCommitteeMultisig = makeAddr("legoCommitteeMultisig");
    address internal rewardProgramsMultisig = makeAddr("rewardProgramsMultisig");
    address internal pauseAddress = makeAddr("pauseAddress");

    address internal voting;
    address internal ldo;
    address internal callsScript;
    IFinance internal finance;
    INodeOperatorsRegistry internal registry;

    address internal increaseNodeOperatorStakingLimit;
    address internal topUpLegoProgram;
    IRewardProgramsRegistry internal rewardProgramsRegistry;
    address internal addRewardProgram;
    address internal removeRewardProgram;
    address internal topUpRewardPrograms;

    function setUp() public {
        _forkAndInitialize();

        voting = _voting();
        ldo = easyTrack.governanceToken();
        callsScript = IEVMScriptExecutor(evmScriptExecutor).callsScript();
        finance = IFinance(config.finance);
        IStakingRouter stakingRouter = IStakingRouter(ILidoLocator(config.locator).stakingRouter());
        registry = INodeOperatorsRegistry(
            stakingRouter.getStakingModule(CURATED_MODULE_ID).stakingModuleAddress
        );

        vm.label(voting, "Voting");
        vm.label(ldo, "LDO");
        vm.label(callsScript, "CallsScript");
        vm.label(address(finance), "Finance");
        vm.label(address(registry), "NodeOperatorsRegistry");

        _deployEasyTracks();
    }

    // python: test_deploy_script
    function testFork_DeploysEasyTrackWired() external view {
        _assertEasyTrackSettings();
        _assertEasyTrackRoles();
        _assertExecutor();
        _assertFactories();
        _assertRegistryRoles();
        _assertFactoryPermissions();
    }

    /// @dev `deploy_easy_tracks`, with the test as the deployer
    function _deployEasyTracks() private {
        _deployEasyTrack(
            address(this),
            INITIAL_MOTION_DURATION,
            INITIAL_MOTIONS_COUNT_LIMIT,
            INITIAL_OBJECTIONS_THRESHOLD
        );

        increaseNodeOperatorStakingLimit =
            _deployArtifact("IncreaseNodeOperatorStakingLimit", abi.encode(registry));
        topUpLegoProgram = _deployArtifact(
            "TopUpLegoProgram", abi.encode(legoCommitteeMultisig, finance, legoProgramVault)
        );

        address[] memory roleHolders = new address[](2);
        roleHolders[0] = voting;
        roleHolders[1] = evmScriptExecutor;
        rewardProgramsRegistry = IRewardProgramsRegistry(
            _deployArtifact("RewardProgramsRegistry", abi.encode(voting, roleHolders, roleHolders))
        );

        addRewardProgram = _deployArtifact(
            "AddRewardProgram", abi.encode(rewardProgramsMultisig, rewardProgramsRegistry)
        );
        removeRewardProgram = _deployArtifact(
            "RemoveRewardProgram", abi.encode(rewardProgramsMultisig, rewardProgramsRegistry)
        );
        topUpRewardPrograms = _deployArtifact(
            "TopUpRewardPrograms",
            abi.encode(rewardProgramsMultisig, rewardProgramsRegistry, finance, ldo)
        );

        _addEVMScriptFactories();
        _grantRoles();
        _handAdminToVoting();
    }

    /// @dev `add_evm_script_factories`, in its order
    function _addEVMScriptFactories() private {
        easyTrack.addEVMScriptFactory(
            increaseNodeOperatorStakingLimit, _setNodeOperatorStakingLimitPermission()
        );
        easyTrack.addEVMScriptFactory(topUpLegoProgram, _newImmediatePaymentPermission());
        easyTrack.addEVMScriptFactory(topUpRewardPrograms, _newImmediatePaymentPermission());
        easyTrack.addEVMScriptFactory(addRewardProgram, _addRewardProgramPermission());
        easyTrack.addEVMScriptFactory(removeRewardProgram, _removeRewardProgramPermission());
    }

    /// @dev `grant_roles`: Voting may pause, unpause and cancel, the pause address may pause
    function _grantRoles() private {
        easyTrack.grantRole(easyTrack.PAUSE_ROLE(), voting);
        easyTrack.grantRole(easyTrack.UNPAUSE_ROLE(), voting);
        easyTrack.grantRole(easyTrack.CANCEL_ROLE(), voting);
        easyTrack.grantRole(easyTrack.PAUSE_ROLE(), pauseAddress);
    }

    function _assertEasyTrackSettings() private view {
        assertEq(easyTrack.governanceToken(), ldo, "governanceToken");
        assertEq(easyTrack.evmScriptExecutor(), evmScriptExecutor, "evmScriptExecutor");
        assertEq(easyTrack.motionDuration(), INITIAL_MOTION_DURATION, "motionDuration");
        assertEq(easyTrack.motionsCountLimit(), INITIAL_MOTIONS_COUNT_LIMIT, "motionsCountLimit");
        assertEq(
            easyTrack.objectionsThreshold(), INITIAL_OBJECTIONS_THRESHOLD, "objectionsThreshold"
        );
    }

    function _assertEasyTrackRoles() private view {
        bytes32 adminRole = easyTrack.DEFAULT_ADMIN_ROLE();

        assertTrue(easyTrack.hasRole(easyTrack.PAUSE_ROLE(), voting), "Voting PAUSE_ROLE");
        assertTrue(easyTrack.hasRole(easyTrack.CANCEL_ROLE(), voting), "Voting CANCEL_ROLE");
        assertTrue(easyTrack.hasRole(easyTrack.UNPAUSE_ROLE(), voting), "Voting UNPAUSE_ROLE");
        assertTrue(easyTrack.hasRole(adminRole, voting), "Voting DEFAULT_ADMIN_ROLE");
        assertFalse(easyTrack.hasRole(adminRole, address(this)), "deployer DEFAULT_ADMIN_ROLE");
    }

    function _assertExecutor() private view {
        IEVMScriptExecutor executor = IEVMScriptExecutor(evmScriptExecutor);

        assertEq(executor.callsScript(), callsScript, "callsScript");
        assertEq(executor.easyTrack(), address(easyTrack), "easyTrack");
        assertEq(executor.owner(), voting, "executor owner");
    }

    function _assertFactories() private view {
        assertEq(
            IIncreaseNodeOperatorStakingLimit(increaseNodeOperatorStakingLimit)
                .nodeOperatorsRegistry(),
            address(registry),
            "nodeOperatorsRegistry"
        );

        ITopUpLegoProgram lego = ITopUpLegoProgram(topUpLegoProgram);
        assertEq(lego.finance(), address(finance), "LEGO finance");
        assertEq(lego.legoProgram(), legoProgramVault, "legoProgram");
        assertEq(lego.trustedCaller(), legoCommitteeMultisig, "LEGO trustedCaller");

        IRewardProgramsFactory add = IRewardProgramsFactory(addRewardProgram);
        assertEq(add.trustedCaller(), rewardProgramsMultisig, "add trustedCaller");
        assertEq(add.rewardProgramsRegistry(), address(rewardProgramsRegistry), "add registry");

        IRewardProgramsFactory remove = IRewardProgramsFactory(removeRewardProgram);
        assertEq(remove.trustedCaller(), rewardProgramsMultisig, "remove trustedCaller");
        assertEq(
            remove.rewardProgramsRegistry(), address(rewardProgramsRegistry), "remove registry"
        );

        ITopUpRewardPrograms topUp = ITopUpRewardPrograms(topUpRewardPrograms);
        assertEq(topUp.trustedCaller(), rewardProgramsMultisig, "top up trustedCaller");
        assertEq(topUp.finance(), address(finance), "top up finance");
        assertEq(topUp.rewardToken(), ldo, "rewardToken");
        assertEq(topUp.rewardProgramsRegistry(), address(rewardProgramsRegistry), "top up registry");
    }

    /// @dev Voting administers the registry, Voting and the executor add and remove
    function _assertRegistryRoles() private view {
        bytes32 addRole = rewardProgramsRegistry.ADD_REWARD_PROGRAM_ROLE();
        bytes32 removeRole = rewardProgramsRegistry.REMOVE_REWARD_PROGRAM_ROLE();

        assertTrue(
            rewardProgramsRegistry.hasRole(rewardProgramsRegistry.DEFAULT_ADMIN_ROLE(), voting),
            "Voting DEFAULT_ADMIN_ROLE on registry"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, evmScriptExecutor),
            "executor ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, voting), "Voting ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, evmScriptExecutor),
            "executor REMOVE_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, voting), "Voting REMOVE_REWARD_PROGRAM_ROLE"
        );
    }

    function _assertFactoryPermissions() private view {
        assertEq(
            easyTrack.evmScriptFactoryPermissions(increaseNodeOperatorStakingLimit),
            _setNodeOperatorStakingLimitPermission(),
            "staking limit permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(topUpLegoProgram),
            _newImmediatePaymentPermission(),
            "LEGO permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(addRewardProgram),
            _addRewardProgramPermission(),
            "add permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(removeRewardProgram),
            _removeRewardProgramPermission(),
            "remove permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(topUpRewardPrograms),
            _newImmediatePaymentPermission(),
            "top up permissions"
        );
    }

    // --- `create_permission`: the target and the selector the script computes from its ABI ---

    function _setNodeOperatorStakingLimitPermission() private view returns (bytes memory) {
        return
            abi.encodePacked(registry, INodeOperatorsRegistry.setNodeOperatorStakingLimit.selector);
    }

    function _newImmediatePaymentPermission() private view returns (bytes memory) {
        return abi.encodePacked(finance, IFinance.newImmediatePayment.selector);
    }

    function _addRewardProgramPermission() private view returns (bytes memory) {
        return
            abi.encodePacked(
                rewardProgramsRegistry, IRewardProgramsRegistry.addRewardProgram.selector
            );
    }

    function _removeRewardProgramPermission() private view returns (bytes memory) {
        return abi.encodePacked(
            rewardProgramsRegistry, IRewardProgramsRegistry.removeRewardProgram.selector
        );
    }
}
