// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    UpdateVaultsFeesInOperatorGrid
} from "contracts/EVMScriptFactories/vaultFactories/UpdateVaultsFeesInOperatorGrid.sol";
import {VaultsAdapter} from "contracts/EVMScriptFactories/vaultFactories/VaultsAdapter.sol";
import {IOperatorGrid, TierParams} from "contracts/interfaces/IOperatorGrid.sol";
import {IOperatorGridStub} from "contracts/interfaces/IOperatorGridStub.sol";
import {IVaultHub} from "contracts/interfaces/IVaultHub.sol";
import {IVaultsAdapter} from "contracts/interfaces/IVaultsAdapter.sol";
import {LidoLocatorStub} from "contracts/test/LidoLocatorStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";
import {Vaults} from "test/foundry/unit/helpers/Vaults.sol";

contract UpdateVaultsFeesInOperatorGridTest is Test {
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;
    /// @dev The maxLiquidityFeeBP, maxReservationFeeBP and maxInfraFeeBP constructor arguments
    uint256 internal constant FACTORY_MAX_FEE_BP = 10000;
    /// @dev python: node_operator, the operator of the tier with fees above the default tier's
    address internal constant OPERATOR = address(1);
    /// @dev The id of the first tier registered after the default one
    uint256 internal constant REGISTERED_TIER_ID = 1;
    /// @dev python: tier_infra_fee, tier_liquidity_fee and tier_reservation_fee
    uint256 internal constant TIER_INFRA_FEE_BP = 5000;
    uint256 internal constant TIER_LIQUIDITY_FEE_BP = 4000;
    uint256 internal constant TIER_RESERVATION_FEE_BP = 3000;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");
    /// @dev python: accounts[1] and accounts[2] as vault addresses
    address internal vault = makeAddr("vault");
    address internal anotherVault = makeAddr("anotherVault");

    LidoLocatorStub internal lidoLocatorStub;
    IOperatorGrid internal operatorGrid;
    IVaultHub internal vaultHub;
    VaultsAdapter internal vaultsAdapter;
    UpdateVaultsFeesInOperatorGrid internal updateVaultsFeesInOperatorGrid;

    function setUp() public {
        lidoLocatorStub = Vaults.deployLidoLocatorStub(owner);
        operatorGrid = IOperatorGrid(lidoLocatorStub.operatorGrid());
        vaultHub = IVaultHub(lidoLocatorStub.vaultHub());

        vm.startPrank(owner);
        vaultsAdapter =
            new VaultsAdapter(owner, address(lidoLocatorStub), owner, VALIDATOR_EXIT_FEE_LIMIT);
        updateVaultsFeesInOperatorGrid = new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(vaultsAdapter),
            address(lidoLocatorStub),
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP
        );
        vm.stopPrank();

        vm.label(address(lidoLocatorStub), "lidoLocatorStub");
        vm.label(address(operatorGrid), "operatorGridStub");
        vm.label(address(vaultHub), "vaultHubStub");
        vm.label(address(vaultsAdapter), "vaultsAdapter");
        vm.label(address(updateVaultsFeesInOperatorGrid), "updateVaultsFeesInOperatorGrid");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(updateVaultsFeesInOperatorGrid.trustedCaller(), owner, "trustedCaller");
        assertEq(
            address(updateVaultsFeesInOperatorGrid.vaultsAdapter()),
            address(vaultsAdapter),
            "vaultsAdapter"
        );
        assertEq(
            address(updateVaultsFeesInOperatorGrid.lidoLocator()),
            address(lidoLocatorStub),
            "lidoLocator"
        );
        assertEq(
            updateVaultsFeesInOperatorGrid.maxLiquidityFeeBP(),
            FACTORY_MAX_FEE_BP,
            "maxLiquidityFeeBP"
        );
        assertEq(
            updateVaultsFeesInOperatorGrid.maxReservationFeeBP(),
            FACTORY_MAX_FEE_BP,
            "maxReservationFeeBP"
        );
        assertEq(
            updateVaultsFeesInOperatorGrid.maxInfraFeeBP(), FACTORY_MAX_FEE_BP, "maxInfraFeeBP"
        );
        assertEq(
            vaultsAdapter.validatorExitFeeLimit(), VALIDATOR_EXIT_FEE_LIMIT, "validatorExitFeeLimit"
        );
        assertEq(vaultsAdapter.trustedCaller(), owner, "adapter trustedCaller");
        assertEq(vaultsAdapter.evmScriptExecutor(), owner, "evmScriptExecutor");
        assertEq(
            address(vaultsAdapter.lidoLocator()), address(lidoLocatorStub), "adapter lidoLocator"
        );
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        updateVaultsFeesInOperatorGrid.createEVMScript(stranger, "");
    }

    // python: test_empty_vaults_array
    function test_RevertWhen_VaultsAreEmpty() external {
        address[] memory vaults = new address[](0);
        uint256[] memory fees = new uint256[](0);

        vm.expectRevert("EMPTY_VAULTS");
        updateVaultsFeesInOperatorGrid.createEVMScript(owner, abi.encode(vaults, fees, fees, fees));
    }

    // python: test_array_length_mismatch
    function test_RevertWhen_ArrayLengthsMismatch() external {
        address[] memory vaults = _vaults(stranger);

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        updateVaultsFeesInOperatorGrid.createEVMScript(
            owner, abi.encode(vaults, _fees(1000, 2000), _fees(1000), _fees(1000))
        );

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        updateVaultsFeesInOperatorGrid.createEVMScript(
            owner, abi.encode(vaults, _fees(1000), _fees(1000, 2000), _fees(1000))
        );

        vm.expectRevert("ARRAY_LENGTH_MISMATCH");
        updateVaultsFeesInOperatorGrid.createEVMScript(
            owner, abi.encode(vaults, _fees(1000), _fees(1000), _fees(1000, 2000))
        );
    }

    // python: test_zero_vault_address
    function test_RevertWhen_VaultIsZero() external {
        vm.expectRevert("ZERO_VAULT");
        updateVaultsFeesInOperatorGrid.createEVMScript(
            owner,
            abi.encode(_vaults(address(0), stranger), _fees(30, 30), _fees(30, 30), _fees(5, 5))
        );
    }

    // python: test_fees_exceed_tier_limits
    function test_RevertWhen_FeesExceedTierLimits() external {
        _connectVault(stranger);

        // the default tier allows infra 50, liquidity 40 and reservation 10
        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        updateVaultsFeesInOperatorGrid.createEVMScript(owner, _encodeCallData(stranger, 51, 30, 5));

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        updateVaultsFeesInOperatorGrid.createEVMScript(owner, _encodeCallData(stranger, 30, 41, 5));

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        updateVaultsFeesInOperatorGrid.createEVMScript(owner, _encodeCallData(stranger, 30, 30, 11));
    }

    // python: test_create_evm_script_single_vault
    function test_CreatesEVMScriptForSingleVault() external {
        _connectVault(stranger);

        bytes memory evmScript = updateVaultsFeesInOperatorGrid.createEVMScript(
            owner, _encodeCallData(stranger, 20, 30, 5)
        );

        assertEq(evmScript, _updateVaultFeesScript(stranger, 20, 30, 5), "evmScript");
    }

    // python: test_create_evm_script_multiple_vaults
    function test_CreatesEVMScriptForMultipleVaults() external {
        _connectVault(vault);
        _connectVault(anotherVault);

        address[] memory vaults = _vaults(vault, anotherVault);
        uint256[] memory infraFeesBP = _fees(20, 15);
        uint256[] memory liquidityFeesBP = _fees(30, 25);
        uint256[] memory reservationFeesBP = _fees(5, 8);

        bytes memory evmScript = updateVaultsFeesInOperatorGrid.createEVMScript(
            owner, abi.encode(vaults, infraFeesBP, liquidityFeesBP, reservationFeesBP)
        );

        assertEq(
            evmScript,
            _updateVaultFeesScript(vaults, infraFeesBP, liquidityFeesBP, reservationFeesBP),
            "evmScript"
        );
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        address[] memory vaults = _vaults(vault, anotherVault);
        uint256[] memory infraFeesBP = _fees(20, 15);
        uint256[] memory liquidityFeesBP = _fees(30, 25);
        uint256[] memory reservationFeesBP = _fees(5, 8);

        (
            address[] memory decodedVaults,
            uint256[] memory decodedInfraFeesBP,
            uint256[] memory decodedLiquidityFeesBP,
            uint256[] memory decodedReservationFeesBP
        ) = updateVaultsFeesInOperatorGrid.decodeEVMScriptCallData(
                abi.encode(vaults, infraFeesBP, liquidityFeesBP, reservationFeesBP)
            );

        assertEq(decodedVaults, vaults, "vaults");
        assertEq(decodedInfraFeesBP, infraFeesBP, "infraFeesBP");
        assertEq(decodedLiquidityFeesBP, liquidityFeesBP, "liquidityFeesBP");
        assertEq(decodedReservationFeesBP, reservationFeesBP, "reservationFeesBP");
    }

    // python: test_can_create_evm_script_with_fees_up_to_tier_limits
    function test_AllowsFeesUpToTierLimits() external {
        _connectVault(stranger);
        _moveVaultToTierWithHighFees(stranger);

        bytes memory evmScript = updateVaultsFeesInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(
                stranger, TIER_INFRA_FEE_BP, TIER_LIQUIDITY_FEE_BP, TIER_RESERVATION_FEE_BP
            )
        );

        assertEq(
            evmScript,
            _updateVaultFeesScript(
                stranger, TIER_INFRA_FEE_BP, TIER_LIQUIDITY_FEE_BP, TIER_RESERVATION_FEE_BP
            ),
            "evmScript"
        );

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        updateVaultsFeesInOperatorGrid.createEVMScript(
            owner,
            _encodeCallData(
                stranger, TIER_INFRA_FEE_BP + 1, TIER_LIQUIDITY_FEE_BP, TIER_RESERVATION_FEE_BP
            )
        );
    }

    // python: test_deploy_with_zero_adapter
    function test_RevertWhen_DeployedWithZeroAdapter() external {
        vm.prank(owner);
        vm.expectRevert("ZERO_ADAPTER");
        new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(0),
            address(lidoLocatorStub),
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP
        );
    }

    // python: test_deploy_with_zero_lido_locator
    function test_RevertWhen_DeployedWithZeroLidoLocator() external {
        vm.prank(owner);
        vm.expectRevert("ZERO_LIDO_LOCATOR");
        new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(vaultsAdapter),
            address(0),
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP
        );
    }

    // python: test_deploy_with_max_liquidity_fee_too_high
    function test_RevertWhen_DeployedWithMaxLiquidityFeeTooHigh() external {
        vm.prank(owner);
        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(vaultsAdapter),
            address(lidoLocatorStub),
            Vaults.MAX_FEE_BP + 1,
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP
        );
    }

    // python: test_deploy_with_max_reservation_fee_too_high
    function test_RevertWhen_DeployedWithMaxReservationFeeTooHigh() external {
        vm.prank(owner);
        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(vaultsAdapter),
            address(lidoLocatorStub),
            FACTORY_MAX_FEE_BP,
            Vaults.MAX_FEE_BP + 1,
            FACTORY_MAX_FEE_BP
        );
    }

    // python: test_deploy_with_max_infra_fee_too_high
    function test_RevertWhen_DeployedWithMaxInfraFeeTooHigh() external {
        vm.prank(owner);
        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        new UpdateVaultsFeesInOperatorGrid(
            owner,
            address(vaultsAdapter),
            address(lidoLocatorStub),
            FACTORY_MAX_FEE_BP,
            FACTORY_MAX_FEE_BP,
            Vaults.MAX_FEE_BP + 1
        );
    }

    // python: test_fees_exceed_max_limits
    function test_RevertWhen_FeesExceedMaxLimits() external {
        // maxLiquidityFeeBP 3000, maxReservationFeeBP 2000 and maxInfraFeeBP 4000, all below the
        // tier the vault is moved onto
        vm.prank(owner);
        UpdateVaultsFeesInOperatorGrid factory = new UpdateVaultsFeesInOperatorGrid(
            owner, address(vaultsAdapter), address(lidoLocatorStub), 3000, 2000, 4000
        );

        _connectVault(stranger);
        _moveVaultToTierWithHighFees(stranger);

        vm.expectRevert("INFRA_FEE_TOO_HIGH");
        factory.createEVMScript(owner, _encodeCallData(stranger, 4001, 2000, 1000));

        vm.expectRevert("LIQUIDITY_FEE_TOO_HIGH");
        factory.createEVMScript(owner, _encodeCallData(stranger, 3000, 3001, 1000));

        vm.expectRevert("RESERVATION_FEE_TOO_HIGH");
        factory.createEVMScript(owner, _encodeCallData(stranger, 3000, 2000, 2001));

        bytes memory evmScript =
            factory.createEVMScript(owner, _encodeCallData(stranger, 4000, 3000, 2000));

        assertEq(evmScript, _updateVaultFeesScript(stranger, 4000, 3000, 2000), "evmScript");
    }

    /// @dev python: vault_hub_stub.connectVault(vault, {"from": owner})
    function _connectVault(address connected) private {
        vm.prank(owner);
        vaultHub.connectVault(connected);
    }

    /// @dev python: a group of share limit 10000 for node_operator, one tier of
    /// (10000, 200, 100, 5000, 4000, 3000) under it, and `moved` set onto that tier
    function _moveVaultToTierWithHighFees(address moved) private {
        TierParams[] memory tiers = new TierParams[](1);
        tiers[0] = Vaults.tierParams(
            10000, 200, 100, TIER_INFRA_FEE_BP, TIER_LIQUIDITY_FEE_BP, TIER_RESERVATION_FEE_BP
        );

        vm.startPrank(owner);
        operatorGrid.registerGroup(OPERATOR, 10000);
        operatorGrid.registerTiers(OPERATOR, tiers);
        IOperatorGridStub(address(operatorGrid)).setVaultTier(moved, REGISTERED_TIER_ID);
        vm.stopPrank();
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

    function _fees(uint256 fee) private pure returns (uint256[] memory fees) {
        fees = new uint256[](1);
        fees[0] = fee;
    }

    function _fees(uint256 first, uint256 second) private pure returns (uint256[] memory fees) {
        fees = new uint256[](2);
        fees[0] = first;
        fees[1] = second;
    }

    /// @dev python: create_calldata([vault], [infraFeeBP], [liquidityFeeBP], [reservationFeeBP])
    function _encodeCallData(
        address single,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    ) private pure returns (bytes memory) {
        return abi.encode(
            _vaults(single), _fees(infraFeeBP), _fees(liquidityFeeBP), _fees(reservationFeeBP)
        );
    }

    /// @dev python: adapter.updateVaultFees.encode_input(vault, infra, liquidity, reservation)
    function _updateVaultFeesCallData(
        address single,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    ) private pure returns (bytes memory) {
        return abi.encodeWithSelector(
            IVaultsAdapter.updateVaultFees.selector,
            single,
            infraFeeBP,
            liquidityFeeBP,
            reservationFeeBP
        );
    }

    /// @dev python: encode_call_script([(adapter, updateVaultFees.encode_input(...))])
    function _updateVaultFeesScript(
        address single,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    ) private view returns (bytes memory) {
        return EVMScripts.encodeCallScript(
            address(vaultsAdapter),
            _updateVaultFeesCallData(single, infraFeeBP, liquidityFeeBP, reservationFeeBP)
        );
    }

    /// @dev python: encode_call_script of one adapter.updateVaultFees per vault
    function _updateVaultFeesScript(
        address[] memory vaults,
        uint256[] memory infraFeesBP,
        uint256[] memory liquidityFeesBP,
        uint256[] memory reservationFeesBP
    ) private view returns (bytes memory) {
        bytes[] memory calls = new bytes[](vaults.length);

        for (uint256 i; i < vaults.length; ++i) {
            calls[i] = _updateVaultFeesCallData(
                vaults[i], infraFeesBP[i], liquidityFeesBP[i], reservationFeesBP[i]
            );
        }

        return EVMScripts.encodeCallScript(address(vaultsAdapter), calls);
    }
}
