// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "OpenZeppelin/openzeppelin-solidity@4.1.0/contracts/access/Ownable.sol";

contract NodeOperatorsEasyTrack is Ownable {
  address private votingCreator;

  constructor(address _votingCreator) public {
    votingCreator = _votingCreator;
  }

  function getVotingCreator() public view returns (address) {
    return votingCreator;
  }

  function setVotingCreator(address _votingCreator) public onlyOwner {
    votingCreator = _votingCreator;
  }
}
