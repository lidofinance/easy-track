// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

/// @author psirex
/// @notice Helper contract with stub implementation of NodeOperatorsRegistry
contract NodeOperatorsRegistryStub {
    uint256 public id = 1;
    bool public active = true;
    address public rewardAddress;
    uint64 public stakingLimit = 200;
    uint64 public totalSigningKeys = 400;

    uint256 internal _nodeOperatorsCount = 1;
    mapping(uint256 => bytes[]) internal _signingKeys;

    constructor(address _rewardAddress) {
        rewardAddress = _rewardAddress;
    }

    function getNodeOperator(
        uint256 _id,
        bool _fullInfo
    )
        external
        view
        returns (
            bool _active,
            string memory _name,
            address _rewardAddress,
            uint64 _stakingLimit,
            uint64 _stoppedValidators,
            uint64 _totalSigningKeys,
            uint64 _usedSigningKeys
        )
    {
        _active = active;
        _rewardAddress = rewardAddress;
        _stakingLimit = stakingLimit;
        _totalSigningKeys = totalSigningKeys;
    }

    function setNodeOperatorStakingLimit(uint256 _id, uint64 _stakingLimit) external {
        stakingLimit = _stakingLimit;
    }

    function setId(uint256 _id) public {
        id = _id;
    }

    function setActive(bool _active) public {
        active = _active;
    }

    function setRewardAddress(address _rewardAddress) public {
        rewardAddress = _rewardAddress;
    }

    function setStakingLimit(uint64 _stakingLimit) public {
        stakingLimit = _stakingLimit;
    }

    function setTotalSigningKeys(uint64 _totalSigningKeys) public {
        totalSigningKeys = _totalSigningKeys;
    }

    function getNodeOperatorsCount() external view returns (uint256) {
        return _nodeOperatorsCount;
    }

    function getSigningKey(
        uint256 _nodeOperatorId,
        uint256 _index
    ) external view returns (bytes memory key, bytes memory depositSignature, bool used) {
        require(_nodeOperatorId < _nodeOperatorsCount, "Node operator ID out of range");
        require(_index < _signingKeys[_nodeOperatorId].length, "Index out of range");

        key = _signingKeys[_nodeOperatorId][_index];
        depositSignature = ""; // Stub implementation, no actual signature
        used = false; // Stub implementation, no actual usage tracking
    }

    /// @notice Sets the desired number of node operators. This is a stub function for testing purposes.
    function setDesiredNodeOperatorCount(uint256 _desiredCount) external {
        require(_desiredCount > 0, "Desired count must be greater than zero");
        _nodeOperatorsCount = _desiredCount;
    }

    function setSigningKey(uint256 _nodeOperatorId, bytes memory _key) external {
        // This is a stub implementation, so we don't care about the actual logic.
        // We want to ensure that the signing key can be set for testing purposes.

        require(_nodeOperatorId < _nodeOperatorsCount, "Node operator ID out of range");
        // Store the signing key
        _signingKeys[_nodeOperatorId].push(_key);
    }
}
