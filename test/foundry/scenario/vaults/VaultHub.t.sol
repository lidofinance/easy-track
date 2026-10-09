// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";
import {VaultsScenarioBase} from "test/foundry/helpers/VaultsScenarioBase.sol";
import {IVaultsAdapterFactory} from "test/foundry/interfaces/Factories.sol";
import {IVaultHub, IVaultsAdapter, TierParams} from "test/foundry/interfaces/Vaults.sol";

/// @notice The three vault hub factories, each deployed fresh from the `contracts` profile
///         artifacts and registered in the fresh Easy Track, driving the live hub through the
///         adapter over two vaults of one operator: forced exits of an unhealthy vault, the
///         redemption shares of minted vaults, and bad debt moved between the two.
contract VaultHubTest is VaultsScenarioBase {
    /// @dev python: the default tier the `vaults` fixture opens for minting
    uint256 private constant DEFAULT_TIER_ID = 0;
    uint256 private constant MINTING_SHARE_LIMIT = 100_000e18;

    /// @dev python: the ASCII string "01" repeated 48 times, two 48-byte keys, not one
    uint256 private constant PUBKEYS_LENGTH = 96;

    /// @dev python: liability_shares_targets
    uint256 private constant FIRST_LIABILITY_TARGET = 100;
    uint256 private constant SECOND_LIABILITY_TARGET = 200;

    /// @dev python: max_shares_to_socialize
    uint256 private constant MAX_SHARES_TO_SOCIALIZE = INITIAL_VAULT_BALANCE / 100;

    address[] internal vaults;

    function setUp() public override {
        super.setUp();

        _grantRole(address(vaultHub), vaultHub.BAD_DEBT_MASTER_ROLE(), address(adapter));
        _grantRole(address(vaultHub), vaultHub.VALIDATOR_EXIT_ROLE(), address(adapter));
        _grantRole(address(vaultHub), vaultHub.REDEMPTION_MASTER_ROLE(), address(adapter));

        // python: the `vaults` fixture. The adapter opens the default tier for minting
        uint256[] memory tierIds = new uint256[](1);
        tierIds[0] = DEFAULT_TIER_ID;
        TierParams[] memory tiers = new TierParams[](1);
        tiers[0] = _tier(MINTING_SHARE_LIMIT, 300, 250, 50, 40, 10);

        vm.prank(address(adapter));
        operatorGrid.alterTiers(tierIds, tiers);

        vaults.push(_createVault());
        vaults.push(_createVault());
    }

    // python: test_force_validator_exits_happy_path
    function testFork_ForcesValidatorExits() external {
        address factory =
            _deployArtifact("ForceValidatorExitsInVaultHub", abi.encode(creator, adapter));

        _assertAdapterFactory(factory);
        assertEq(
            adapter.validatorExitFeeLimit(),
            VALIDATOR_EXIT_FEE_LIMIT,
            "setup: validatorExitFeeLimit"
        );

        _registerOnlyFactory(
            factory, abi.encodePacked(adapter, IVaultsAdapter.forceValidatorExit.selector)
        );

        address[] memory exitingVaults = new address[](1);
        exitingVaults[0] = vaults[0];
        bytes[] memory pubkeys = new bytes[](1);
        pubkeys[0] = _asciiPubkeys();

        bytes memory callData = abi.encode(exitingVaults, pubkeys);

        uint256 motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        _passMotionDuration();

        // A fresh report leaves the vault with fees it cannot settle, so it is unhealthy
        _submitReport();
        _applyVaultReport(
            vaults[0],
            INITIAL_VAULT_BALANCE,
            int256(INITIAL_VAULT_BALANCE),
            4 * INITIAL_VAULT_BALANCE,
            0
        );

        vm.expectEmit(address(vaultHub));
        emit IVaultHub.ForcedValidatorExitTriggered(vaults[0], pubkeys[0], address(adapter));

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
        assertEq(
            _countLogs(
                vm.getRecordedLogs(),
                address(vaultHub),
                IVaultHub.ForcedValidatorExitTriggered.selector
            ),
            exitingVaults.length,
            "ForcedValidatorExitTriggered count"
        );
    }

    // python: test_set_liability_shares_target_happy_path
    function testFork_SetsLiabilitySharesTargets() external {
        address factory =
            _deployArtifact("SetLiabilitySharesTargetInVaultHub", abi.encode(creator, adapter));

        assertEq(IVaultsAdapterFactory(factory).trustedCaller(), creator, "setup: trustedCaller");
        assertEq(
            IVaultsAdapterFactory(factory).vaultsAdapter(), address(adapter), "setup: vaultsAdapter"
        );

        _registerOnlyFactory(
            factory, abi.encodePacked(adapter, IVaultsAdapter.setLiabilitySharesTarget.selector)
        );

        uint256[] memory targets = new uint256[](2);
        targets[0] = FIRST_LIABILITY_TARGET;
        targets[1] = SECOND_LIABILITY_TARGET;

        bytes memory callData = abi.encode(vaults, targets);

        uint256 motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        // Each vault mints a multiple of its target, the excess becomes redemption shares
        _submitReport();

        uint256[] memory minted = new uint256[](2);
        for (uint256 i; i < vaults.length; ++i) {
            minted[i] = targets[i] * (i + 1);

            _applyVaultReport(vaults[i], INITIAL_VAULT_BALANCE, int256(INITIAL_VAULT_BALANCE), 0, 0);
            _mintShares(vaults[i], minted[i]);
        }

        _passMotionDuration();

        vm.expectEmit(address(vaultHub));
        emit IVaultHub.VaultRedemptionSharesUpdated(vaults[0], minted[0] - targets[0]);

        vm.expectEmit(address(vaultHub));
        emit IVaultHub.VaultRedemptionSharesUpdated(vaults[1], minted[1] - targets[1]);

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");
        assertEq(
            _countLogs(
                vm.getRecordedLogs(),
                address(vaultHub),
                IVaultHub.VaultRedemptionSharesUpdated.selector
            ),
            vaults.length,
            "VaultRedemptionSharesUpdated count"
        );
    }

    // python: test_socialize_bad_debt_happy_path
    function testFork_SocializesBadDebt() external {
        address factory =
            _deployArtifact("SocializeBadDebtInVaultHub", abi.encode(creator, adapter));

        _assertAdapterFactory(factory);

        _registerOnlyFactory(
            factory, abi.encodePacked(adapter, IVaultsAdapter.socializeBadDebt.selector)
        );

        address badDebtVault = vaults[0];
        address acceptor = vaults[1];
        address[] memory badDebtVaults = new address[](1);
        badDebtVaults[0] = badDebtVault;
        address[] memory acceptors = new address[](1);
        acceptors[0] = acceptor;
        uint256[] memory maxShares = new uint256[](1);
        maxShares[0] = MAX_SHARES_TO_SOCIALIZE;

        bytes memory callData = abi.encode(badDebtVaults, acceptors, maxShares);

        uint256 motionId = _createMotion(factory, creator, callData);

        assertEq(easyTrack.getMotions().length, 1, "motions after creation");

        // The donor mints against a healthy report
        _submitReport();
        _applyVaultReport(badDebtVault, INITIAL_VAULT_BALANCE, int256(INITIAL_VAULT_BALANCE), 0, 0);
        _mintShares(badDebtVault, 10 * MAX_SHARES_TO_SOCIALIZE);

        _passMotionDuration();

        // The acceptor stays healthy, the donor's value drops below its liability
        _submitReport();
        _applyVaultReport(acceptor, INITIAL_VAULT_BALANCE, int256(INITIAL_VAULT_BALANCE), 0, 0);
        _applyVaultReport(
            badDebtVault,
            10 * MAX_SHARES_TO_SOCIALIZE,
            int256(INITIAL_VAULT_BALANCE),
            0,
            INITIAL_VAULT_BALANCE
        );

        uint256 badLiabilityBefore = vaultHub.vaultRecord(badDebtVault).liabilityShares;
        uint256 acceptorLiabilityBefore = vaultHub.vaultRecord(acceptor).liabilityShares;

        vm.recordLogs();

        vm.prank(stranger);
        easyTrack.enactMotion(motionId, callData);

        assertEq(easyTrack.getMotions().length, 0, "motions after enactment");

        uint256 badLiabilityAfter = vaultHub.vaultRecord(badDebtVault).liabilityShares;
        uint256 acceptorLiabilityAfter = vaultHub.vaultRecord(acceptor).liabilityShares;
        assertEq(
            badLiabilityAfter + acceptorLiabilityAfter,
            badLiabilityBefore + acceptorLiabilityBefore,
            "total liability conserved"
        );
        assertGt(badLiabilityBefore, badLiabilityAfter, "donor liability decreased");

        Vm.Log memory log = _singleLog(
            vm.getRecordedLogs(), address(vaultHub), IVaultHub.BadDebtSocialized.selector
        );
        assertEq(address(uint160(uint256(log.topics[1]))), badDebtVault, "vaultDonor");
        assertEq(address(uint160(uint256(log.topics[2]))), acceptor, "vaultAcceptor");
        assertEq(
            abi.decode(log.data, (uint256)), badLiabilityBefore - badLiabilityAfter, "badDebtShares"
        );
    }

    /// @dev python: b"01" * 48. The 96 ASCII bytes "0101…", two keys of 48 bytes
    function _asciiPubkeys() private pure returns (bytes memory pubkeys) {
        pubkeys = new bytes(PUBKEYS_LENGTH);
        for (uint256 i; i < PUBKEYS_LENGTH; i += 2) {
            pubkeys[i] = "0";
            pubkeys[i + 1] = "1";
        }
    }

    /// @dev The factory trusts the creator and acts through the adapter, which trusts the creator
    ///      and takes the fresh executor's calls
    function _assertAdapterFactory(address factory) private view {
        assertEq(IVaultsAdapterFactory(factory).trustedCaller(), creator, "setup: trustedCaller");
        assertEq(
            IVaultsAdapterFactory(factory).vaultsAdapter(), address(adapter), "setup: vaultsAdapter"
        );
        assertEq(adapter.trustedCaller(), creator, "setup: adapter trustedCaller");
        assertEq(adapter.evmScriptExecutor(), evmScriptExecutor, "setup: adapter evmScriptExecutor");
    }
}
