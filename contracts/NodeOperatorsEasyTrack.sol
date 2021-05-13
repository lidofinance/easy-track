// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "OpenZeppelin/openzeppelin-solidity@4.1.0/contracts/access/Ownable.sol"; // solhint-disable-line

struct Voting {
    uint256 id;
    uint256 duration;
    uint256 startDate;
    uint256 snapshotBlock;
    uint256 objections; // sum of all balances who voted against
    uint256 objectionsThreshold;
	bool isEnacted;
	bool isCanceled;
    uint256[] nodeOperatorIds;
    uint256[] stakingLimits;
	mapping(address => bool) voters;
}

address constant NODE_OPERATORS_REGISTRY = 0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5;
address constant LDO_TOKEN = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32;

interface NodeOperatorsRegistry {
    function getNodeOperator(uint256 _id, bool _fullInfo) external view returns (
        bool active,
        string memory name,
        address rewardAddress,
        uint64 stakingLimit,
        uint64 stoppedValidators,
        uint64 totalSigningKeys,
        uint64 usedSigningKeys
    );
}

contract NodeOperatorsEasyTrack is Ownable {
    /**
     @dev Allowed address to create new votings
     */
    address private votingCreator;

    /**
     @dev Duration of the new votings in seconds
     */
    uint256 private votingDuration;

    /**
     @dev Total balance of governance tokens required to make voting rejected
     */
    uint256 private objectionsThreshold;

    /**
     @dev Store last votingId and total votings count
     */
    uint256 private votingsCount;

    /**
     @dev Store votings by id
     */
    mapping(uint256 => Voting) votings;

    constructor(
        address _votingCreator,
        uint256 _votingDuration,
        uint256 _objectionsThreshold
    ) public {
        votingCreator = _votingCreator;
        votingDuration = _votingDuration;
        objectionsThreshold = _objectionsThreshold;
    }

    /**
     @notice Returns duration of new created votings
     */
    function getVotingDuration() public view returns (uint256) {
        return votingDuration;
    }

    /**
     @notice Set duration of new created votings. Can be called only by the owner of contract.
     */
    function setVotingDuration(uint256 _votingDuration) public onlyOwner {
        votingDuration = _votingDuration;
    }

    /**
     @notice Returns address who allowed to create new votes
     */
    function getVotingCreator() public view returns (address) {
        return votingCreator;
    }

    /**
     @notice Set address who allowed to create new votes
     */
    function setVotingCreator(address _votingCreator) public onlyOwner {
        votingCreator = _votingCreator;
    }

    /**
     @notice Returns total balance of governance tokens required to make voting rejected
     */
    function getObjectionsThreshold() public view returns (uint256) {
        return objectionsThreshold;
    }

    /**
     @notice Set total balance of governance tokens required to make voting rejected
     */
    function setObjectionsThreshold(uint256 _objectionsThreshold) public onlyOwner {
        objectionsThreshold = _objectionsThreshold;
    }

    /**
     @notice Creates new vote to change node operator staking limit
     */
    function createVoting(
        uint256 _nodeOperatorId,
        uint256 _stakingLimit
    ) public onlyVotingCreator returns (uint256 votingId) {

        validateNodeOperator(_nodeOperatorId);

        votingId = ++votingsCount;
        Voting storage v = votings[votingId];
        v.id = votingId;
        v.duration = votingDuration;
        v.startDate = block.timestamp;
        v.snapshotBlock = block.number;
        v.objectionsThreshold = objectionsThreshold;
        v.nodeOperatorIds = [_nodeOperatorId];
        v.stakingLimits = [_stakingLimit];
    }

    /**
     @notice Returns voting info by _votingId
     */
    function getVoting(uint256 _votingId) public view votingExists(_votingId) returns (
        uint256 id,
        uint256 duration,
        uint256 startDate,
        uint256 snapshotBlock,
        uint256 objections,
        uint256 _objectionsThreshold,
        bool isEnacted,
        bool isCanceled,
        uint256[] memory nodeOperatorIds,
        uint256[] memory stakingLimits
    ) {
        Voting storage v = votings[_votingId];
        id = v.id;
        duration = v.duration;
        startDate = v.startDate;
        snapshotBlock = v.snapshotBlock;
        objections = v.objections;
        _objectionsThreshold = v.objectionsThreshold;
        isEnacted = v.isEnacted;
        isCanceled = v.isCanceled;
        nodeOperatorIds = v.nodeOperatorIds;
        stakingLimits = v.stakingLimits;
    }

    modifier onlyVotingCreator {
        require(msg.sender == votingCreator, "Caller is not the voting creator");
        _;
    }

    modifier votingExists(uint256 _votingId) {
        require(_votingId <= votingsCount, "Voting not found");
        _;
    }

    /**
     @notice Check that validator with id exists and not disabled
     @dev Check for existence contained in `getNodeOperator` method of NodeOperatorsRegistry
     */
    function validateNodeOperator(uint256 _nodeOperatorId) internal {
        NodeOperatorsRegistry registry = NodeOperatorsRegistry(NODE_OPERATORS_REGISTRY);
        (bool active,,,,,,) = registry.getNodeOperator(_nodeOperatorId, false);
        require(active, "Operator disabled");
    }
}
