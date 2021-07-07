// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

contract TrustedCaller {
    address public immutable trustedCaller;

    constructor(address _trustedCaller) {
        trustedCaller = _trustedCaller;
    }

    modifier onlyTrustedCaller(address _caller) {
        require(_caller == trustedCaller, "CALLER_IS_FORBIDDEN");
        _;
    }
}
