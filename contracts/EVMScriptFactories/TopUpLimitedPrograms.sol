// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../LimitedProgramsRegistry.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

/// @notice Creates EVMScript to check limits and top up balances
contract TopUpLimitedPrograms is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_LENGTH_MISMATCH = "LENGTH_MISMATCH";
    string private constant ERROR_EMPTY_DATA = "EMPTY_DATA";
    string private constant ERROR_ZERO_AMOUNT = "ZERO_AMOUNT";
    string private constant ERROR_REWARD_PROGRAM_NOT_ALLOWED = "REWARD_PROGRAM_NOT_ALLOWED";
    string private constant ERROR_SUM_EXCEEDS_LIMIT = "SUM_EXCEEDS_LIMIT";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of Aragon's Finance contract
    IFinance public immutable finance;

    /// @notice Address of RewardProgramsRegistry
    LimitedProgramsRegistry public immutable limitedProgramsRegistry;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _limitedProgramsRegistry,
        address _finance
    ) TrustedCaller(_trustedCaller) {
        finance = IFinance(_finance);
        limitedProgramsRegistry = LimitedProgramsRegistry(_limitedProgramsRegistry);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to top up balances of reward programs
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (address[] _rewardTokens, address[] _rewardPrograms, uint256[] _amounts) where
    /// _rewardTokens - addresses of ERC20 tokens (zero address for ETH) to transfer
    /// _rewardPrograms - addresses of reward programs to top up
    /// _amounts - corresponding amount of tokens to transfer
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory rewardTokens,
            address[] memory rewardPrograms,
            uint256[] memory amounts
        ) = _decodeEVMScriptCallData(_evmScriptCallData);
        _validateEVMScriptCallData(rewardTokens, rewardPrograms, amounts);

        bytes[] memory evmScriptsCalldata = new bytes[](rewardPrograms.length);
        uint256 sum = 0;
        for (uint256 i = 0; i < rewardPrograms.length; ++i) {
            evmScriptsCalldata[i] = abi.encode(
                rewardTokens[i],
                rewardPrograms[i],
                amounts[i],
                "Reward program top up"
            );
            sum += amounts[i];
        }

        _checkLimits(sum);

        bytes memory _evmScript_checkAndUpdateLimits = EVMScriptCreator.createEVMScript(
            address(this),
            this._checkAndUpdateLimits.selector,
            abi.encode(sum)
        );

        bytes memory _evmScript_newImmediatePayment = EVMScriptCreator.createEVMScript(
            address(finance),
            finance.newImmediatePayment.selector,
            evmScriptsCalldata
        );

        return
            EVMScriptCreator.concatScripts(
                _evmScript_checkAndUpdateLimits,
                _evmScript_newImmediatePayment
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (address[] memory _rewardTokens, address[] _rewardPrograms, uint256[] _amounts) where
    /// _rewardTokens - addresses of ERC20 tokens (zero address for ETH) to transfer
    /// _rewardPrograms - addresses of reward programs to top up
    /// _amounts - corresponding amount of tokens to transfer
    /// @return _rewardTokens Addresses of ERC20 tokens (zero address for ETH) to transfer
    /// @return _rewardPrograms Addresses of reward programs to top up
    /// @return _amounts Amounts of tokens to transfer
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            address[] memory _rewardTokens,
            address[] memory _rewardPrograms,
            uint256[] memory _amounts
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _validateEVMScriptCallData(
        address[] memory _rewardTokens,
        address[] memory _rewardPrograms,
        uint256[] memory _amounts
    ) private view {
        require(_rewardPrograms.length == _rewardTokens.length, ERROR_LENGTH_MISMATCH);
        require(_rewardTokens.length == _amounts.length, ERROR_LENGTH_MISMATCH);
        require(_amounts.length == _rewardPrograms.length, ERROR_LENGTH_MISMATCH);
        require(_rewardPrograms.length > 0, ERROR_EMPTY_DATA);
        for (uint256 i = 0; i < _rewardPrograms.length; ++i) {
            require(_amounts[i] > 0, ERROR_ZERO_AMOUNT);
            require(
                limitedProgramsRegistry.isRewardProgram(_rewardPrograms[i]),
                ERROR_REWARD_PROGRAM_NOT_ALLOWED
            );
        }
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            address[] memory _rewardTokens,
            address[] memory _rewardPrograms,
            uint256[] memory _amounts
        )
    {
        return abi.decode(_evmScriptCallData, (address[], address[], uint256[]));
    }

    function _checkLimits(uint256 _sum) private view {
        require(limitedProgramsRegistry.isUnderLimit(_sum), ERROR_SUM_EXCEEDS_LIMIT);
    }

    function _checkAndUpdateLimits(uint256 _paymentSum) external {
        limitedProgramsRegistry.checkAndUpdateLimits(_paymentSum);
    }
}
