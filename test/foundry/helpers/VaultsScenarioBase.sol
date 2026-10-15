// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";
import {EasyTrackScenarioBase} from "test/foundry/helpers/EasyTrackScenarioBase.sol";
import {ILidoLocator} from "test/foundry/interfaces/External.sol";
import {
    ILazyOracle,
    IOperatorGrid,
    IVaultFactory,
    IVaultHub,
    IVaultsAdapter,
    TierParams
} from "test/foundry/interfaces/Vaults.sol";

/// @notice Harness for the vaults scenarios: a fresh Easy Track with Voting as admin, a fresh
///         `VaultsAdapter` for its executor funded for validator exits, and the live grid, hub,
///         vault factory and lazy oracle of the locator. The test deploys a factory under test,
///         registers it as Voting and drives it. Skipped on a chain without the vaults contracts.
abstract contract VaultsScenarioBase is EasyTrackScenarioBase {
    uint256 internal constant INITIAL_VAULT_BALANCE = 2 ether;
    uint256 internal constant VALIDATOR_EXIT_FEE_LIMIT = 1 ether;

    /// @dev What the adapter holds to pay validator exit fees
    uint256 internal constant ADAPTER_BALANCE = 10 ether;

    /// @dev python: the `createVaultWithDashboard` arguments of the `vaults` fixture
    uint256 internal constant NODE_OPERATOR_FEE_BP = 10000;
    uint256 internal constant CONFIRM_EXPIRY = 10000;

    /// @dev python: the `updateReportData` arguments of a fresh report
    uint256 internal constant REPORT_REF_SLOT = 1000;
    string internal constant REPORT_CID = "0x00";

    ILidoLocator internal locator;
    IOperatorGrid internal operatorGrid;
    IVaultHub internal vaultHub;
    IVaultFactory internal vaultFactory;
    ILazyOracle internal lazyOracle;
    address internal accountingOracle;

    IVaultsAdapter internal adapter;

    /// @dev The node operator and manager every vault of the harness gets
    address internal vaultNodeOperator = makeAddr("vaultNodeOperator");
    address internal vaultNodeOperatorManager = makeAddr("vaultNodeOperatorManager");

    function setUp() public virtual {
        _forkAndInitialize();

        vm.skip(!_hasVaults(), "the locator has no vaults contracts on this chain");

        locator = ILidoLocator(config.locator);
        operatorGrid = IOperatorGrid(locator.operatorGrid());
        vaultHub = IVaultHub(locator.vaultHub());
        vaultFactory = IVaultFactory(locator.vaultFactory());
        lazyOracle = ILazyOracle(locator.lazyOracle());
        accountingOracle = locator.accountingOracle();
        creator = makeAddr("trustedAddress");

        vm.label(address(operatorGrid), "OperatorGrid");
        vm.label(address(vaultHub), "VaultHub");
        vm.label(address(vaultFactory), "VaultFactory");
        vm.label(address(lazyOracle), "LazyOracle");
        vm.label(accountingOracle, "AccountingOracle");

        _deployEasyTrack(_voting());

        // python: the `adapter` fixture
        adapter = IVaultsAdapter(
            _deployArtifact(
                "VaultsAdapter",
                abi.encode(creator, locator, evmScriptExecutor, VALIDATOR_EXIT_FEE_LIMIT)
            )
        );

        vm.deal(address(adapter), ADAPTER_BALANCE);

        _grantRole(address(operatorGrid), operatorGrid.REGISTRY_ROLE(), address(adapter));
    }

    // --- factory under test ---

    /// @dev python: setup_evm_script_factory. The only factory of the fresh Easy Track
    function _registerOnlyFactory(address factory, bytes memory permissions) internal {
        _registerFactory(factory, permissions);

        address[] memory factories = easyTrack.getEVMScriptFactories();
        assertEq(factories.length, 1, "setup: factories");
        assertEq(factories[0], factory, "setup: factory");
    }

    /// @dev python: execute_motion. The one pending motion is enacted
    function _executeMotion(uint256 motionId, bytes memory callData) internal {
        assertEq(easyTrack.getMotions().length, 1, "motions before enactment");

        _enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
    }

    // --- vaults and reports ---

    /// @dev python: the `vaults` fixture. A vault with its dashboard, the test as admin, funded
    ///      with the initial balance and connected to the hub as its last vault
    function _createVault() internal returns (address vault) {
        vm.deal(address(this), INITIAL_VAULT_BALANCE);

        (vault,) = vaultFactory.createVaultWithDashboard{value: INITIAL_VAULT_BALANCE}(
            address(this),
            vaultNodeOperator,
            vaultNodeOperatorManager,
            NODE_OPERATOR_FEE_BP,
            CONFIRM_EXPIRY,
            new IVaultFactory.RoleAssignment[](0)
        );

        vm.label(vault, string.concat("vault", vm.toString(vaultHub.vaultsCount())));

        assertEq(vault, vaultHub.vaultByIndex(vaultHub.vaultsCount()), "setup: vault connected");
    }

    /// @dev python: lazy_oracle.updateReportData at the current time, from the accounting oracle
    function _submitReport() internal {
        vm.prank(accountingOracle);
        lazyOracle.updateReportData(vm.getBlockTimestamp(), REPORT_REF_SLOT, bytes32(0), REPORT_CID);
    }

    /// @dev python: vault_hub.applyVaultReport at the current time, from the lazy oracle, with
    ///      no max liability shares and no slashing reserve
    function _applyVaultReport(
        address vault,
        uint256 totalValue,
        int256 inOutDelta,
        uint256 cumulativeLidoFees,
        uint256 liabilityShares
    ) internal {
        vm.prank(address(lazyOracle));
        vaultHub.applyVaultReport(
            vault,
            vm.getBlockTimestamp(),
            totalValue,
            inOutDelta,
            cumulativeLidoFees,
            liabilityShares,
            0,
            0
        );
    }

    /// @dev python: vault_hub.mintShares from the vault's dashboard, its owner in the hub
    function _mintShares(address vault, uint256 shares) internal {
        vm.prank(vaultHub.vaultConnection(vault).owner);
        vaultHub.mintShares(vault, address(this), shares);
    }

    // --- tiers ---

    function _tier(
        uint256 shareLimit,
        uint256 reserveRatioBP,
        uint256 forcedRebalanceThresholdBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    ) internal pure returns (TierParams memory) {
        return TierParams({
            shareLimit: shareLimit,
            reserveRatioBP: reserveRatioBP,
            forcedRebalanceThresholdBP: forcedRebalanceThresholdBP,
            infraFeeBP: infraFeeBP,
            liquidityFeeBP: liquidityFeeBP,
            reservationFeeBP: reservationFeeBP
        });
    }

    /// @dev The tier `tierId` holds `params`
    function _assertTier(uint256 tierId, TierParams memory params) internal view {
        IOperatorGrid.Tier memory tier = operatorGrid.tier(tierId);
        string memory label = string.concat("tier ", vm.toString(tierId), " ");

        assertEq(tier.shareLimit, params.shareLimit, string.concat(label, "shareLimit"));
        assertEq(tier.reserveRatioBP, params.reserveRatioBP, string.concat(label, "reserveRatioBP"));
        assertEq(
            tier.forcedRebalanceThresholdBP,
            params.forcedRebalanceThresholdBP,
            string.concat(label, "forcedRebalanceThresholdBP")
        );
        assertEq(tier.infraFeeBP, params.infraFeeBP, string.concat(label, "infraFeeBP"));
        assertEq(tier.liquidityFeeBP, params.liquidityFeeBP, string.concat(label, "liquidityFeeBP"));
        assertEq(
            tier.reservationFeeBP, params.reservationFeeBP, string.concat(label, "reservationFeeBP")
        );
    }

    // --- logs ---

    /// @dev The number of `logs` that `emitter` emitted with `selector`
    function _countLogs(Vm.Log[] memory logs, address emitter, bytes32 selector)
        internal
        pure
        returns (uint256 count)
    {
        for (uint256 i; i < logs.length; ++i) {
            if (logs[i].emitter == emitter && logs[i].topics[0] == selector) {
                ++count;
            }
        }
    }

    /// @dev The one log that `emitter` emitted with `selector`
    function _singleLog(Vm.Log[] memory logs, address emitter, bytes32 selector)
        internal
        pure
        returns (Vm.Log memory found)
    {
        assertEq(_countLogs(logs, emitter, selector), 1, "event count");

        for (uint256 i; i < logs.length; ++i) {
            if (logs[i].emitter == emitter && logs[i].topics[0] == selector) {
                return logs[i];
            }
        }
    }

    // --- chain ---

    /// @dev Whether the locator resolves an operator grid, a vaults deployment
    function _hasVaults() private view returns (bool) {
        (bool ok, bytes memory data) =
            config.locator.staticcall(abi.encodeCall(ILidoLocator.operatorGrid, ()));

        return ok && data.length == 32 && abi.decode(data, (address)) != address(0);
    }
}
