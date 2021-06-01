// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

contract NodeOperatorsRegistryStub {
    string private constant ERROR_NODE_OPERATOR_NOT_FOUND = "NODE_OPERATOR_NOT_FOUND";
    uint256 public id;
    bool public active;
    address public rewardAddress;
    uint64 public stakingLimit;
    uint64 public totalSigningKeys;

    function getNodeOperator(uint256 _id, bool _fullInfo)
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
        require(id == _id, ERROR_NODE_OPERATOR_NOT_FOUND);
        _active = active;
        _rewardAddress = rewardAddress;
        _stakingLimit = stakingLimit;
        _totalSigningKeys = totalSigningKeys;
    }

    function setNodeOperatorStakingLimit(uint256 _id, uint64 _stakingLimit) external {
        require(id == _id, ERROR_NODE_OPERATOR_NOT_FOUND);
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
}
