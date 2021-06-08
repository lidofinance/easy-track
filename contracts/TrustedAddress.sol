// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

contract TrustedAddress {
    address public trustedAddress;

    constructor(address _trustedAddress) {
        trustedAddress = _trustedAddress;
    }

    modifier onlyTrustedAddress(address _caller) {
        require(_caller == trustedAddress, "ADDRESS_NOT_TRUSTED");
        _;
    }
}
