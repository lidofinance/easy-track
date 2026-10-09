// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {VaultsScenarioBase} from "test/foundry/helpers/VaultsScenarioBase.sol";
import {
    IAlterTiersInOperatorGrid,
    IOperatorGridFactory,
    IRegisterGroupsInOperatorGrid,
    IUpdateGroupsShareLimitInOperatorGrid,
    IUpdateVaultsFeesInOperatorGrid,
    IVaultsAdapterFactory
} from "test/foundry/interfaces/Factories.sol";
import {
    IOperatorGrid,
    IVaultHub,
    IVaultsAdapter,
    TierParams
} from "test/foundry/interfaces/Vaults.sol";

/// @notice The six operator grid factories, each deployed fresh from the `contracts` profile
///         artifacts and registered in the fresh Easy Track, driving the live grid: groups and
///         tiers directly, the jail and the vault fees through the adapter.
contract OperatorGridTest is VaultsScenarioBase {
    uint256 private constant MAX_SHARE_LIMIT = 10000;
    uint256 private constant DEFAULT_TIER_MAX_SHARE_LIMIT = 1000e18;
    uint256 private constant MAX_LIQUIDITY_FEE_BP = 1000;
    uint256 private constant MAX_RESERVATION_FEE_BP = 100;
    uint256 private constant MAX_INFRA_FEE_BP = 100;

    /// @dev python: operator_addresses, in the ascending order the group factory requires
    address private constant OPERATOR_1 = address(1);
    address private constant OPERATOR_2 = address(2);

    // python: test_register_group_happy_path
    function testFork_RegistersGroups() external {
        _grantRegistryRoles();

        address factory = _deployArtifact(
            "RegisterGroupsInOperatorGrid", abi.encode(creator, locator, MAX_SHARE_LIMIT)
        );

        _assertGridFactory(factory);
        assertEq(
            IRegisterGroupsInOperatorGrid(factory).maxShareLimit(),
            MAX_SHARE_LIMIT,
            "setup: maxShareLimit"
        );

        _registerOnlyFactory(
            factory,
            abi.encodePacked(
                operatorGrid,
                IOperatorGrid.registerGroup.selector,
                operatorGrid,
                IOperatorGrid.registerTiers.selector
            )
        );

        address[] memory operators = _operators();
        uint256[] memory shareLimits = new uint256[](2);
        shareLimits[0] = 1000;
        shareLimits[1] = 5000;
        TierParams[][] memory tiers = new TierParams[][](2);
        tiers[0] = new TierParams[](2);
        tiers[0][0] = _tier(500, 200, 100, 50, 40, 10);
        tiers[0][1] = _tier(800, 200, 100, 50, 40, 10);
        tiers[1] = new TierParams[](2);
        tiers[1][0] = _tier(800, 200, 100, 50, 40, 10);
        tiers[1][1] = _tier(800, 200, 100, 50, 40, 10);

        for (uint256 i; i < operators.length; ++i) {
            IOperatorGrid.Group memory group = operatorGrid.group(operators[i]);
            assertEq(group.operator, address(0), "group operator before");
            assertEq(group.shareLimit, 0, "group shareLimit before");
            assertEq(group.tierIds.length, 0, "group tiers before");
        }

        bytes memory callData = abi.encode(operators, shareLimits, tiers);

        uint256 motionId = _createMotion(factory, creator, callData);
        _executeMotion(motionId, callData);

        for (uint256 i; i < operators.length; ++i) {
            IOperatorGrid.Group memory group = operatorGrid.group(operators[i]);
            assertEq(group.operator, operators[i], "group operator after");
            assertEq(group.shareLimit, shareLimits[i], "group shareLimit after");
            _assertGroupTiers(group, tiers[i]);
        }
    }

    // python: test_update_groups_share_limit_happy_path
    function testFork_UpdatesGroupShareLimits() external {
        _grantRegistryRoles();

        address factory = _deployArtifact(
            "UpdateGroupsShareLimitInOperatorGrid", abi.encode(creator, locator, MAX_SHARE_LIMIT)
        );

        _assertGridFactory(factory);
        assertEq(
            IUpdateGroupsShareLimitInOperatorGrid(factory).maxShareLimit(),
            MAX_SHARE_LIMIT,
            "setup: maxShareLimit"
        );

        _registerOnlyFactory(
            factory, abi.encodePacked(operatorGrid, IOperatorGrid.updateGroupShareLimit.selector)
        );

        address[] memory operators = _operators();
        uint256[] memory newShareLimits = new uint256[](2);
        newShareLimits[0] = 2000;
        newShareLimits[1] = 3000;

        for (uint256 i; i < operators.length; ++i) {
            operatorGrid.registerGroup(operators[i], newShareLimits[i] * 2);

            IOperatorGrid.Group memory group = operatorGrid.group(operators[i]);
            assertEq(group.operator, operators[i], "group operator before");
            assertEq(group.shareLimit, newShareLimits[i] * 2, "group shareLimit before");
        }

        bytes memory callData = abi.encode(operators, newShareLimits);

        uint256 motionId = _createMotion(factory, creator, callData);
        _executeMotion(motionId, callData);

        for (uint256 i; i < operators.length; ++i) {
            IOperatorGrid.Group memory group = operatorGrid.group(operators[i]);
            assertEq(group.operator, operators[i], "group operator after");
            assertEq(group.shareLimit, newShareLimits[i], "group shareLimit after");
        }
    }

    // python: test_register_tiers_happy_path
    function testFork_RegistersTiers() external {
        _grantRegistryRoles();

        address factory =
            _deployArtifact("RegisterTiersInOperatorGrid", abi.encode(creator, locator));

        _assertGridFactory(factory);

        _registerOnlyFactory(
            factory, abi.encodePacked(operatorGrid, IOperatorGrid.registerTiers.selector)
        );

        address[] memory operators = _operators();
        TierParams[][] memory tiers = new TierParams[][](2);
        tiers[0] = new TierParams[](2);
        tiers[0][0] = _tier(500, 200, 100, 50, 40, 10);
        tiers[0][1] = _tier(300, 150, 75, 25, 20, 5);
        tiers[1] = new TierParams[](2);
        tiers[1][0] = _tier(800, 250, 125, 60, 50, 15);
        tiers[1][1] = _tier(400, 180, 90, 30, 25, 8);

        for (uint256 i; i < operators.length; ++i) {
            operatorGrid.registerGroup(operators[i], 1000);

            assertEq(operatorGrid.group(operators[i]).tierIds.length, 0, "group tiers before");
        }

        bytes memory callData = abi.encode(operators, tiers);

        uint256 motionId = _createMotion(factory, creator, callData);
        _executeMotion(motionId, callData);

        for (uint256 i; i < operators.length; ++i) {
            _assertGroupTiers(operatorGrid.group(operators[i]), tiers[i]);
        }
    }

    // python: test_alter_tiers_happy_path
    function testFork_AltersTiers() external {
        _grantRegistryRoles();

        address factory = _deployArtifact(
            "AlterTiersInOperatorGrid", abi.encode(creator, locator, DEFAULT_TIER_MAX_SHARE_LIMIT)
        );

        _assertGridFactory(factory);
        assertEq(
            IAlterTiersInOperatorGrid(factory).defaultTierMaxShareLimit(),
            DEFAULT_TIER_MAX_SHARE_LIMIT,
            "setup: defaultTierMaxShareLimit"
        );

        _registerOnlyFactory(
            factory, abi.encodePacked(operatorGrid, IOperatorGrid.alterTiers.selector)
        );

        TierParams[] memory initialTiers = new TierParams[](2);
        initialTiers[0] = _tier(1000, 200, 100, 50, 40, 10);
        initialTiers[1] = _tier(1000, 200, 100, 50, 40, 10);
        TierParams[] memory newTiers = new TierParams[](2);
        newTiers[0] = _tier(2000, 300, 150, 75, 60, 20);
        newTiers[1] = _tier(3000, 400, 200, 100, 80, 30);

        operatorGrid.registerGroup(OPERATOR_1, MAX_SHARE_LIMIT);
        operatorGrid.registerTiers(OPERATOR_1, initialTiers);

        uint256 tiersCount = operatorGrid.tiersCount();
        uint256[] memory tierIds = new uint256[](2);
        tierIds[0] = tiersCount - 2;
        tierIds[1] = tiersCount - 1;

        for (uint256 i; i < tierIds.length; ++i) {
            _assertTier(tierIds[i], initialTiers[i]);
        }

        bytes memory callData = abi.encode(tierIds, newTiers);

        uint256 motionId = _createMotion(factory, creator, callData);
        _executeMotion(motionId, callData);

        for (uint256 i; i < tierIds.length; ++i) {
            _assertTier(tierIds[i], newTiers[i]);
        }
    }

    // python: test_set_jail_status_happy_path
    function testFork_SetsJailStatus() external {
        address factory =
            _deployArtifact("SetJailStatusInOperatorGrid", abi.encode(creator, adapter));

        _assertAdapterFactory(factory);

        _registerOnlyFactory(
            factory, abi.encodePacked(adapter, IVaultsAdapter.setVaultJailStatus.selector)
        );

        address vault = _createVault();
        address[] memory vaults = new address[](1);
        vaults[0] = vault;
        bool[] memory jailStatuses = new bool[](1);
        jailStatuses[0] = true;

        bytes memory callData = abi.encode(vaults, jailStatuses);

        uint256 motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions before enactment");

        _passMotionDuration();

        vm.expectEmit(address(operatorGrid));
        emit IOperatorGrid.VaultJailStatusUpdated(vault, true);

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
        assertTrue(operatorGrid.isVaultInJail(vault), "isVaultInJail");
        assertEq(
            _countLogs(
                vm.getRecordedLogs(),
                address(operatorGrid),
                IOperatorGrid.VaultJailStatusUpdated.selector
            ),
            vaults.length,
            "VaultJailStatusUpdated count"
        );
    }

    // python: test_update_vaults_fees_happy_path
    function testFork_UpdatesVaultFees() external {
        address factory = _deployArtifact(
            "UpdateVaultsFeesInOperatorGrid",
            abi.encode(
                creator,
                adapter,
                locator,
                MAX_LIQUIDITY_FEE_BP,
                MAX_RESERVATION_FEE_BP,
                MAX_INFRA_FEE_BP
            )
        );

        _assertAdapterFactory(factory);
        assertEq(
            IUpdateVaultsFeesInOperatorGrid(factory).lidoLocator(),
            address(locator),
            "setup: lidoLocator"
        );

        _registerOnlyFactory(
            factory, abi.encodePacked(adapter, IVaultsAdapter.updateVaultFees.selector)
        );

        address vault = _createVault();
        address[] memory vaults = new address[](1);
        vaults[0] = vault;
        uint256[] memory infraFees = new uint256[](1);
        infraFees[0] = 1;
        uint256[] memory liquidityFees = new uint256[](1);
        liquidityFees[0] = 1;
        uint256[] memory reservationFees = new uint256[](1);
        reservationFees[0] = 0;

        IVaultHub.VaultConnection memory before = vaultHub.vaultConnection(vault);
        assertNotEq(before.infraFeeBP, infraFees[0], "infraFeeBP before");
        assertNotEq(before.liquidityFeeBP, liquidityFees[0], "liquidityFeeBP before");

        bytes memory callData = abi.encode(vaults, infraFees, liquidityFees, reservationFees);

        uint256 motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        _passMotionDuration();

        assertEq(easyTrack.getMotions().length, 1, "motions before enactment");

        // The adapter requires a fresh report on the vault
        _submitReport();
        _applyVaultReport(vault, INITIAL_VAULT_BALANCE, int256(INITIAL_VAULT_BALANCE), 0, 0);

        vm.expectEmit(address(vaultHub));
        emit IVaultHub.VaultFeesUpdated(
            vault,
            before.infraFeeBP,
            before.liquidityFeeBP,
            before.reservationFeeBP,
            infraFees[0],
            liquidityFees[0],
            reservationFees[0]
        );

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");

        IVaultHub.VaultConnection memory after_ = vaultHub.vaultConnection(vault);
        assertEq(after_.infraFeeBP, infraFees[0], "infraFeeBP after");
        assertEq(after_.liquidityFeeBP, liquidityFees[0], "liquidityFeeBP after");
        assertEq(after_.reservationFeeBP, reservationFees[0], "reservationFeeBP after");
        assertEq(
            _countLogs(
                vm.getRecordedLogs(), address(vaultHub), IVaultHub.VaultFeesUpdated.selector
            ),
            vaults.length,
            "VaultFeesUpdated count"
        );
    }

    /// @dev python: setup_operator_grid. The executor and the test may edit the grid
    function _grantRegistryRoles() private {
        bytes32 registryRole = operatorGrid.REGISTRY_ROLE();

        _grantRole(address(operatorGrid), registryRole, evmScriptExecutor);
        _grantRole(address(operatorGrid), registryRole, address(this));
    }

    function _operators() private pure returns (address[] memory operators) {
        operators = new address[](2);
        operators[0] = OPERATOR_1;
        operators[1] = OPERATOR_2;
    }

    /// @dev The group's tiers are `tiers`, in order
    function _assertGroupTiers(IOperatorGrid.Group memory group, TierParams[] memory tiers)
        private
        view
    {
        assertEq(group.tierIds.length, tiers.length, "group tiers after");

        for (uint256 i; i < tiers.length; ++i) {
            _assertTier(group.tierIds[i], tiers[i]);
        }
    }

    /// @dev The factory trusts the creator and reads the locator
    function _assertGridFactory(address factory) private view {
        assertEq(IOperatorGridFactory(factory).trustedCaller(), creator, "setup: trustedCaller");
        assertEq(
            IOperatorGridFactory(factory).lidoLocator(), address(locator), "setup: lidoLocator"
        );
    }

    /// @dev The factory trusts the creator and acts through the adapter, which trusts the creator
    ///      and takes the fresh executor's calls
    function _assertAdapterFactory(address factory) private view {
        assertEq(IVaultsAdapterFactory(factory).trustedCaller(), creator, "setup: trustedCaller");
        assertEq(
            IVaultsAdapterFactory(factory).vaultsAdapter(), address(adapter), "setup: vaultsAdapter"
        );
        assertEq(
            adapter.validatorExitFeeLimit(),
            VALIDATOR_EXIT_FEE_LIMIT,
            "setup: validatorExitFeeLimit"
        );
        assertEq(adapter.trustedCaller(), creator, "setup: adapter trustedCaller");
        assertEq(adapter.evmScriptExecutor(), evmScriptExecutor, "setup: adapter evmScriptExecutor");
    }
}
