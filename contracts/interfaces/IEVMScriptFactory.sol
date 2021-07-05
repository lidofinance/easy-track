// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IEVMScriptFactory {
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        returns (bytes memory);
}
