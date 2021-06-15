// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../TrustedSender.sol";
import "../MotionsRegistry.sol";
import "../IFinance.sol";

contract LegoEasyTrack is TrustedSender {
    MotionsRegistry public motionsRegistry;
    IFinance public finance;
    address public legoProgram;

    constructor(
        MotionsRegistry _motionsRegistry,
        address _trustedSender,
        IFinance _finance,
        address _legoProgram
    ) TrustedSender(_trustedSender) {
        finance = _finance;
        motionsRegistry = _motionsRegistry;
        legoProgram = _legoProgram;
    }

    function createMotion(address[] memory _rewardTokens, uint256[] memory _amounts)
        external
        onlyTrustedSender
        returns (uint256)
    {
        _validateMotionData(_rewardTokens, _amounts);
        return motionsRegistry.createMotion(abi.encode(_rewardTokens, _amounts));
    }

    function enactMotion(uint256 _motionId) external {
        bytes memory motionData = motionsRegistry.getMotionData(_motionId);
        (address[] memory _rewardTokens, uint256[] memory _amounts) = _decodeMotionData(motionData);
        _validateMotionData(_rewardTokens, _amounts);

        motionsRegistry.enactMotion(_motionId, _createEvmScript(_rewardTokens, _amounts));
    }

    function cancelMotion(uint256 _motionId) external onlyTrustedSender {
        motionsRegistry.cancelMotion(_motionId);
    }

    function _createEvmScript(address[] memory _rewardTokens, uint256[] memory _amounts)
        private
        view
        returns (bytes memory)
    {
        bytes[] memory paymentsCallData = new bytes[](_rewardTokens.length);
        for (uint256 i = 0; i < _rewardTokens.length; ++i) {
            paymentsCallData[i] = abi.encodeWithSelector(
                finance.newImmediatePayment.selector,
                _rewardTokens[i],
                legoProgram,
                _amounts[i],
                "Lego Program Transfer"
            );
        }
        return motionsRegistry.createEvmScript(address(finance), paymentsCallData);
    }

    function _validateMotionData(address[] memory _rewardTokens, uint256[] memory _amounts)
        private
        pure
    {
        require(_rewardTokens.length == _amounts.length, "LENGTHS_MISMATCH");
        require(_rewardTokens.length > 0, "EMPTY_DATA");
        for (uint256 i = 0; i < _rewardTokens.length; ++i) {
            require(_amounts[i] > 0, "ZERO_AMOUNT");
        }
    }

    function _decodeMotionData(bytes memory _motionData)
        private
        pure
        returns (address[] memory, uint256[] memory)
    {
        return abi.decode(_motionData, (address[], uint256[]));
    }
}
