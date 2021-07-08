// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../TrustedCaller.sol";
import "../interfaces/IFinance.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";

contract TopUpLegoProgram is TrustedCaller, IEVMScriptFactory {
    IFinance public immutable finance;
    address public immutable legoProgram;

    constructor(
        address _trustedCaller,
        IFinance _finance,
        address _legoProgram
    ) TrustedCaller(_trustedCaller) {
        finance = _finance;
        legoProgram = _legoProgram;
    }

    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (address[] memory rewardTokens, uint256[] memory amounts) =
            _decodeEVMScriptCallData(_evmScriptCallData);
        _validateMotionData(rewardTokens, amounts);

        bytes[] memory paymentsCallData = new bytes[](rewardTokens.length);
        for (uint256 i = 0; i < rewardTokens.length; ++i) {
            paymentsCallData[i] = abi.encode(
                rewardTokens[i],
                legoProgram,
                amounts[i],
                "Lego Program Transfer"
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                address(finance),
                finance.newImmediatePayment.selector,
                paymentsCallData
            );
    }

    function _validateMotionData(address[] memory _rewardTokens, uint256[] memory _amounts)
        private
        pure
    {
        require(_rewardTokens.length == _amounts.length, "LENGTH_MISMATCH");
        require(_rewardTokens.length > 0, "EMPTY_DATA");
        for (uint256 i = 0; i < _rewardTokens.length; ++i) {
            require(_amounts[i] > 0, "ZERO_AMOUNT");
        }
    }

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (address[] memory rewardTokens, uint256[] memory amounts)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        internal
        pure
        returns (address[] memory rewardTokens, uint256[] memory amounts)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[]));
    }
}
