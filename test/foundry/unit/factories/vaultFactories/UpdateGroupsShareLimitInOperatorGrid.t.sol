// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    UpdateGroupsShareLimitInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/UpdateGroupsShareLimitInOperatorGrid.sol";
import {IOperatorGrid} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {Arrays} from "test/foundry/unit/helpers/Arrays.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract UpdateGroupsShareLimitInOperatorGridTest is Test {
    /// @dev The maxShareLimit constructor argument
    uint256 internal constant MAX_SHARE_LIMIT = 10000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal anotherNodeOperator = makeAddr("anotherNodeOperator");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    UpdateGroupsShareLimitInOperatorGrid internal updateGroupsShareLimitInOperatorGrid;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());

        vm.prank(owner);
        updateGroupsShareLimitInOperatorGrid = new UpdateGroupsShareLimitInOperatorGrid(
            owner, address(lidoLocatorStub), MAX_SHARE_LIMIT
        );

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(
            address(updateGroupsShareLimitInOperatorGrid), "updateGroupsShareLimitInOperatorGrid"
        );
    }

    function test_SetsInitialState() external view {
        assertEq(updateGroupsShareLimitInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(updateGroupsShareLimitInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
    }

    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(stranger, "");
    }

    function test_RevertWhen_NodeOperatorsAreEmpty() external {
        address[] memory nodeOperators = new address[](0);
        uint256[] memory shareLimits = new uint256[](0);

        vm.expectRevert("EMPTY_NODE_OPERATORS");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits)
        );
    }

    function test_RevertWhen_ArrayLengthsMismatch() external {
        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(Arrays.list(stranger), Arrays.list(1000, 2000))
        );
    }

    function test_RevertWhen_NodeOperatorIsZero() external {
        vm.expectRevert("ZERO_NODE_OPERATOR");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(Arrays.list(address(0), stranger), Arrays.list(1000, 2000))
        );
    }

    function test_RevertWhen_GroupDoesNotExist() external {
        vm.expectRevert("GROUP_NOT_EXISTS");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(Arrays.list(stranger, nodeOperator), Arrays.list(1000, 2000))
        );
    }

    function test_RevertWhen_ShareLimitIsTooHigh() external {
        _registerGroup(nodeOperator, 5000);

        uint256 shareLimit = updateGroupsShareLimitInOperatorGrid.maxShareLimit() + 1;

        vm.expectRevert("SHARE_LIMIT_TOO_HIGH");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(Arrays.list(nodeOperator), Arrays.list(shareLimit))
        );
    }

    function test_CreatesEVMScript() external {
        _registerGroup(nodeOperator, 1000);
        _registerGroup(anotherNodeOperator, 1500);

        address[] memory nodeOperators = Arrays.list(nodeOperator, anotherNodeOperator);
        uint256[] memory shareLimits = Arrays.list(2000, 3000);

        bytes memory evmScript = updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits)
        );

        assertEq(evmScript, _updateGroupShareLimitsScript(nodeOperators, shareLimits), "evmScript");
    }

    function test_DecodesEVMScriptCallData() external view {
        address[] memory nodeOperators = Arrays.list(nodeOperator, anotherNodeOperator);
        uint256[] memory shareLimits = Arrays.list(2000, 3000);

        (address[] memory decodedNodeOperators, uint256[] memory decodedShareLimits) = updateGroupsShareLimitInOperatorGrid.decodeEVMScriptCallData(
            abi.encode(nodeOperators, shareLimits)
        );

        assertEq(decodedNodeOperators, nodeOperators, "nodeOperators");
        assertEq(decodedShareLimits, shareLimits, "shareLimits");
    }

    function test_RevertWhen_CallDataLengthIsWrong() external {
        vm.expectRevert(bytes(""));
        updateGroupsShareLimitInOperatorGrid.createEVMScript(owner, hex"00");
    }

    function _registerGroup(address operator, uint256 shareLimit) private {
        vm.prank(owner);
        operatorGrid.registerGroup(operator, shareLimit);
    }

    function _updateGroupShareLimitsScript(
        address[] memory nodeOperators,
        uint256[] memory shareLimits
    ) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](nodeOperators.length);

        for (uint256 i; i < nodeOperators.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IOperatorGrid.updateGroupShareLimit.selector, nodeOperators[i], shareLimits[i]
            );
        }

        return EVMScripts.encodeCallScript(address(operatorGrid), calls);
    }
}
