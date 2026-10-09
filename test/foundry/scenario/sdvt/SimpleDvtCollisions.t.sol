// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {SimpleDvtScenarioBase} from "test/foundry/helpers/SimpleDvtScenarioBase.sol";

/// @notice The deployed SimpleDVT node operator factories of `deployed-<chain>.json` with two
///         motions pending at once: the first enacts, the second then fails the factory's
///         re-validation at enactment. Each case builds on the state the previous one left, so
///         they run in one sequence. Operators are addressed by their table number, 1 to 4.
contract SimpleDvtCollisionsTest is SimpleDvtScenarioBase {
    struct PlannedMotion {
        address factory;
        address creator;
        bytes callData;
    }

    /// @dev The limits the vetting cases raise operator 1 to, one key at a time
    uint256 internal constant FIRST_VETTED_LIMIT = 1;
    uint256 internal constant SECOND_VETTED_LIMIT = 2;
    uint256 internal constant THIRD_VETTED_LIMIT = 3;

    function setUp() public override {
        super.setUp();

        // Mainnet deployed the increase factory but never registered it
        vm.skip(
            !easyTrack.isEVMScriptFactory(increaseVettedValidatorsLimit),
            "IncreaseVettedValidatorsLimit is not registered in Easy Track"
        );
    }

    // python: test_simple_dvt_scenario
    function testFork_RejectsCollidingMotionsAtEnactment() external {
        // 1. The same add twice: the second one sees a changed operator count
        _expectCollision(
            "NODE_OPERATORS_COUNT_MISMATCH",
            _addMotion(0, _tableName(1), _tableAddress(1), _tableAddress(1)),
            _addMotion(0, _tableName(1), _tableAddress(1), _tableAddress(1))
        );

        _enact(
            deactivateNodeOperators,
            creator,
            _encodeOperatorManager(_tableOperator(1), _tableAddress(1))
        );

        // 2. Reactivating operator 1 under manager 1, then adding operator 2 under manager 1
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE",
            _activateMotion(1, 1),
            _addMotion(1, _tableName(2), _tableAddress(2), _tableAddress(1))
        );

        // 3. Moving operator 1 to manager 2, then adding operator 2 under manager 2
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE",
            _changeManagerMotion(1, 1, 2),
            _addMotion(1, _tableName(2), _tableAddress(2), _tableAddress(2))
        );

        // 4. The same deactivation twice
        _expectCollision(
            "WRONG_OPERATOR_ACTIVE_STATE", _deactivateMotion(1, 2), _deactivateMotion(1, 2)
        );

        // 5. Adding operator 2 under manager 2, then reactivating operator 1 under manager 2
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE",
            _addMotion(1, _tableName(2), _tableAddress(2), _tableAddress(2)),
            _activateMotion(1, 2)
        );

        // 6. The same activation twice
        _expectCollision(
            "WRONG_OPERATOR_ACTIVE_STATE", _activateMotion(1, 1), _activateMotion(1, 1)
        );

        _enact(
            deactivateNodeOperators,
            creator,
            _encodeOperatorManager(_tableOperator(2), _tableAddress(2))
        );

        // 7. Moving operator 1 to manager 2, then reactivating operator 2 under manager 2
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE", _changeManagerMotion(1, 1, 2), _activateMotion(2, 2)
        );

        // 8. The same rename twice
        _expectCollision(
            "SAME_NAME", _setNameMotion(1, _tableName(3)), _setNameMotion(1, _tableName(3))
        );

        // 9. The same reward address change twice
        _expectCollision(
            "SAME_REWARD_ADDRESS", _setRewardAddressMotion(1, 3), _setRewardAddressMotion(1, 3)
        );

        // 10. Adding operator 3 under manager 3, then moving operator 1 to manager 3
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE",
            _addMotion(2, _tableName(1), _tableAddress(1), _tableAddress(3)),
            _changeManagerMotion(1, 2, 3)
        );

        // 11. Reactivating operator 2 under manager 1, then moving operator 1 to manager 1
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE", _activateMotion(2, 1), _changeManagerMotion(1, 2, 1)
        );

        // 12. The same manager change twice: the old manager has lost the role
        _expectCollision(
            "OLD_MANAGER_HAS_NO_ROLE", _changeManagerMotion(1, 2, 4), _changeManagerMotion(1, 2, 4)
        );

        // 13. Moving operator 1 to manager 2, then operator 2 to manager 2
        _expectCollision(
            "MANAGER_ALREADY_HAS_ROLE", _changeManagerMotion(1, 4, 2), _changeManagerMotion(2, 1, 2)
        );

        // Manager 2 keys operator 1 so its limit can be vetted
        _addSigningKeys(_tableOperator(1), _tableAddress(2));

        // 14. Vetting operator 1 to one key, then its manager raising the limit to one key
        _expectCollision(
            "STAKING_LIMIT_TOO_LOW",
            _setVettedLimitMotion(1, FIRST_VETTED_LIMIT),
            _increaseVettedLimitMotion(1, FIRST_VETTED_LIMIT, _tableAddress(2))
        );

        // 15. The same limit increase twice
        _expectCollision(
            "STAKING_LIMIT_TOO_LOW",
            _increaseVettedLimitMotion(1, SECOND_VETTED_LIMIT, _tableAddress(2)),
            _increaseVettedLimitMotion(1, SECOND_VETTED_LIMIT, _tableAddress(2))
        );

        // 16. Deactivating operator 1, then its former manager raising its limit
        _expectCollision(
            "CALLER_IS_NOT_NODE_OPERATOR_OR_MANAGER",
            _deactivateMotion(1, 2),
            _increaseVettedLimitMotion(1, THIRD_VETTED_LIMIT, _tableAddress(2))
        );
    }

    /// @dev Create both motions, enact the first, then the second fails its re-validation with
    ///      `reason` and its creator cancels it, keeping Easy Track below its motions limit
    function _expectCollision(
        string memory reason,
        PlannedMotion memory first,
        PlannedMotion memory second
    ) private {
        uint256 firstMotionId = _createMotion(first.factory, first.creator, first.callData);
        uint256 secondMotionId = _createMotion(second.factory, second.creator, second.callData);

        _passMotionDuration();

        vm.prank(stranger);
        easyTrack.enactMotion(firstMotionId, first.callData);

        vm.prank(stranger);
        vm.expectRevert(bytes(reason));
        easyTrack.enactMotion(secondMotionId, second.callData);

        vm.prank(second.creator);
        easyTrack.cancelMotion(secondMotionId);
    }

    // --- tables ---

    function _tableOperator(uint256 table) private view returns (uint256) {
        return _operatorId(table - 1);
    }

    /// @dev The table's address, its reward address and manager alike
    function _tableAddress(uint256 table) private pure returns (address) {
        return _operatorAddress(table - 1);
    }

    function _tableName(uint256 table) private pure returns (string memory) {
        return string.concat("Table ", vm.toString(table));
    }

    // --- planned motions ---

    /// @dev Add one operator on top of the `added` the scenario has added so far
    function _addMotion(uint256 added, string memory name, address rewardAddress, address manager)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            addNodeOperators,
            creator,
            _encodeAddNodeOperator(firstOperatorId + added, name, rewardAddress, manager)
        );
    }

    function _activateMotion(uint256 table, uint256 managerTable)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            activateNodeOperators,
            creator,
            _encodeOperatorManager(_tableOperator(table), _tableAddress(managerTable))
        );
    }

    function _deactivateMotion(uint256 table, uint256 managerTable)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            deactivateNodeOperators,
            creator,
            _encodeOperatorManager(_tableOperator(table), _tableAddress(managerTable))
        );
    }

    function _changeManagerMotion(uint256 table, uint256 oldManagerTable, uint256 newManagerTable)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            changeNodeOperatorManagers,
            creator,
            _encodeChangeManager(
                _tableOperator(table),
                _tableAddress(oldManagerTable),
                _tableAddress(newManagerTable)
            )
        );
    }

    function _setNameMotion(uint256 table, string memory name)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            setNodeOperatorNames, creator, _encodeSetName(_tableOperator(table), name)
        );
    }

    function _setRewardAddressMotion(uint256 table, uint256 addressTable)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            setNodeOperatorRewardAddresses,
            creator,
            _encodeSetRewardAddress(_tableOperator(table), _tableAddress(addressTable))
        );
    }

    function _setVettedLimitMotion(uint256 table, uint256 stakingLimit)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            setVettedValidatorsLimits,
            creator,
            _encodeSetVettedLimit(_tableOperator(table), stakingLimit)
        );
    }

    /// @dev The factory has no trusted caller, the operator's manager creates the motion
    function _increaseVettedLimitMotion(uint256 table, uint256 stakingLimit, address manager)
        private
        view
        returns (PlannedMotion memory)
    {
        return PlannedMotion(
            increaseVettedValidatorsLimit,
            manager,
            _encodeIncreaseVettedLimit(_tableOperator(table), stakingLimit)
        );
    }
}
