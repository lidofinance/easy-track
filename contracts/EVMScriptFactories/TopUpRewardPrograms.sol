// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../TrustedCaller.sol";
import "../RewardProgramsRegistry.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

contract TopUpRewardPrograms is TrustedCaller, IEVMScriptFactory {
    constructor(
        address _trustedCaller,
        address _rewardProgramsRegistry,
        address _finance,
        address _rewardToken
    ) TrustedCaller(_trustedCaller) {
        finance = IFinance(_finance);
        rewardToken = _rewardToken;
        rewardProgramsRegistry = RewardProgramsRegistry(_rewardProgramsRegistry);
    }

    RewardProgramsRegistry public rewardProgramsRegistry;

    IFinance public finance;
    address public rewardToken;

    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory rewardPrograms, uint256[] memory amounts) =
            _decodeEVMScriptCallData(_evmScriptCallData);

        _validateMotionData(rewardPrograms, amounts);

        bytes[] memory evmScriptsCalldata = new bytes[](rewardPrograms.length);
        for (uint256 i = 0; i < rewardPrograms.length; ++i) {
            evmScriptsCalldata[i] = abi.encode(
                rewardToken,
                rewardPrograms[i],
                amounts[i],
                "Reward program top up"
            );
        }
        return
            EVMScriptCreator.createEVMScript(
                address(finance),
                finance.newImmediatePayment.selector,
                evmScriptsCalldata
            );
    }

    function _validateMotionData(address[] memory _rewardPrograms, uint256[] memory _amounts)
        private
        view
    {
        require(_rewardPrograms.length == _amounts.length, "LENGTH_MISMATCH");
        require(_rewardPrograms.length > 0, "EMPTY_DATA");
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            require(_amounts[i] > 0, "ZERO_AMOUNT");
            require(
                rewardProgramsRegistry.isRewardProgram(_rewardPrograms[i]),
                "REWARD_PROGRAM_NOT_ALLOWED"
            );
        }
    }

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory rewardPrograms, uint256[] memory amounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        internal
        pure
        returns (address[] memory rewardPrograms, uint256[] memory amounts)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }
}
