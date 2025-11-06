// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

contract MockERC20 {

    uint8 public decimals;

    constructor(uint8 _decimals) {
        decimals = _decimals;
    }
}