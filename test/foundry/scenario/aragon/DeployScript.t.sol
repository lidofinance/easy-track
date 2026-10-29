// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {DeployEasyTrack} from "script/DeployEasyTrack.s.sol";
import {Lido} from "script/helpers/Lido.sol";
import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {IEVMScriptExecutor, IRewardProgramsRegistry} from "test/foundry/interfaces/EasyTrack.sol";
import {IFinance, INodeOperatorsRegistry} from "test/foundry/interfaces/External.sol";
import {
    IIncreaseNodeOperatorStakingLimit,
    IRewardProgramsFactory,
    ITopUpLegoProgram,
    ITopUpRewardPrograms
} from "test/foundry/interfaces/Factories.sol";

/// @notice `script/DeployEasyTrack.s.sol` run on the fork over the live Aragon apps and the
///         curated registry, with the script contract as the deployer: Easy Track with the
///         initial settings and its roles on Voting, the executor, the five factories registered
///         with their permissions and the reward programs registry with its roles. The test reads
///         the deployment back.
contract DeployScriptTest is EasyTrackScenarioBase {
    DeployEasyTrack.Params internal params = DeployEasyTrack.Params({
        legoProgramVault: makeAddr("legoProgramVault"),
        legoCommitteeMultisig: makeAddr("legoCommitteeMultisig"),
        rewardProgramsMultisig: makeAddr("rewardProgramsMultisig"),
        pauseAddress: makeAddr("pauseAddress")
    });

    Lido.DAO internal dao;
    INodeOperatorsRegistry internal registry;
    DeployEasyTrack internal script;
    DeployEasyTrack.Deployment internal deployment;

    function setUp() public {
        _forkAndInitialize();

        dao = Lido.dao();
        registry = INodeOperatorsRegistry(Lido.curatedRegistry(dao));
        script = new DeployEasyTrack();

        vm.label(dao.voting, "Voting");
        vm.label(dao.ldo, "LDO");
        vm.label(dao.callsScript, "CallsScript");
        vm.label(dao.finance, "Finance");
        vm.label(address(registry), "NodeOperatorsRegistry");
        vm.label(address(script), "DeployEasyTrack");

        deployment = script.deploy(address(script), params);
        easyTrack = deployment.easyTrack;
        evmScriptExecutor = deployment.evmScriptExecutor;
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

    function _assertEasyTrackSettings() private view {
        assertEq(easyTrack.governanceToken(), dao.ldo, "governanceToken");
        assertEq(easyTrack.evmScriptExecutor(), evmScriptExecutor, "evmScriptExecutor");
        assertEq(easyTrack.motionDuration(), script.INITIAL_MOTION_DURATION(), "motionDuration");
        assertEq(
            easyTrack.motionsCountLimit(), script.INITIAL_MOTIONS_COUNT_LIMIT(), "motionsCountLimit"
        );
        assertEq(
            easyTrack.objectionsThreshold(),
            script.INITIAL_OBJECTIONS_THRESHOLD(),
            "objectionsThreshold"
        );
    }

    function _assertEasyTrackRoles() private view {
        bytes32 adminRole = easyTrack.DEFAULT_ADMIN_ROLE();

        assertTrue(easyTrack.hasRole(easyTrack.PAUSE_ROLE(), dao.voting), "Voting PAUSE_ROLE");
        assertTrue(easyTrack.hasRole(easyTrack.CANCEL_ROLE(), dao.voting), "Voting CANCEL_ROLE");
        assertTrue(easyTrack.hasRole(easyTrack.UNPAUSE_ROLE(), dao.voting), "Voting UNPAUSE_ROLE");
        assertTrue(
            easyTrack.hasRole(easyTrack.PAUSE_ROLE(), params.pauseAddress),
            "pauseAddress PAUSE_ROLE"
        );
        assertTrue(easyTrack.hasRole(adminRole, dao.voting), "Voting DEFAULT_ADMIN_ROLE");
        assertFalse(easyTrack.hasRole(adminRole, address(script)), "deployer DEFAULT_ADMIN_ROLE");
    }

    function _assertExecutor() private view {
        IEVMScriptExecutor executor = IEVMScriptExecutor(evmScriptExecutor);

        assertEq(executor.callsScript(), dao.callsScript, "callsScript");
        assertEq(executor.easyTrack(), address(easyTrack), "easyTrack");
        assertEq(executor.owner(), dao.voting, "executor owner");
    }

    function _assertFactories() private view {
        assertEq(
            IIncreaseNodeOperatorStakingLimit(deployment.increaseNodeOperatorStakingLimit)
                .nodeOperatorsRegistry(),
            address(registry),
            "nodeOperatorsRegistry"
        );

        ITopUpLegoProgram lego = ITopUpLegoProgram(deployment.topUpLegoProgram);
        assertEq(lego.finance(), dao.finance, "LEGO finance");
        assertEq(lego.legoProgram(), params.legoProgramVault, "legoProgram");
        assertEq(lego.trustedCaller(), params.legoCommitteeMultisig, "LEGO trustedCaller");

        address rewardProgramsRegistry = address(deployment.rewardProgramsRegistry);

        IRewardProgramsFactory add = IRewardProgramsFactory(deployment.addRewardProgram);
        assertEq(add.trustedCaller(), params.rewardProgramsMultisig, "add trustedCaller");
        assertEq(add.rewardProgramsRegistry(), rewardProgramsRegistry, "add registry");

        IRewardProgramsFactory remove = IRewardProgramsFactory(deployment.removeRewardProgram);
        assertEq(remove.trustedCaller(), params.rewardProgramsMultisig, "remove trustedCaller");
        assertEq(remove.rewardProgramsRegistry(), rewardProgramsRegistry, "remove registry");

        ITopUpRewardPrograms topUp = ITopUpRewardPrograms(deployment.topUpRewardPrograms);
        assertEq(topUp.trustedCaller(), params.rewardProgramsMultisig, "top up trustedCaller");
        assertEq(topUp.finance(), dao.finance, "top up finance");
        assertEq(topUp.rewardToken(), dao.ldo, "rewardToken");
        assertEq(topUp.rewardProgramsRegistry(), rewardProgramsRegistry, "top up registry");
    }

    /// @dev Voting administers the registry, Voting and the executor add and remove
    function _assertRegistryRoles() private view {
        IRewardProgramsRegistry rewardProgramsRegistry = deployment.rewardProgramsRegistry;
        bytes32 addRole = rewardProgramsRegistry.ADD_REWARD_PROGRAM_ROLE();
        bytes32 removeRole = rewardProgramsRegistry.REMOVE_REWARD_PROGRAM_ROLE();

        assertTrue(
            rewardProgramsRegistry.hasRole(rewardProgramsRegistry.DEFAULT_ADMIN_ROLE(), dao.voting),
            "Voting DEFAULT_ADMIN_ROLE on registry"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, evmScriptExecutor),
            "executor ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(addRole, dao.voting), "Voting ADD_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, evmScriptExecutor),
            "executor REMOVE_REWARD_PROGRAM_ROLE"
        );
        assertTrue(
            rewardProgramsRegistry.hasRole(removeRole, dao.voting),
            "Voting REMOVE_REWARD_PROGRAM_ROLE"
        );
    }

    function _assertFactoryPermissions() private view {
        assertEq(
            easyTrack.evmScriptFactoryPermissions(deployment.increaseNodeOperatorStakingLimit),
            _setNodeOperatorStakingLimitPermission(),
            "staking limit permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(deployment.topUpLegoProgram),
            _newImmediatePaymentPermission(),
            "LEGO permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(deployment.addRewardProgram),
            _addRewardProgramPermission(),
            "add permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(deployment.removeRewardProgram),
            _removeRewardProgramPermission(),
            "remove permissions"
        );
        assertEq(
            easyTrack.evmScriptFactoryPermissions(deployment.topUpRewardPrograms),
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
        return abi.encodePacked(dao.finance, IFinance.newImmediatePayment.selector);
    }

    function _addRewardProgramPermission() private view returns (bytes memory) {
        return abi.encodePacked(
            deployment.rewardProgramsRegistry, IRewardProgramsRegistry.addRewardProgram.selector
        );
    }

    function _removeRewardProgramPermission() private view returns (bytes memory) {
        return abi.encodePacked(
            deployment.rewardProgramsRegistry, IRewardProgramsRegistry.removeRewardProgram.selector
        );
    }
}
