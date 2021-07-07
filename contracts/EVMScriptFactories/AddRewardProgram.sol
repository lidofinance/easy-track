// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../RewardProgramsRegistry.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

contract AddRewardProgram is TrustedCaller, IEVMScriptFactory {
    RewardProgramsRegistry public immutable rewardProgramsRegistry;

    constructor(address _trustedCaller, address _rewardProgramsRegistry)
        TrustedCaller(_trustedCaller)
    {
        rewardProgramsRegistry = RewardProgramsRegistry(_rewardProgramsRegistry);
    }

    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        require(
            !rewardProgramsRegistry.isRewardProgram(_decodeEVMScriptCallData(_evmScriptCallData)),
            "REWARD_PROGRAM_ALREADY_ADDED"
        );

        return
            EVMScriptCreator.createEVMScript(
                address(rewardProgramsRegistry),
                rewardProgramsRegistry.addRewardProgram.selector,
                _evmScriptCallData
            );
    }

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        internal
        pure
        returns (address)
    {
        return abi.decode(_evmScriptCallData, (address));
    }
}
