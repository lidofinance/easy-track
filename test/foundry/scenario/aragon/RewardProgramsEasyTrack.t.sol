// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    IEasyTrack,
    IEVMScriptExecutor,
    IRewardProgramsRegistry
} from "test/foundry/interfaces/EasyTrack.sol";
import {IFinance, IMiniMeToken} from "test/foundry/interfaces/External.sol";

/// @notice A fresh Easy Track over the live Aragon apps, the way the reward programs went live:
///         Easy Track and its executor handed to the DAO Voting, the registry and the three
///         factories registered, and the DAO vote granting the executor `CREATE_PAYMENTS_ROLE` on
///         Finance. The base helpers drive this deployment, not the deployed Easy Track.
contract RewardProgramsEasyTrackTest is EasyTrackScenarioBase {
    uint256 private constant MIN_MOTION_DURATION = 48 hours;
    uint256 private constant MAX_MOTIONS_LIMIT = 24;
    uint256 private constant DEFAULT_OBJECTIONS_THRESHOLD = 50;

    string private constant REWARD_PROGRAM_TITLE = "Our Reward Program";
    uint256 private constant TOP_UP_AMOUNT = 5e18;

    address internal rewardProgram = makeAddr("rewardProgram");

    IRewardProgramsRegistry internal rewardProgramsRegistry;
    address internal addRewardProgram;
    address internal topUpRewardPrograms;
    address internal removeRewardProgram;

    IFinance internal finance;
    IMiniMeToken internal ldo;
    address internal voting;

    function setUp() public {
        _forkAndInitialize();

        voting = _voting();
        finance = IFinance(config.finance);
        ldo = IMiniMeToken(easyTrack.governanceToken());
        address callsScript = IEVMScriptExecutor(evmScriptExecutor).callsScript();
        creator = makeAddr("trustedCaller");

        vm.label(address(finance), "Finance");
        vm.label(address(ldo), "LDO");

        _deployEasyTrack(callsScript);
        _deployFactories();
        _handAdminToVoting();

        // The vote "Grant permissions to EVMScriptExecutor to make payments"
        _grantPermission(evmScriptExecutor, address(finance), finance.CREATE_PAYMENTS_ROLE());
    }

    // python: test_reward_programs_easy_track
    function testFork_AddsTopsUpAndRemovesRewardProgram() external {
        bytes memory addCallData = abi.encode(rewardProgram, REWARD_PROGRAM_TITLE);
        uint256 motionId = _createMotion(addRewardProgram, creator, addCallData);

        assertEq(easyTrack.getMotions().length, 1, "motions after add created");

        _enactMotion(motionId, addCallData);

        assertEq(easyTrack.getMotions().length, 0, "motions after add enacted");
        address[] memory rewardPrograms = rewardProgramsRegistry.getRewardPrograms();
        assertEq(rewardPrograms.length, 1, "reward programs after add");
        assertEq(rewardPrograms[0], rewardProgram, "reward program");

        bytes memory topUpCallData = abi.encode(_single(rewardProgram), _single(TOP_UP_AMOUNT));
        motionId = _createMotion(topUpRewardPrograms, creator, topUpCallData);

        assertEq(easyTrack.getMotions().length, 1, "motions after top up created");
        assertEq(ldo.balanceOf(rewardProgram), 0, "LDO before top up");

        _enactMotion(motionId, topUpCallData);

        assertEq(easyTrack.getMotions().length, 0, "motions after top up enacted");
        assertEq(ldo.balanceOf(rewardProgram), TOP_UP_AMOUNT, "LDO after top up");

        bytes memory removeCallData = abi.encode(rewardProgram);
        motionId = _createMotion(removeRewardProgram, creator, removeCallData);

        assertEq(easyTrack.getMotions().length, 1, "motions after remove created");

        _enactMotion(motionId, removeCallData);

        assertEq(easyTrack.getMotions().length, 0, "motions after remove enacted");
        assertEq(
            rewardProgramsRegistry.getRewardPrograms().length, 0, "reward programs after remove"
        );
    }

    /// @dev Easy Track with the test as admin and an executor owned by Voting, which the base
    ///      helpers drive from here on instead of the deployed pair
    function _deployEasyTrack(address callsScript) private {
        easyTrack = IEasyTrack(
            _deployArtifact(
                "EasyTrack",
                abi.encode(
                    ldo,
                    address(this),
                    MIN_MOTION_DURATION,
                    MAX_MOTIONS_LIMIT,
                    DEFAULT_OBJECTIONS_THRESHOLD
                )
            )
        );
        evmScriptExecutor = _deployArtifact("EVMScriptExecutor", abi.encode(callsScript, easyTrack));

        IEVMScriptExecutor(evmScriptExecutor).transferOwnership(voting);

        assertEq(IEVMScriptExecutor(evmScriptExecutor).owner(), voting, "setup: executor owner");

        easyTrack.setEVMScriptExecutor(evmScriptExecutor);
    }

    /// @dev The registry, with Voting and the executor in both of its roles, and the three
    ///      factories registered with the permission each one's script needs
    function _deployFactories() private {
        address[] memory roleHolders = new address[](2);
        roleHolders[0] = voting;
        roleHolders[1] = evmScriptExecutor;
        rewardProgramsRegistry = IRewardProgramsRegistry(
            _deployArtifact("RewardProgramsRegistry", abi.encode(voting, roleHolders, roleHolders))
        );

        topUpRewardPrograms = _deployArtifact(
            "TopUpRewardPrograms", abi.encode(creator, rewardProgramsRegistry, finance, ldo)
        );
        easyTrack.addEVMScriptFactory(
            topUpRewardPrograms, abi.encodePacked(finance, IFinance.newImmediatePayment.selector)
        );

        addRewardProgram =
            _deployArtifact("AddRewardProgram", abi.encode(creator, rewardProgramsRegistry));
        easyTrack.addEVMScriptFactory(
            addRewardProgram,
            abi.encodePacked(
                rewardProgramsRegistry, IRewardProgramsRegistry.addRewardProgram.selector
            )
        );

        removeRewardProgram =
            _deployArtifact("RemoveRewardProgram", abi.encode(creator, rewardProgramsRegistry));
        easyTrack.addEVMScriptFactory(
            removeRewardProgram,
            abi.encodePacked(
                rewardProgramsRegistry, IRewardProgramsRegistry.removeRewardProgram.selector
            )
        );
    }

    /// @dev Voting becomes the admin and the deployer stops being one
    function _handAdminToVoting() private {
        bytes32 adminRole = easyTrack.DEFAULT_ADMIN_ROLE();

        easyTrack.grantRole(adminRole, voting);

        assertTrue(easyTrack.hasRole(adminRole, voting), "setup: Voting is admin");

        easyTrack.revokeRole(adminRole, address(this));

        assertFalse(easyTrack.hasRole(adminRole, address(this)), "setup: deployer is not admin");
    }

    function _single(address value) private pure returns (address[] memory values) {
        values = new address[](1);
        values[0] = value;
    }

    function _single(uint256 value) private pure returns (uint256[] memory values) {
        values = new uint256[](1);
        values[0] = value;
    }
}
