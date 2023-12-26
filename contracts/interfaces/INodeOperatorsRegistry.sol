// SPDX-FileCopyrightText: 2023 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

/// @author bulbozaur
interface INodeOperatorsRegistry {
    function activateNodeOperator(uint256 _nodeOperatorId) external;

    function deactivateNodeOperator(uint256 _nodeOperatorId) external;

    function getNodeOperatorIsActive(uint256 _nodeOperatorId) external view returns (bool);

    function getNodeOperatorsCount() external view returns (uint256);

    function addNodeOperator(
        string memory _name,
        address _rewardAddress
    ) external returns (uint256 id);

    function MAX_NODE_OPERATOR_NAME_LENGTH() external view returns (uint256);

    function MAX_NODE_OPERATORS_COUNT() external view returns (uint256);

    function setNodeOperatorRewardAddress(uint256 _nodeOperatorId, address _rewardAddress) external;

    function setNodeOperatorName(uint256 _nodeOperatorId, string memory _name) external;

    function getNodeOperator(
        uint256 _id,
        bool _fullInfo
    )
        external
        view
        returns (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 stakingLimit,
            uint64 stoppedValidators,
            uint64 totalSigningKeys,
            uint64 usedSigningKeys
        );

    function canPerform(
        address _sender,
        bytes32 _role,
        uint256[] memory _params
    ) external view returns (bool);

    function setNodeOperatorStakingLimit(uint256 _id, uint64 _stakingLimit) external;

    function updateTargetValidatorsLimits(
        uint256 _nodeOperatorId,
        bool _isTargetLimitActive,
        uint256 _targetLimit
    ) external;
}
