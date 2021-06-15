// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

interface IForwardable {
    function forward(bytes memory _evmScript) external;
}

contract EvmScriptExecutor {
    bytes4 private constant SPEC_ID = hex"00000001";
    IForwardable public aragonAgent;

    constructor(address _aragonAgent) {
        aragonAgent = IForwardable(_aragonAgent);
    }

    function executeScript(bytes memory _evmScript) internal {
        aragonAgent.forward(_evmScript);
    }

    function createEvmScript(address _to, bytes memory _evmScriptCalldata)
        external
        pure
        returns (bytes memory)
    {
        return bytes.concat(SPEC_ID, _createEvmScript(_to, _evmScriptCalldata));
    }

    function createEvmScript(address _to, bytes[] memory _evmScriptCalldata)
        external
        pure
        returns (bytes memory _evmScript)
    {
        for (uint256 i = 0; i < _evmScriptCalldata.length; ++i) {
            _evmScript = bytes.concat(_evmScript, _createEvmScript(_to, _evmScriptCalldata[i]));
        }
        _evmScript = bytes.concat(SPEC_ID, _evmScript);
    }

    function createEvmScript(address[] memory _to, bytes[] memory _evmScriptCalldata)
        external
        pure
        returns (bytes memory _evmScript)
    {
        require(_to.length == _evmScriptCalldata.length, "LENGTH_MISMATCH");
        for (uint256 i = 0; i < _to.length; ++i) {
            _evmScript = bytes.concat(_evmScript, _createEvmScript(_to[i], _evmScriptCalldata[i]));
        }
        _evmScript = bytes.concat(SPEC_ID, _evmScript);
    }

    function _createEvmScript(address _to, bytes memory _evmScriptCalldata)
        private
        pure
        returns (bytes memory)
    {
        return
            bytes.concat(
                bytes20(_to),
                bytes4(uint32(_evmScriptCalldata.length)),
                _evmScriptCalldata
            );
    }
}
