// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../TrustedSender.sol";
import "../MotionsRegistry.sol";
import "../IFinance.sol";

contract TopUpRewardProgramEasyTrack is TrustedSender {
    constructor(
        address _motionsRegistry,
        address _trustedSender,
        address _finance,
        address _rewardToken
    ) TrustedSender(_trustedSender) {
        motionsRegistry = MotionsRegistry(_motionsRegistry);
        finance = IFinance(_finance);
        rewardToken = _rewardToken;
    }

    MotionsRegistry public motionsRegistry;

    address[] public rewardPrograms;
    IFinance public finance;
    address public rewardToken;

    mapping(address => uint256) private rewardProgramIndices;

    address public addRewardProgramEasyTrack;
    address public removeRewardProgramEasyTrack;

    function initialize(address _addRewardProgramEasyTrack, address _removeRewardProgramEasyTrack)
        external
    {
        require(
            addRewardProgramEasyTrack == address(0) && removeRewardProgramEasyTrack == address(0),
            "ALREADY_INITIALIZED"
        );
        addRewardProgramEasyTrack = _addRewardProgramEasyTrack;
        removeRewardProgramEasyTrack = _removeRewardProgramEasyTrack;
    }

    function createMotion(address[] memory _rewardPrograms, uint256[] memory _amounts)
        external
        onlyTrustedSender
        returns (uint256)
    {
        _validateMotionData(_rewardPrograms, _amounts);
        return motionsRegistry.createMotion(_encodeMotionData(_rewardPrograms, _amounts));
    }

    function cancelMotion(uint256 _motionId) external onlyTrustedSender {
        motionsRegistry.cancelMotion(_motionId);
    }

    function enactMotion(uint256 _motionId) external {
        bytes memory motionData = motionsRegistry.getMotionData(_motionId);
        (address[] memory _rewardPrograms, uint256[] memory _amounts) =
            _decodeMotionData(motionData);
        _validateMotionData(_rewardPrograms, _amounts);
        motionsRegistry.enactMotion(_motionId, _createEvmScript(_rewardPrograms, _amounts));
    }

    function isAllowed(address _rewardProgram) external view returns (bool) {
        return rewardProgramIndices[_rewardProgram] > 0;
    }

    function addRewardProgram(address _rewardProgram) external {
        require(msg.sender == addRewardProgramEasyTrack, "FORBIDDEN");
        require(rewardProgramIndices[_rewardProgram] == 0, "REWARD_PROGRAM_ALREADY_ADDED");

        rewardPrograms.push(_rewardProgram);
        rewardProgramIndices[_rewardProgram] = rewardPrograms.length;
    }

    function removeRewardProgram(address _rewardProgram) external {
        require(msg.sender == removeRewardProgramEasyTrack, "FORBIDDEN");
        require(rewardProgramIndices[_rewardProgram] > 0, "REWARD_PROGRAM_NOT_FOUND");

        uint256 index = rewardProgramIndices[_rewardProgram] - 1;
        uint256 lastIndex = rewardPrograms.length - 1;

        if (index != lastIndex) {
            address lastRewardProgram = rewardPrograms[lastIndex];
            rewardPrograms[index] = lastRewardProgram;
            rewardProgramIndices[lastRewardProgram] = index + 1;
        }

        rewardPrograms.pop();
        delete rewardProgramIndices[_rewardProgram];
    }

    function getRewardPrograms() external view returns (address[] memory) {
        return rewardPrograms;
    }

    function _validateMotionData(address[] memory _rewardPrograms, uint256[] memory _amounts)
        private
        view
    {
        require(_rewardPrograms.length == _amounts.length, "LENGTH_MISMATCH");
        require(_rewardPrograms.length > 0, "EMPTY_DATA");
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            require(_amounts[i] > 0, "ZERO_AMOUNT");
            require(rewardProgramIndices[_rewardPrograms[i]] > 0, "REWARD_PROGRAM_NOT_FOUND");
        }
    }

    function _encodeMotionData(address[] memory _rewardPrograms, uint256[] memory _amounts)
        private
        pure
        returns (bytes memory)
    {
        return abi.encode(_rewardPrograms, _amounts);
    }

    function _decodeMotionData(bytes memory _motionData)
        private
        pure
        returns (address[] memory _rewardPrograms, uint256[] memory _amounts)
    {
        (_rewardPrograms, _amounts) = abi.decode(_motionData, (address[], uint256[]));
    }

    function _createEvmScript(address[] memory _rewardPrograms, uint256[] memory _amounts)
        private
        view
        returns (bytes memory _evmScripts)
    {
        bytes[] memory _evmScriptsCalldata = new bytes[](_rewardPrograms.length);
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            _evmScriptsCalldata[i] = abi.encodeWithSelector(
                finance.newImmediatePayment.selector,
                rewardToken,
                _rewardPrograms[i],
                _amounts[i],
                "Reward program top up"
            );
        }
        _evmScripts = motionsRegistry.createEvmScript(address(finance), _evmScriptsCalldata);
    }
}
