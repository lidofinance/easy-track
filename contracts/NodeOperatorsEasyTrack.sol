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

  uint256 private votingsCount;
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
}
