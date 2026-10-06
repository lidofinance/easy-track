// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    UpdateGroupsShareLimitInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/UpdateGroupsShareLimitInOperatorGrid.sol";
import {IOperatorGrid} from "contracts/interfaces/IOperatorGrid.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract UpdateGroupsShareLimitInOperatorGridTest is Test {
    /// @dev The maxShareLimit constructor argument
    uint256 internal constant MAX_SHARE_LIMIT = 10000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: operator1 and operator2, accounts[5] and accounts[6]
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

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(updateGroupsShareLimitInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(updateGroupsShareLimitInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_node_operators_array
    function test_RevertWhen_NodeOperatorsAreEmpty() external {
        address[] memory nodeOperators = new address[](0);
        uint256[] memory shareLimits = new uint256[](0);

        vm.expectRevert("EMPTY_NODE_OPERATORS");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits)
        );
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(stranger), _shareLimits(1000, 2000))
        );
    }

    // python: test_zero_node_operator
    function test_RevertWhen_NodeOperatorIsZero() external {
        vm.expectRevert("ZERO_NODE_OPERATOR");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(address(0), stranger), _shareLimits(1000, 2000))
        );
    }

    // python: test_group_not_exists
    function test_RevertWhen_GroupDoesNotExist() external {
        vm.expectRevert("GROUP_NOT_EXISTS");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(stranger, nodeOperator), _shareLimits(1000, 2000))
        );
    }

    // python: test_share_limit_too_high
    function test_RevertWhen_ShareLimitIsTooHigh() external {
        _givenGroupRegistered(nodeOperator, 5000);

        uint256 shareLimit = updateGroupsShareLimitInOperatorGrid.maxShareLimit() + 1;

        vm.expectRevert("SHARE_LIMIT_TOO_HIGH");
        updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(_operators(nodeOperator), _shareLimits(shareLimit))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        _givenGroupRegistered(nodeOperator, 1000);
        _givenGroupRegistered(anotherNodeOperator, 1500);

        address[] memory nodeOperators = _operators(nodeOperator, anotherNodeOperator);
        uint256[] memory shareLimits = _shareLimits(2000, 3000);

        bytes memory evmScript = updateGroupsShareLimitInOperatorGrid.createEVMScript(
            owner, abi.encode(nodeOperators, shareLimits)
        );

        assertEq(evmScript, _updateGroupShareLimitsScript(nodeOperators, shareLimits), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory nodeOperators = _operators(nodeOperator, anotherNodeOperator);
        uint256[] memory shareLimits = _shareLimits(2000, 3000);

        (address[] memory decodedNodeOperators, uint256[] memory decodedShareLimits) = updateGroupsShareLimitInOperatorGrid.decodeEVMScriptCallData(
            abi.encode(nodeOperators, shareLimits)
        );

        assertEq(decodedNodeOperators, nodeOperators, "nodeOperators");
        assertEq(decodedShareLimits, shareLimits, "shareLimits");
    }

    // python: test_cannot_update_share_limit_with_wrong_calldata_length
    function test_RevertWhen_CallDataLengthIsWrong() external {
        vm.expectRevert(bytes(""));
        updateGroupsShareLimitInOperatorGrid.createEVMScript(owner, hex"00");
    }

    /// @dev python: operatorGrid.registerGroup(operator, shareLimit, {"from": owner})
    function _givenGroupRegistered(address operator, uint256 shareLimit) private {
        vm.prank(owner);
        operatorGrid.registerGroup(operator, shareLimit);
    }

    function _operators(address operator) private pure returns (address[] memory nodeOperators) {
        nodeOperators = new address[](1);
        nodeOperators[0] = operator;
    }

    function _operators(address first, address second)
        private
        pure
        returns (address[] memory nodeOperators)
    {
        nodeOperators = new address[](2);
        nodeOperators[0] = first;
        nodeOperators[1] = second;
    }

    function _shareLimits(uint256 shareLimit) private pure returns (uint256[] memory shareLimits) {
        shareLimits = new uint256[](1);
        shareLimits[0] = shareLimit;
    }

    function _shareLimits(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory shareLimits)
    {
        shareLimits = new uint256[](2);
        shareLimits[0] = first;
        shareLimits[1] = second;
    }

    /// @dev python: encode_call_script of one updateGroupShareLimit per operator, every call to
    /// the operator grid
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
