// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>

// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import "./TrustedAddress.sol";
import "./EasyTrackExecutor.sol";

interface IFinance {
    function newImmediatePayment(
        address _token,
        address _receiver,
        uint256 _amount,
        string memory _reference
    ) external;
}

contract LegoEasyTrackExecutor is EasyTrackExecutor, TrustedAddress {
    address public legoProgram;
    address[3] public tokens;
    IFinance public finance;

    constructor(
        address _easyTracksRegistry,
        address _allowedCaller,
        address _finance,
        address _legoProgram,
        address _ldoToken,
        address _stEthToken
    ) EasyTrackExecutor(_easyTracksRegistry) TrustedAddress(_allowedCaller) {
        legoProgram = _legoProgram;
        finance = IFinance(_finance);
        tokens[0] = _ldoToken;
        tokens[1] = _stEthToken;
        tokens[2] = address(0);
    }

    function _beforeCreateMotionGuard(address _caller, bytes memory _data)
        internal
        view
        override
        onlyTrustedAddress(_caller)
    {
        (uint256 _ldoAmount, uint256 _stethAmount, uint256 _ethAmount) = _decodeMotionData(_data);
        require(_ldoAmount > 0 || _stethAmount > 0 || _ethAmount > 0, "ALL_AMOUNTS_ZERO");
    }

    function _beforeCancelMotionGuard(
        address _caller,
        bytes memory _motionData,
        bytes memory _cancelData
    ) internal view override onlyTrustedAddress(_caller) {}

    function _execute(bytes memory _motionData, bytes memory _enactData)
        internal
        override
        returns (bytes memory _evmScript)
    {
        (uint256 _ldoAmount, uint256 _stethAmount, uint256 _ethAmount) =
            _decodeMotionData(_motionData);
        require(_ldoAmount > 0 || _stethAmount > 0 || _ethAmount > 0, "ALL_AMOUNTS_ZERO");

        _evmScript = hex"00000001";
        if (_ldoAmount > 0) {
            _evmScript = bytes.concat(
                _evmScript,
                _createEvmScript(_encodeImmediatePaymentCallData(tokens[0], _ldoAmount))
            );
        }
        if (_stethAmount > 0) {
            _evmScript = bytes.concat(
                _evmScript,
                _createEvmScript(_encodeImmediatePaymentCallData(tokens[1], _stethAmount))
            );
        }
        if (_ethAmount > 0) {
            _evmScript = bytes.concat(
                _evmScript,
                _createEvmScript(_encodeImmediatePaymentCallData(tokens[2], _ethAmount))
            );
        }
    }

    function _decodeMotionData(bytes memory _motionData)
        private
        pure
        returns (
            uint256 _ldoAmount,
            uint256 _stethAmount,
            uint256 _ethAmount
        )
    {
        (_ldoAmount, _stethAmount, _ethAmount) = abi.decode(
            _motionData,
            (uint256, uint256, uint256)
        );
    }

    function _encodeImmediatePaymentCallData(address _rewardToken, uint256 _amount)
        private
        view
        returns (bytes memory)
    {
        return
            abi.encodeWithSelector(
                finance.newImmediatePayment.selector,
                _rewardToken,
                legoProgram,
                _amount,
                "Lego Program Transfer"
            );
    }

    function _createEvmScript(bytes memory evmScriptCalldata) private view returns (bytes memory) {
        return
            bytes.concat(
                bytes20(address(finance)),
                bytes4(uint32(evmScriptCalldata.length)),
                evmScriptCalldata
            );
    }
}
