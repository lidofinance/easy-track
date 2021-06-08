// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./EasyTrackExecutor.sol";
import "./TrustedAddress.sol";

interface IFinance {
    function newImmediatePayment(
        address _token,
        address _receiver,
        uint256 _amount,
        string memory _reference
    ) external;
}

contract TopUpRewardProgramEasyTrackExecutor is EasyTrackExecutor, TrustedAddress {
    address[] public rewardPrograms;
    IFinance public finance;
    address public rewardToken;

    mapping(address => uint256) private rewardProgramIndices;

    address public addRewardProgramEasyTrackExecutor;
    address public removeRewardProgramEasyTrackExecutor;

    constructor(
        address _easyTracksRegistry,
        address _allowedCaller,
        address _financeApp,
        address _rewardToken
    ) EasyTrackExecutor(_easyTracksRegistry) TrustedAddress(_allowedCaller) {
        finance = IFinance(_financeApp);
        rewardToken = _rewardToken;
    }

    function initialize(
        address _addRewardProgramEasyTrackExecutor,
        address _removeRewardProgramEasyTrackExecutor
    ) external {
        require(
            addRewardProgramEasyTrackExecutor == address(0) &&
                removeRewardProgramEasyTrackExecutor == address(0),
            "ALREADY_INITIALIZED"
        );
        addRewardProgramEasyTrackExecutor = _addRewardProgramEasyTrackExecutor;
        removeRewardProgramEasyTrackExecutor = _removeRewardProgramEasyTrackExecutor;
    }

    function addRewardProgram(address _rewardProgram) external {
        require(msg.sender == addRewardProgramEasyTrackExecutor, "FORBIDDEN");
        require(rewardProgramIndices[_rewardProgram] == 0, "REWARD_PROGRAM_ALREADY_ADDED");

        rewardPrograms.push(_rewardProgram);
        rewardProgramIndices[_rewardProgram] = rewardPrograms.length;
    }

    function removeRewardProgram(address _rewardProgram) external {
        require(msg.sender == removeRewardProgramEasyTrackExecutor, "FORBIDDEN");
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

    function isAllowed(address _rewardProgram) external view returns (bool) {
        return rewardProgramIndices[_rewardProgram] > 0;
    }

    function _beforeCreateMotionGuard(address _caller, bytes memory _data)
        internal
        view
        override
        onlyTrustedAddress(_caller)
    {
        (address[] memory _rewardPrograms, ) = _decodeMotionData(_data);
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            require(rewardProgramIndices[_rewardPrograms[i]] > 0, "REWARD_PROGRAM_NOT_FOUND");
        }
    }

    function _beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) internal view override onlyTrustedAddress(_caller) {}

    function _execute(bytes memory _motionData, bytes memory _enactData)
        internal
        view
        override
        returns (bytes memory _evmScript)
    {
        (address[] memory _rewardPrograms, uint256[] memory _amounts) =
            _decodeMotionData(_motionData);
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            require(rewardProgramIndices[_rewardPrograms[i]] > 0, "REWARD_PROGRAM_NOT_FOUND");
            bytes memory evmScriptCalldata =
                abi.encodeWithSelector(
                    finance.newImmediatePayment.selector,
                    rewardToken,
                    _rewardPrograms[i],
                    _amounts[i],
                    "Reward program top up"
                );
            _evmScript = bytes.concat(
                _evmScript,
                _createEvmScript(address(finance), evmScriptCalldata)
            );
        }
        _evmScript = bytes.concat(hex"00000001", _evmScript);
    }

    function _decodeMotionData(bytes memory _motionData)
        private
        pure
        returns (address[] memory _rewardPrograms, uint256[] memory _amounts)
    {
        (_rewardPrograms, _amounts) = abi.decode(_motionData, (address[], uint256[]));
        require(
            _rewardPrograms.length > 0 && _rewardPrograms.length == _amounts.length,
            "INVALID_LENGTH"
        );
    }

    function _createEvmScript(address _to, bytes memory evmScriptCalldata)
        private
        pure
        returns (bytes memory)
    {
        return
            bytes.concat(bytes20(_to), bytes4(uint32(evmScriptCalldata.length)), evmScriptCalldata);
    }
}
