// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../TrustedSender.sol";
import "../MotionsRegistry.sol";
import "./TopUpRewardProgramEasyTrack.sol";

contract RemoveRewardProgramEasyTrack is TrustedSender {
    MotionsRegistry public motionsRegistry;
    TopUpRewardProgramEasyTrack public topUpRewardProgramEasyTrack;

    constructor(
        MotionsRegistry _motionsRegistry,
        address _trustedSender,
        TopUpRewardProgramEasyTrack _topUpRewardProgramEasyTrack
    ) TrustedSender(_trustedSender) {
        motionsRegistry = _motionsRegistry;
        topUpRewardProgramEasyTrack = _topUpRewardProgramEasyTrack;
    }

    function createMotion(address _rewardProgram) external onlyTrustedSender returns (uint256) {
        _validateMotionData(_rewardProgram);
        return motionsRegistry.createMotion(_encodeMotionData(_rewardProgram));
    }

    function cancelMotion(uint256 _motionId) external onlyTrustedSender {
        motionsRegistry.cancelMotion(_motionId);
    }

    function enactMotion(uint256 _motionId) external {
        bytes memory motionData = motionsRegistry.getMotionData(_motionId);
        address _rewardProgram = _decodeMotionData(motionData);
        _validateMotionData(_rewardProgram);
        topUpRewardProgramEasyTrack.removeRewardProgram(_rewardProgram);
        motionsRegistry.enactMotion(_motionId);
    }

    function _validateMotionData(address _rewardProgram) private view {
        require(topUpRewardProgramEasyTrack.isAllowed(_rewardProgram), "REWARD_PROGRAM_NOT_FOUND");
    }

    function _encodeMotionData(address _rewardProgram) private pure returns (bytes memory) {
        return abi.encode(_rewardProgram);
    }

    function _decodeMotionData(bytes memory _motionData) private pure returns (address) {
        return abi.decode(_motionData, (address));
    }
}
