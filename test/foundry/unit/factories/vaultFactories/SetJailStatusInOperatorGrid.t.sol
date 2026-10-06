// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SetJailStatusInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/SetJailStatusInOperatorGrid.sol";
import {VaultsAdapter} from "contracts/EVMScriptFactories/vaultFactories/VaultsAdapter.sol";
import {IOperatorGrid} from "contracts/interfaces/IOperatorGrid.sol";
import {IVaultHub} from "contracts/interfaces/IVaultHub.sol";
import {IVaultsAdapter} from "contracts/interfaces/IVaultsAdapter.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {StakingVaultStub} from "contracts/test/StakingVaultStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract SetJailStatusInOperatorGridTest is Test {
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: accounts[5] and accounts[6] as node operators
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal anotherNodeOperator = makeAddr("anotherNodeOperator");
    /// @dev python: accounts[5], accounts[6] and accounts[7] as vault addresses
    address internal vault = makeAddr("vault");
    address internal anotherVault = makeAddr("anotherVault");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    IVaultHub internal vaultHub;
    VaultsAdapter internal vaultsAdapter;
    SetJailStatusInOperatorGrid internal setJailStatusInOperatorGrid;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event VaultJailStatusUpdateFailed(address indexed vault, bool isInJail);
    event VaultJailStatusUpdated(address indexed vault, bool isInJail);

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());
        vaultHub = IVaultHub(lidoLocatorStub.vaultHub());

        vm.startPrank(owner);
        vaultsAdapter =
            new VaultsAdapter(owner, address(lidoLocatorStub), owner, VALIDATOR_EXIT_FEE_LIMIT);
        setJailStatusInOperatorGrid = new SetJailStatusInOperatorGrid(owner, address(vaultsAdapter));
        vm.stopPrank();

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(address(vaultHub), "vaultHubStub");
        vm.label(address(vaultsAdapter), "vaultsAdapter");
        vm.label(address(setJailStatusInOperatorGrid), "setJailStatusInOperatorGrid");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setJailStatusInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(setJailStatusInOperatorGrid.vaultsAdapter()),
            address(vaultsAdapter),
            "vaultsAdapter"
        );
        assertEq(
            vaultsAdapter.validatorExitFeeLimit(), VALIDATOR_EXIT_FEE_LIMIT, "validatorExitFeeLimit"
        );
        assertEq(vaultsAdapter.trustedCaller(), owner, "adapter trustedCaller");
        assertEq(vaultsAdapter.evmScriptExecutor(), owner, "evmScriptExecutor");
        assertEq(address(vaultsAdapter.lidoLocator()), address(lidoLocatorStub), "lidoLocator");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        setJailStatusInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_vaults_array
    function test_RevertWhen_VaultsAreEmpty() external {
        address[] memory vaults = new address[](0);
        bool[] memory jailStatuses = new bool[](0);

        vm.expectRevert("EMPTY_VAULTS");
        setJailStatusInOperatorGrid.createEVMScript(owner, abi.encode(vaults, jailStatuses));
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        setJailStatusInOperatorGrid.createEVMScript(
            owner, abi.encode(_vaults(stranger), _jailStatuses(true, false))
        );
    }

    // python: test_zero_vault_address
    function test_RevertWhen_VaultIsZero() external {
        vm.expectRevert("ZERO_VAULT");
        setJailStatusInOperatorGrid.createEVMScript(
            owner, abi.encode(_vaults(address(0), stranger), _jailStatuses(true, false))
        );
    }

    // python: test_different_node_operators
    function test_RevertWhen_NodeOperatorsDiffer() external {
        StakingVaultStub firstVault = new StakingVaultStub(nodeOperator);
        StakingVaultStub secondVault = new StakingVaultStub(anotherNodeOperator);

        vm.expectRevert("INVALID_NODE_OPERATOR");
        setJailStatusInOperatorGrid.createEVMScript(
            owner,
            abi.encode(
                _vaults(address(firstVault), address(secondVault)), _jailStatuses(true, false)
            )
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        StakingVaultStub firstVault = new StakingVaultStub(nodeOperator);
        StakingVaultStub secondVault = new StakingVaultStub(nodeOperator);

        address[] memory vaults = _vaults(address(firstVault), address(secondVault));
        bool[] memory jailStatuses = _jailStatuses(true, false);

        bytes memory evmScript =
            setJailStatusInOperatorGrid.createEVMScript(owner, abi.encode(vaults, jailStatuses));

        assertEq(evmScript, _setJailStatusesScript(vaults, jailStatuses), "evmScript");
    }

    // python: test_same_jail_status_fails
    function test_EmitsVaultJailStatusUpdateFailedWhenStatusIsUnchanged() external {
        operatorGrid.setVaultJailStatus(vault, true);

        vm.expectEmit(address(vaultsAdapter));
        emit VaultJailStatusUpdateFailed(vault, true);

        vm.prank(owner);
        vaultsAdapter.setVaultJailStatus(vault, true);
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        bool[] memory jailStatuses = _jailStatuses(true, false);

        (address[] memory decodedVaults, bool[] memory decodedJailStatuses) =
            setJailStatusInOperatorGrid.decodeEVMScriptCallData(abi.encode(vaults, jailStatuses));

        assertEq(decodedVaults, vaults, "vaults");
        assertEq(decodedJailStatuses, jailStatuses, "jailStatuses");
    }

    // python: test_can_set_jail_status_on_disconnected_vault
    function test_SetsJailStatusOnDisconnectedVault() external {
        assertFalse(vaultHub.isVaultConnected(vault), "isVaultConnected");

        vm.expectEmit(address(operatorGrid));
        emit VaultJailStatusUpdated(vault, true);

        vm.prank(owner);
        vaultsAdapter.setVaultJailStatus(vault, true);

        assertTrue(operatorGrid.isVaultInJail(vault), "isVaultInJail");
    }

    function _vaults(address single) private pure returns (address[] memory vaults) {
        vaults = new address[](1);
        vaults[0] = single;
    }

    function _vaults(address first, address second) private pure returns (address[] memory vaults) {
        vaults = new address[](2);
        vaults[0] = first;
        vaults[1] = second;
    }

    function _jailStatuses(bool first, bool second)
        private
        pure
        returns (bool[] memory jailStatuses)
    {
        jailStatuses = new bool[](2);
        jailStatuses[0] = first;
        jailStatuses[1] = second;
    }

    /// @dev python: encode_call_script of one adapter.setVaultJailStatus per vault
    function _setJailStatusesScript(address[] memory vaults, bool[] memory jailStatuses)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](vaults.length);

        for (uint256 i; i < vaults.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IVaultsAdapter.setVaultJailStatus.selector, vaults[i], jailStatuses[i]
            );
        }

        return EVMScripts.encodeCallScript(address(vaultsAdapter), calls);
    }
}
