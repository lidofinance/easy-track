// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../interfaces/IEVMScriptFactory.sol";

contract EVMScriptFactoryStub is IEVMScriptFactory {
    bool public isCalled;
    address public creator;
    bytes public evmScriptCallData;
    bytes public evmScript;

    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        override
        returns (bytes memory)
    {
        creator = _creator;
        evmScriptCallData = _evmScriptCallData;
        return evmScript;
    }

    function setEVMScript(bytes memory _evmScript) external {
        evmScript = _evmScript;
    }
}
