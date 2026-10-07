// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {SimpleDvtScenarioBase} from "test/foundry/helpers/SimpleDvtScenarioBase.sol";
import {IACL} from "test/foundry/interfaces/External.sol";

/// @notice The deployed SimpleDVT node operator factories of `deployed-<chain>.json` in one
///         sequence: 36 clusters are added, three deactivated and reactivated, one renamed and
///         re-addressed, two keyed and vetted, two target-limited, one handed to a new manager.
///         A DAO vote then hands the `MANAGE_SIGNING_KEYS` permission manager to the Agent.
contract SimpleDvtLifecycleTest is SimpleDvtScenarioBase {
    uint256 internal constant CLUSTERS_COUNT = 36;

    /// @dev Indexes of the clusters the sequence singles out
    uint256 internal constant FIRST_DEACTIVATED = 2;
    uint256 internal constant LAST_DEACTIVATED = 4;
    uint256 internal constant OPERATOR_5 = 5;
    uint256 internal constant OPERATOR_6 = 6;

    string internal constant NEW_NAME = "New Name";
    address internal constant NEW_REWARD_ADDRESS = 0x000000000000000000000000000000000000dEaD;

    uint256 internal constant VETTED_LIMIT_5 = 4;
    uint256 internal constant VETTED_LIMIT_6 = 3;
    uint256 internal constant INCREASED_VETTED_LIMIT_5 = 6;

    uint256 internal constant TARGET_LIMIT_MODE_5 = 2;
    uint256 internal constant TARGET_LIMIT_5 = 1;
    uint256 internal constant TARGET_LIMIT_MODE_6 = 1;
    uint256 internal constant TARGET_LIMIT_6 = 10;

    // python: test_simple_dvt_scenario
    function testFork_SimpleDvtLifecycle() external {
        _enact(addNodeOperators, creator, _encodeAddClusters(CLUSTERS_COUNT));

        for (uint256 index; index < CLUSTERS_COUNT; ++index) {
            _assertClusterAdded(index);
        }

        _enact(deactivateNodeOperators, creator, _encodeDeactivatedManagers());

        for (uint256 index = FIRST_DEACTIVATED; index <= LAST_DEACTIVATED; ++index) {
            _assertClusterActive(index, false);
        }

        _enact(activateNodeOperators, creator, _encodeDeactivatedManagers());

        for (uint256 index = FIRST_DEACTIVATED; index <= LAST_DEACTIVATED; ++index) {
            _assertClusterActive(index, true);
        }

        _enact(setNodeOperatorNames, creator, _encodeSetName(_operatorId(OPERATOR_6), NEW_NAME));

        (, string memory name,,,,,) = simpleDvt.getNodeOperator(_operatorId(OPERATOR_6), true);
        assertEq(name, NEW_NAME, "name");

        _enact(
            setNodeOperatorRewardAddresses,
            creator,
            _encodeSetRewardAddress(_operatorId(OPERATOR_6), NEW_REWARD_ADDRESS)
        );

        (,, address rewardAddress,,,,) = simpleDvt.getNodeOperator(_operatorId(OPERATOR_6), true);
        assertEq(rewardAddress, NEW_REWARD_ADDRESS, "rewardAddress");

        // Six keys on operator 5 and three on operator 6, added by their managers
        _addSigningKeys(_operatorId(OPERATOR_5), _operatorAddress(OPERATOR_5));
        _addSigningKeys(_operatorId(OPERATOR_5), _operatorAddress(OPERATOR_5));
        _addSigningKeys(_operatorId(OPERATOR_6), _operatorAddress(OPERATOR_6));

        _enact(setVettedValidatorsLimits, creator, _encodeVettedLimits());

        assertEq(
            _totalVettedValidators(OPERATOR_5), VETTED_LIMIT_5, "operator 5 totalVettedValidators"
        );
        assertEq(
            _totalVettedValidators(OPERATOR_6), VETTED_LIMIT_6, "operator 6 totalVettedValidators"
        );

        // Three more keys on operator 5, then its manager raises its own limit
        _addSigningKeys(_operatorId(OPERATOR_5), _operatorAddress(OPERATOR_5));

        _enact(
            increaseVettedValidatorsLimit,
            _operatorAddress(OPERATOR_5),
            _encodeIncreaseVettedLimit(_operatorId(OPERATOR_5), INCREASED_VETTED_LIMIT_5)
        );

        assertEq(
            _totalVettedValidators(OPERATOR_5),
            INCREASED_VETTED_LIMIT_5,
            "operator 5 totalVettedValidators"
        );

        _enact(updateTargetValidatorLimits, creator, _encodeTargetLimits());

        (uint256 targetLimitMode5, uint256 targetValidatorsCount5,,,,,,) =
            simpleDvt.getNodeOperatorSummary(_operatorId(OPERATOR_5));
        (uint256 targetLimitMode6, uint256 targetValidatorsCount6,,,,,,) =
            simpleDvt.getNodeOperatorSummary(_operatorId(OPERATOR_6));
        assertEq(targetLimitMode5, TARGET_LIMIT_MODE_5, "operator 5 targetLimitMode");
        assertEq(targetValidatorsCount5, TARGET_LIMIT_5, "operator 5 targetValidatorsCount");
        assertEq(targetLimitMode6, TARGET_LIMIT_MODE_6, "operator 6 targetLimitMode");
        assertEq(targetValidatorsCount6, TARGET_LIMIT_6, "operator 6 targetValidatorsCount");

        _enact(
            changeNodeOperatorManagers,
            creator,
            _encodeChangeManager(_operatorId(OPERATOR_5), _operatorAddress(OPERATOR_5), stranger)
        );

        assertFalse(
            _canManageSigningKeys(_operatorAddress(OPERATOR_5), _operatorId(OPERATOR_5)),
            "old manager canPerform"
        );
        assertTrue(
            _canManageSigningKeys(stranger, _operatorId(OPERATOR_5)), "new manager canPerform"
        );

        // The executor, as the permission manager, hands the role to the Agent on the DAO's behalf
        _executeDaoScript(
            address(acl),
            abi.encodeCall(
                IACL.setPermissionManager, (config.agent, address(simpleDvt), MANAGE_SIGNING_KEYS)
            )
        );

        assertEq(
            acl.getPermissionManager(address(simpleDvt), MANAGE_SIGNING_KEYS),
            config.agent,
            "getPermissionManager"
        );
    }

    /// @dev Operators 2 to 4 with their managers, the input of the deactivation and the
    ///      reactivation
    function _encodeDeactivatedManagers() private view returns (bytes memory) {
        OperatorManagerInput[] memory inputs =
            new OperatorManagerInput[](LAST_DEACTIVATED - FIRST_DEACTIVATED + 1);
        for (uint256 i; i < inputs.length; ++i) {
            uint256 index = FIRST_DEACTIVATED + i;
            inputs[i] = OperatorManagerInput(_operatorId(index), _operatorAddress(index));
        }

        return abi.encode(inputs);
    }

    function _encodeVettedLimits() private view returns (bytes memory) {
        VettedValidatorsLimitInput[] memory inputs = new VettedValidatorsLimitInput[](2);
        inputs[0] = VettedValidatorsLimitInput(_operatorId(OPERATOR_5), VETTED_LIMIT_5);
        inputs[1] = VettedValidatorsLimitInput(_operatorId(OPERATOR_6), VETTED_LIMIT_6);

        return abi.encode(inputs);
    }

    function _encodeTargetLimits() private view returns (bytes memory) {
        TargetValidatorsLimit[] memory limits = new TargetValidatorsLimit[](2);
        limits[0] =
            TargetValidatorsLimit(_operatorId(OPERATOR_5), TARGET_LIMIT_MODE_5, TARGET_LIMIT_5);
        limits[1] =
            TargetValidatorsLimit(_operatorId(OPERATOR_6), TARGET_LIMIT_MODE_6, TARGET_LIMIT_6);

        return abi.encode(limits);
    }

    /// @dev The cluster's active flag and its manager's signing keys permission move together
    function _assertClusterActive(uint256 index, bool expected) private view {
        (bool active,,,,,,) = simpleDvt.getNodeOperator(_operatorId(index), true);

        assertEq(active, expected, string.concat(_clusterName(index), " active"));
        assertEq(
            _canManageSigningKeys(_operatorAddress(index), _operatorId(index)),
            expected,
            string.concat(_clusterName(index), " canPerform")
        );
    }

    function _totalVettedValidators(uint256 index)
        private
        view
        returns (uint64 totalVettedValidators)
    {
        (,,, totalVettedValidators,,,) = simpleDvt.getNodeOperator(_operatorId(index), false);
    }
}
