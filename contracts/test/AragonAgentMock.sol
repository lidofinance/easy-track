// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

contract AragonAgentMock {
    bytes public data;
    bool public called;

    function forward(bytes memory _data) public {
        data = _data;
        called = true;
    }
}
