// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SocializeBadDebtInVaultHub
} from "contracts/EVMScriptFactories/vaultFactories/SocializeBadDebtInVaultHub.sol";
import {VaultsAdapter} from "contracts/EVMScriptFactories/vaultFactories/VaultsAdapter.sol";
import {IVaultHub} from "contracts/interfaces/IVaultHub.sol";
import {IVaultsAdapter} from "contracts/interfaces/IVaultsAdapter.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {StakingVaultStub} from "contracts/test/StakingVaultStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract SocializeBadDebtInVaultHubTest is Test {
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: accounts[5] and accounts[6] as node operators
    address internal nodeOperator = makeAddr("nodeOperator");
    address internal anotherNodeOperator = makeAddr("anotherNodeOperator");
    /// @dev python: accounts[5] and accounts[6] as bad debt vaults, accounts[7] and accounts[8]
    /// as vault acceptors
    address internal badDebtVault = makeAddr("badDebtVault");
    address internal anotherBadDebtVault = makeAddr("anotherBadDebtVault");
    address internal vaultAcceptor = makeAddr("vaultAcceptor");
    address internal anotherVaultAcceptor = makeAddr("anotherVaultAcceptor");

    LidoLocatorStub internal lidoLocatorStub;
    IVaultHub internal vaultHub;
    VaultsAdapter internal vaultsAdapter;
    SocializeBadDebtInVaultHub internal socializeBadDebtInVaultHub;

    // Re-declared: solc 0.8.6 cannot emit another contract's events
    event BadDebtSocializationFailed(
        address indexed badDebtVault, address indexed vaultAcceptor, uint256 maxSharesToSocialize
    );

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        vaultHub = IVaultHub(lidoLocatorStub.vaultHub());

        vm.startPrank(owner);
        vaultsAdapter =
            new VaultsAdapter(owner, address(lidoLocatorStub), owner, VALIDATOR_EXIT_FEE_LIMIT);
        socializeBadDebtInVaultHub = new SocializeBadDebtInVaultHub(owner, address(vaultsAdapter));
        vm.stopPrank();

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(vaultHub), "vaultHubStub");
        vm.label(address(vaultsAdapter), "vaultsAdapter");
        vm.label(address(socializeBadDebtInVaultHub), "socializeBadDebtInVaultHub");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(socializeBadDebtInVaultHub.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(socializeBadDebtInVaultHub.vaultsAdapter()),
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
        socializeBadDebtInVaultHub.createEVMScript(stranger, "");
    }

    // python: test_empty_bad_debt_vaults_array
    function test_RevertWhen_BadDebtVaultsAreEmpty() external {
        address[] memory badDebtVaults = new address[](0);
        address[] memory vaultAcceptors = new address[](0);
        uint256[] memory maxSharesToSocialize = new uint256[](0);

        vm.expectRevert("EMPTY_BAD_DEBT_VAULTS");
        socializeBadDebtInVaultHub.createEVMScript(
            owner, abi.encode(badDebtVaults, vaultAcceptors, maxSharesToSocialize)
        );
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        socializeBadDebtInVaultHub.createEVMScript(
            owner, abi.encode(_vaults(stranger), _vaults(stranger, stranger), _shares(100))
        );
    }

    // python: test_zero_bad_debt_vault_address
    function test_RevertWhen_BadDebtVaultIsZero() external {
        vm.expectRevert("ZERO_BAD_DEBT_VAULT");
        socializeBadDebtInVaultHub.createEVMScript(
            owner,
            abi.encode(
                _vaults(address(0), stranger), _vaults(stranger, stranger), _shares(100, 200)
            )
        );
    }

    // python: test_zero_vault_acceptor_address
    function test_RevertWhen_VaultAcceptorIsZero() external {
        vm.expectRevert("ZERO_VAULT_ACCEPTOR");
        socializeBadDebtInVaultHub.createEVMScript(
            owner,
            abi.encode(
                _vaults(stranger, stranger), _vaults(address(0), stranger), _shares(100, 200)
            )
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        StakingVaultStub firstBadDebtVault = new StakingVaultStub(nodeOperator);
        StakingVaultStub secondBadDebtVault = new StakingVaultStub(anotherNodeOperator);
        StakingVaultStub firstVaultAcceptor = new StakingVaultStub(nodeOperator);
        StakingVaultStub secondVaultAcceptor = new StakingVaultStub(anotherNodeOperator);

        address[] memory badDebtVaults =
            _vaults(address(firstBadDebtVault), address(secondBadDebtVault));
        address[] memory vaultAcceptors =
            _vaults(address(firstVaultAcceptor), address(secondVaultAcceptor));
        uint256[] memory maxSharesToSocialize = _shares(100, 200);

        bytes memory evmScript = socializeBadDebtInVaultHub.createEVMScript(
            owner, abi.encode(badDebtVaults, vaultAcceptors, maxSharesToSocialize)
        );

        assertEq(
            evmScript,
            _socializeBadDebtScript(badDebtVaults, vaultAcceptors, maxSharesToSocialize),
            "evmScript"
        );
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory badDebtVaults = _vaults(badDebtVault, anotherBadDebtVault);
        address[] memory vaultAcceptors = _vaults(vaultAcceptor, anotherVaultAcceptor);
        uint256[] memory maxSharesToSocialize = _shares(100, 200);

        (
            address[] memory decodedBadDebtVaults,
            address[] memory decodedVaultAcceptors,
            uint256[] memory decodedMaxSharesToSocialize
        ) = socializeBadDebtInVaultHub.decodeEVMScriptCallData(
                abi.encode(badDebtVaults, vaultAcceptors, maxSharesToSocialize)
            );

        assertEq(decodedBadDebtVaults, badDebtVaults, "badDebtVaults");
        assertEq(decodedVaultAcceptors, vaultAcceptors, "vaultAcceptors");
        assertEq(decodedMaxSharesToSocialize, maxSharesToSocialize, "maxSharesToSocialize");
    }

    // python: test_socialize_bad_debt_fails_when_bad_debt_vault_not_connected
    function test_EmitsBadDebtSocializationFailedWhenBadDebtVaultIsNotConnected() external {
        uint256 maxSharesToSocialize = 100;

        _connectVault(vaultAcceptor);

        assertFalse(vaultHub.isVaultConnected(badDebtVault), "badDebtVault isVaultConnected");
        assertTrue(vaultHub.isVaultConnected(vaultAcceptor), "vaultAcceptor isVaultConnected");

        vm.expectEmit(address(vaultsAdapter));
        emit BadDebtSocializationFailed(badDebtVault, vaultAcceptor, maxSharesToSocialize);

        vm.prank(owner);
        vaultsAdapter.socializeBadDebt(badDebtVault, vaultAcceptor, maxSharesToSocialize);
    }

    // python: test_socialize_bad_debt_fails_when_vault_acceptor_not_connected
    function test_EmitsBadDebtSocializationFailedWhenVaultAcceptorIsNotConnected() external {
        uint256 maxSharesToSocialize = 100;

        _connectVault(badDebtVault);

        assertTrue(vaultHub.isVaultConnected(badDebtVault), "badDebtVault isVaultConnected");
        assertFalse(vaultHub.isVaultConnected(vaultAcceptor), "vaultAcceptor isVaultConnected");

        vm.expectEmit(address(vaultsAdapter));
        emit BadDebtSocializationFailed(badDebtVault, vaultAcceptor, maxSharesToSocialize);

        vm.prank(owner);
        vaultsAdapter.socializeBadDebt(badDebtVault, vaultAcceptor, maxSharesToSocialize);
    }

    /// @dev python: vault_hub.connectVault(vault, {"from": owner})
    function _connectVault(address connected) private {
        vm.prank(owner);
        vaultHub.connectVault(connected);
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

    function _shares(uint256 single) private pure returns (uint256[] memory shares) {
        shares = new uint256[](1);
        shares[0] = single;
    }

    function _shares(uint256 first, uint256 second) private pure returns (uint256[] memory shares) {
        shares = new uint256[](2);
        shares[0] = first;
        shares[1] = second;
    }

    /// @dev python: encode_call_script of one adapter.socializeBadDebt per bad debt vault
    function _socializeBadDebtScript(
        address[] memory badDebtVaults,
        address[] memory vaultAcceptors,
        uint256[] memory maxSharesToSocialize
    ) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](badDebtVaults.length);

        for (uint256 i; i < badDebtVaults.length; ++i) {
            calls[i] = abi.encodeWithSelector(
                IVaultsAdapter.socializeBadDebt.selector,
                badDebtVaults[i],
                vaultAcceptors[i],
                maxSharesToSocialize[i]
            );
        }

        return EVMScripts.encodeCallScript(address(vaultsAdapter), calls);
    }
}
