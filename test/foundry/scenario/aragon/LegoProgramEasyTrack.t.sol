// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {
    IAgent,
    IFinance,
    ILido,
    ILidoLocator,
    IMiniMeToken
} from "test/foundry/interfaces/External.sol";

/// @notice A fresh Easy Track over the live Aragon apps with `TopUpLegoProgram` registered, the
///         DAO vote granting the executor `CREATE_PAYMENTS_ROLE` on Finance, and one motion
///         paying the LEGO program LDO, stETH and ETH from the Agent. Unlike the reward programs
///         deployment, the test stays Easy Track's admin.
contract LegoProgramEasyTrackTest is EasyTrackScenarioBase {
    uint256 private constant LDO_AMOUNT = 1e18;
    uint256 private constant STETH_AMOUNT = 2e18;
    uint256 private constant ETH_AMOUNT = 3e18;

    /// @dev What the deployer stakes to fund the Agent's stETH
    uint256 private constant STAKE_AMOUNT = 2.1 ether;

    /// @dev python: brownie.chain.sleep(48 * 60 * 60 + 100), the motion duration hardcoded
    uint256 private constant MOTION_WAIT = 48 hours + 100;

    /// @dev stETH share rounding on the transfer
    uint256 private constant STETH_TOLERANCE = 10;

    address internal legoProgram = makeAddr("legoProgram");
    address internal topUpLegoProgram;

    IFinance internal finance;
    IAgent internal agent;
    IMiniMeToken internal ldo;
    ILido internal steth;

    function setUp() public {
        _forkAndInitialize();

        finance = IFinance(config.finance);
        agent = IAgent(config.agent);
        ldo = IMiniMeToken(easyTrack.governanceToken());
        steth = ILido(ILidoLocator(config.locator).lido());
        creator = makeAddr("trustedAddress");

        vm.label(address(finance), "Finance");
        vm.label(address(ldo), "LDO");
        vm.label(address(steth), "stETH");

        _deployEasyTrack(address(this));

        topUpLegoProgram =
            _deployArtifact("TopUpLegoProgram", abi.encode(creator, finance, legoProgram));
        easyTrack.addEVMScriptFactory(
            topUpLegoProgram, abi.encodePacked(finance, IFinance.newImmediatePayment.selector)
        );

        address[] memory factories = easyTrack.getEVMScriptFactories();
        assertEq(factories.length, 1, "setup: factories");
        assertEq(factories[0], topUpLegoProgram, "setup: factory");

        // The vote "Grant permissions to EVMScriptExecutor to make payments"
        _grantPermission(evmScriptExecutor, address(finance), finance.CREATE_PAYMENTS_ROLE());
    }

    // python: test_lego_easy_track_happy_path
    function testFork_TopsUpLegoProgram() external {
        address[] memory tokens = new address[](3);
        tokens[0] = address(ldo);
        tokens[1] = address(steth);
        tokens[2] = address(0);
        uint256[] memory amounts = new uint256[](3);
        amounts[0] = LDO_AMOUNT;
        amounts[1] = STETH_AMOUNT;
        amounts[2] = ETH_AMOUNT;
        bytes memory callData = abi.encode(tokens, amounts);

        uint256 motionId = _createMotion(topUpLegoProgram, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        vm.warp(vm.getBlockTimestamp() + MOTION_WAIT);

        _fundAgent();

        assertGe(agent.balance(address(ldo)), LDO_AMOUNT, "Agent LDO");
        assertGe(agent.balance(address(steth)), STETH_AMOUNT, "Agent stETH");
        assertGe(agent.balance(address(0)), ETH_AMOUNT, "Agent ETH");
        assertEq(ldo.balanceOf(legoProgram), 0, "LDO before enactment");
        assertEq(steth.balanceOf(legoProgram), 0, "stETH before enactment");
        uint256 ethBefore = legoProgram.balance;

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
        assertEq(ldo.balanceOf(legoProgram), LDO_AMOUNT, "LDO after enactment");
        assertApproxEqAbs(
            steth.balanceOf(legoProgram), STETH_AMOUNT, STETH_TOLERANCE, "stETH after enactment"
        );
        assertEq(legoProgram.balance - ethBefore, ETH_AMOUNT, "ETH after enactment");
    }

    /// @dev python: the Agent deposits LDO it already holds into itself, the deployer stakes for
    ///      stETH and deposits it, then deposits ETH
    function _fundAgent() private {
        vm.startPrank(address(agent));
        ldo.approve(address(agent), LDO_AMOUNT);
        agent.deposit(address(ldo), LDO_AMOUNT);
        vm.stopPrank();

        vm.deal(address(this), STAKE_AMOUNT + ETH_AMOUNT);

        steth.submit{value: STAKE_AMOUNT}(address(0));
        steth.approve(address(agent), STAKE_AMOUNT);
        agent.deposit(address(steth), STETH_AMOUNT);
        agent.deposit{value: ETH_AMOUNT}(address(0), ETH_AMOUNT);
    }
}
