// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SetLiabilitySharesTargetInVaultHub
} from "contracts/EVMScriptFactories/vaultFactories/SetLiabilitySharesTargetInVaultHub.sol";
import {VaultsAdapter} from "contracts/EVMScriptFactories/vaultFactories/VaultsAdapter.sol";
import {IVaultsAdapter} from "contracts/interfaces/IVaultsAdapter.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract SetLiabilitySharesTargetInVaultHubTest is Test {
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: accounts[5] and accounts[6] as vault addresses
    address internal vault = makeAddr("vault");
    address internal anotherVault = makeAddr("anotherVault");

    LidoLocatorStub internal lidoLocatorStub;
    VaultsAdapter internal vaultsAdapter;
    SetLiabilitySharesTargetInVaultHub internal setLiabilitySharesTargetInVaultHub;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);

        vm.startPrank(owner);
        vaultsAdapter =
            new VaultsAdapter(owner, address(lidoLocatorStub), owner, VALIDATOR_EXIT_FEE_LIMIT);
        setLiabilitySharesTargetInVaultHub =
            new SetLiabilitySharesTargetInVaultHub(owner, address(vaultsAdapter));
        vm.stopPrank();

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(vaultsAdapter), "vaultsAdapter");
        vm.label(address(setLiabilitySharesTargetInVaultHub), "setLiabilitySharesTargetInVaultHub");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(setLiabilitySharesTargetInVaultHub.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(setLiabilitySharesTargetInVaultHub.vaultsAdapter()),
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
        setLiabilitySharesTargetInVaultHub.createEVMScript(stranger, "");
    }

    // python: test_empty_vaults_array
    function test_RevertWhen_VaultsAreEmpty() external {
        address[] memory vaults = new address[](0);
        uint256[] memory liabilitySharesTargets = new uint256[](0);

        vm.expectRevert("EMPTY_VAULTS");
        setLiabilitySharesTargetInVaultHub.createEVMScript(
            owner, abi.encode(vaults, liabilitySharesTargets)
        );
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        setLiabilitySharesTargetInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(stranger), _targets(100, 200))
        );
    }

    // python: test_zero_vault_address
    function test_RevertWhen_VaultIsZero() external {
        vm.expectRevert("ZERO_VAULT");
        setLiabilitySharesTargetInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(address(0), stranger), _targets(100, 200))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        uint256[] memory liabilitySharesTargets = _targets(100, 200);

        bytes memory evmScript = setLiabilitySharesTargetInVaultHub.createEVMScript(
            owner, abi.encode(vaults, liabilitySharesTargets)
        );

        assertEq(
            evmScript, _setLiabilitySharesTargetsScript(vaults, liabilitySharesTargets), "evmScript"
        );
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        uint256[] memory liabilitySharesTargets = _targets(100, 200);

        (address[] memory decodedVaults, uint256[] memory decodedLiabilitySharesTargets) = setLiabilitySharesTargetInVaultHub.decodeEVMScriptCallData(
            abi.encode(vaults, liabilitySharesTargets)
        );

        assertEq(decodedVaults, vaults, "vaults");
        assertEq(decodedLiabilitySharesTargets, liabilitySharesTargets, "liabilitySharesTargets");
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

    function _targets(uint256 first, uint256 second)
        private
        pure
        returns (uint256[] memory targets)
    {
        targets = new uint256[](2);
        targets[0] = first;
        targets[1] = second;
    }

    /// @dev python: encode_call_script of one adapter.setLiabilitySharesTarget per vault
    function _setLiabilitySharesTargetsScript(
        address[] memory vaults,
        uint256[] memory liabilitySharesTargets
    ) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](vaults.length);

        for (uint256 i; i < vaults.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IVaultsAdapter.setLiabilitySharesTarget.selector,
                vaults[i],
                liabilitySharesTargets[i]
            );
        }

        return EVMScripts.encodeCallScript(address(vaultsAdapter), calls);
    }
}
