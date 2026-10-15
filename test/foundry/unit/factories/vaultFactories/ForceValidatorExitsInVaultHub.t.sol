// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    ForceValidatorExitsInVaultHub
} from "contracts/EVMScriptFactories/vaultFactories/ForceValidatorExitsInVaultHub.sol";
import {VaultsAdapter} from "contracts/EVMScriptFactories/vaultFactories/VaultsAdapter.sol";
import {IVaultHub} from "contracts/interfaces/IVaultHub.sol";
import {IVaultHubStub} from "contracts/interfaces/IVaultHubStub.sol";
import {IVaultsAdapter} from "contracts/interfaces/IVaultsAdapter.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract ForceValidatorExitsInVaultHubTest is Test {
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;
    /// @dev python: owner.transfer(adapter, 10 * 10 ** 18)
    uint256 internal constant ADAPTER_BALANCE = 10 ether;
    /// @dev python: owner.transfer(adapter, "1 ether")
    uint256 internal constant TOP_UP = 1 ether;
    /// @dev The fee the EIP-7002 predeploy mock returns, the minimum of an empty request queue
    uint256 internal constant WITHDRAWAL_REQUEST_FEE = 1 wei;
    /// @dev python: the repeat count of the two-byte pubkey patterns. 48 repeats make 96 bytes,
    /// which the factory and the adapter read as two public keys
    uint256 internal constant PUBKEY_PATTERN_REPEATS = 48;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: accounts[5] and accounts[6] as vault addresses
    address internal vault = makeAddr("vault");
    address internal anotherVault = makeAddr("anotherVault");

    LidoLocatorStub internal lidoLocatorStub;
    IVaultHub internal vaultHub;
    VaultsAdapter internal vaultsAdapter;
    ForceValidatorExitsInVaultHub internal forceValidatorExitsInVaultHub;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event ForceValidatorExitFailed(address indexed vault, bytes pubkeys);

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        vaultHub = IVaultHub(lidoLocatorStub.vaultHub());

        vm.startPrank(owner);
        vaultsAdapter =
            new VaultsAdapter(owner, address(lidoLocatorStub), owner, VALIDATOR_EXIT_FEE_LIMIT);
        forceValidatorExitsInVaultHub =
            new ForceValidatorExitsInVaultHub(owner, address(vaultsAdapter));
        vm.stopPrank();

        vm.deal(address(vaultsAdapter), ADAPTER_BALANCE);

        // nothing is deployed at the EIP-7002 address locally, the mock answers the fee read
        address withdrawalRequestPredeploy =
            forceValidatorExitsInVaultHub.WITHDRAWAL_REQUEST_PREDEPLOY_ADDRESS();
        vm.mockCall(withdrawalRequestPredeploy, bytes(""), abi.encode(WITHDRAWAL_REQUEST_FEE));

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(vaultHub), "vaultHubStub");
        vm.label(address(vaultsAdapter), "vaultsAdapter");
        vm.label(address(forceValidatorExitsInVaultHub), "forceValidatorExitsInVaultHub");
        vm.label(withdrawalRequestPredeploy, "withdrawalRequestPredeploy");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(forceValidatorExitsInVaultHub.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(forceValidatorExitsInVaultHub.vaultsAdapter()),
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
        forceValidatorExitsInVaultHub.createEVMScript(stranger, "");
    }

    // python: test_empty_vaults_array
    function test_RevertWhen_VaultsAreEmpty() external {
        address[] memory vaults = new address[](0);
        bytes[] memory pubkeys = new bytes[](0);

        vm.expectRevert("EMPTY_VAULTS");
        forceValidatorExitsInVaultHub.createEVMScript(owner, abi.encode(vaults, pubkeys));
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        bytes memory pubkeys = _repeat("0x", PUBKEY_PATTERN_REPEATS);

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        forceValidatorExitsInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(stranger), _pubkeys(pubkeys, pubkeys))
        );
    }

    // python: test_zero_vault_address
    function test_RevertWhen_VaultIsZero() external {
        bytes memory pubkeys = _repeat("0x", PUBKEY_PATTERN_REPEATS);

        vm.expectRevert("ZERO_VAULT");
        forceValidatorExitsInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(address(0), stranger), _pubkeys(pubkeys, pubkeys))
        );
    }

    // python: test_empty_pubkeys
    function test_RevertWhen_PubkeysAreEmpty() external {
        vm.expectRevert("EMPTY_PUBKEYS");
        forceValidatorExitsInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(stranger), _pubkeys(""))
        );
    }

    // python: test_invalid_pubkeys_length
    function test_RevertWhen_PubkeysLengthIsInvalid() external {
        vm.expectRevert("INVALID_PUBKEYS_LENGTH");
        forceValidatorExitsInVaultHub.createEVMScript(
            owner,
            abi.encode(_vaults(stranger), _pubkeys(_repeat("0x", PUBKEY_PATTERN_REPEATS - 1)))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        bytes[] memory pubkeys =
            _pubkeys(_repeat("01", PUBKEY_PATTERN_REPEATS), _repeat("02", PUBKEY_PATTERN_REPEATS));

        bytes memory evmScript =
            forceValidatorExitsInVaultHub.createEVMScript(owner, abi.encode(vaults, pubkeys));

        assertEq(evmScript, _forceValidatorExitsScript(vaults, pubkeys), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        bytes[] memory pubkeys =
            _pubkeys(_repeat("01", PUBKEY_PATTERN_REPEATS), _repeat("02", PUBKEY_PATTERN_REPEATS));

        (address[] memory decodedVaults, bytes[] memory decodedPubkeys) =
            forceValidatorExitsInVaultHub.decodeEVMScriptCallData(abi.encode(vaults, pubkeys));

        assertEq(decodedVaults, vaults, "vaults");
        assertEq(decodedPubkeys, pubkeys, "pubkeys");
    }

    // python: test_withdraw_eth_called_by_stranger
    function test_RevertWhen_WithdrawETHCalledByStranger() external {
        vm.prank(stranger);
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        vaultsAdapter.withdrawETH(stranger);
    }

    // python: test_withdraw_eth_no_balance
    function test_RevertWhen_NoETHToWithdraw() external {
        vm.prank(owner);
        vaultsAdapter.withdrawETH(owner);

        vm.prank(owner);
        vm.expectRevert("NO_ETH_TO_WITHDRAW");
        vaultsAdapter.withdrawETH(owner);
    }

    // python: test_withdraw_eth_success
    function test_WithdrawsAllETH() external {
        vm.deal(address(vaultsAdapter), ADAPTER_BALANCE + TOP_UP);

        uint256 initialOwnerBalance = owner.balance;
        uint256 initialBalance = address(vaultsAdapter).balance;

        vm.recordLogs();

        vm.prank(owner);
        vaultsAdapter.withdrawETH(owner);

        // forge charges the sender no gas, so the owner receives the whole balance
        assertEq(address(vaultsAdapter).balance, 0, "adapter balance");
        assertEq(owner.balance, initialOwnerBalance + initialBalance, "owner balance");
        assertEq(vm.getRecordedLogs().length, 0, "events");
    }

    // python: test_force_validator_exit_fails_when_no_obligations_shortfall
    function test_EmitsForceValidatorExitFailedWhenNoObligationsShortfall() external {
        bytes memory pubkeys = _repeat("01", PUBKEY_PATTERN_REPEATS);

        vm.prank(owner);
        vaultHub.connectVault(stranger);

        IVaultHubStub(address(vaultHub)).setObligationsShortfallValue(stranger, 0);

        vm.expectEmit(address(vaultsAdapter));
        emit ForceValidatorExitFailed(stranger, pubkeys);

        vm.recordLogs();

        vm.prank(owner);
        vaultsAdapter.forceValidatorExit(stranger, pubkeys);

        assertEq(vm.getRecordedLogs().length, 1, "events");
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

    function _pubkeys(bytes memory single) private pure returns (bytes[] memory pubkeys) {
        pubkeys = new bytes[](1);
        pubkeys[0] = single;
    }

    function _pubkeys(bytes memory first, bytes memory second)
        private
        pure
        returns (bytes[] memory pubkeys)
    {
        pubkeys = new bytes[](2);
        pubkeys[0] = first;
        pubkeys[1] = second;
    }

    /// @dev python: `pattern * count`, a two-byte literal repeated `count` times
    function _repeat(bytes2 pattern, uint256 count) private pure returns (bytes memory repeated) {
        repeated = new bytes(2 * count);

        for (uint256 i; i < repeated.length; ++i) {
            repeated[i] = pattern[i % 2];
        }
    }

    /// @dev python: encode_call_script of one adapter.forceValidatorExit per vault
    function _forceValidatorExitsScript(address[] memory vaults, bytes[] memory pubkeys)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory calls = new bytes[](vaults.length);

        for (uint256 i; i < vaults.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IVaultsAdapter.forceValidatorExit.selector, vaults[i], pubkeys[i]
            );
        }

        return EVMScripts.encodeCallScript(address(vaultsAdapter), calls);
    }
}
