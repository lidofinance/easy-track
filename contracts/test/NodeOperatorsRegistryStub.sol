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

    struct NodeOperator {
        bool active;
        string name;
        address rewardAddress;
        uint64 stakingLimit;
        uint64 stoppedValidators;
        uint64 totalSigningKeys;
        uint64 usedSigningKeys;
    }

    uint256 internal _nodeOperatorsCount = 0;

    mapping(uint256 => NodeOperator) internal _nodeOperators;
    mapping(uint256 => bytes) internal _signingKeys;

    constructor(address _rewardAddress) {
        rewardAddress = _rewardAddress;
        _addNodeOperator("Test Node Operator", _rewardAddress, stakingLimit, totalSigningKeys);
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
        NodeOperator storage nodeOperator = _nodeOperators[_id];

        _active = nodeOperator.active;
        _name = nodeOperator.name;
        _rewardAddress = nodeOperator.rewardAddress;
        _stakingLimit = nodeOperator.stakingLimit;
        _stoppedValidators = nodeOperator.stoppedValidators;
        _totalSigningKeys = nodeOperator.totalSigningKeys;
        _usedSigningKeys = nodeOperator.usedSigningKeys;
    }

    function addNodeOperator(
        string memory _name,
        address _rewardAddress,
        uint64 _stakingLimit,
        uint64 _totalSigningKeys
    ) external returns (uint256) {
        return _addNodeOperator(_name, _rewardAddress, _stakingLimit, _totalSigningKeys);
    }

    function _addNodeOperator(
        string memory _name,
        address _rewardAddress,
        uint64 _stakingLimit,
        uint64 _totalSigningKeys
    ) internal returns (uint256) {
        _nodeOperators[_nodeOperatorsCount] = NodeOperator({
            active: true,
            name: _name,
            rewardAddress: _rewardAddress,
            stakingLimit: _stakingLimit,
            stoppedValidators: 0,
            totalSigningKeys: _totalSigningKeys,
            usedSigningKeys: 0
        });

        _nodeOperatorsCount++;

        return _nodeOperatorsCount;
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

    /// @notice Sets the desired number of node operators. This is a stub function for testing purposes.
    function setDesiredNodeOperatorCount(uint256 _desiredCount) external {
        _nodeOperatorsCount = uint40(_desiredCount);
    }

    /// @notice Returns the signing key for a given node operator and index.
    function getSigningKey(
        uint256 _nodeOperatorId,
        uint256 _index
    ) external view returns (bytes memory key, bytes memory depositSignature, bool used) {
        bytes memory allKeys = _signingKeys[_nodeOperatorId];

        key = new bytes(48);
        assembly {
            // src offset = allKeys + 32 (array header) + _index * 48
            let src := add(add(allKeys, 32), mul(_index, 48))
            let dest := add(key, 32)
            mstore(dest, mload(src))
            mstore(add(dest, 32), mload(add(src, 32)))
        }
        depositSignature = "";
        used = false;
    }

    /// @notice Sets the signing keys for a given node operator.
    /// @dev This function overwrites all existing keys for the specified node operator. It expects the keys to be concatenated to a single bytes array.
    ///      This is done to make it more efficient for testing purposes.
    function setSigningKeys(uint256 _nodeOperatorId, bytes memory keysConcat) external {
        // Overwrite all keys for this node operator
        _signingKeys[_nodeOperatorId] = keysConcat;
    }
}
