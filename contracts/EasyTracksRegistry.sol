// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IForwardable {
    function forward(bytes memory _evmScript) external;
}

contract EasyTracksRegistry is Ownable {
    /**
     @dev upper bound for objectionsThreshold value.
     Stored in basis points (1% = 100)
     */
    uint64 private constant MAX_OBJECTIONS_THRESHOLD = 500;

    /**
     @dev lower bound for motionDuration value
     */
    uint64 private constant MIN_MOTION_DURATION = 48 hours;

    /**
     @dev Aragon agent where evm script will be forwarded to
     */
    IForwardable private aragonAgent;

    /**
     @dev Duration of the new motions in seconds
     */
    uint64 private motionDuration = 48 hours;

    /**
     @dev Percent of governance tokens required to reject a proposal
     values stored in basis points (1% = 100).
     Default value is 0.5%
     */
    uint64 private objectionsThreshold = 50;

    constructor(address _aragonAgent) {
        aragonAgent = IForwardable(_aragonAgent);
    }

    /**
     @notice Returns duration of new created motions
     */
    function getMotionDuration() public view returns (uint256) {
        return motionDuration;
    }

    /**
     @notice Percent of governance tokens required to reject a proposal in basis points (1% = 100)
     */
    function getObjectionsThreshold() public view returns (uint256) {
        return objectionsThreshold;
    }

    function getAragonAgent() public view returns (address) {
        return address(aragonAgent);
    }
}
