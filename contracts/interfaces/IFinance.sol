// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IFinance {
    function newImmediatePayment(
        address _token,
        address _receiver,
        uint256 _amount,
        string memory _reference
    ) external;
}
