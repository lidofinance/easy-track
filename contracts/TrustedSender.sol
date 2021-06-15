// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

contract TrustedSender {
    address public trustedSender;

    constructor(address _trustedSender) {
        trustedSender = _trustedSender;
    }

    modifier onlyTrustedSender {
        require(msg.sender == trustedSender, "SENDER_NOT_TRUSTED");
        _;
    }
}
