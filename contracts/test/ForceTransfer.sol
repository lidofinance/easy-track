// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;  

contract ForceTransfer {
    function transfer(address to) external payable {
        selfdestruct(payable(to));
    }
}
