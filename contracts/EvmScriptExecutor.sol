// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./TrustedCaller.sol";

interface ICallsScript {
    function execScript(
        bytes memory _script,
        bytes memory,
        address[] memory _blacklist
    ) external returns (bytes memory);
}

library UnstructuredStorageSlim {
    function setStorageUint256(bytes32 position, uint256 data) internal {
        assembly {
            sstore(position, data)
        }
    }
}

contract EVMScriptExecutor is TrustedCaller {
    using UnstructuredStorageSlim for bytes32;

    event ScriptExecuted(address indexed _caller, bytes _evmScript);

    // keccak256("aragonOS.initializable.initializationBlock")
    bytes32 internal constant INITIALIZATION_BLOCK_POSITION =
        0xebb05b386a8d34882b8711d156f463690983dc47815980fb82aeeff1aa43579e;

    address public callsScript;

    constructor(address _callsScript, address _allowedCaller) TrustedCaller(_allowedCaller) {
        INITIALIZATION_BLOCK_POSITION.setStorageUint256(block.number);
        callsScript = _callsScript;
    }

    function executeEVMScript(bytes memory _evmScript)
        external
        onlyTrustedCaller(msg.sender)
        returns (bytes memory)
    {
        bytes memory execScriptCallData =
            abi.encodeWithSelector(
                ICallsScript.execScript.selector,
                _evmScript,
                new bytes(0),
                new address[](0)
            );
        (bool success, bytes memory output) = callsScript.delegatecall(execScriptCallData);
        if (!success) {
            assembly {
                let ptr := mload(0x40)
                let size := returndatasize()
                returndatacopy(ptr, 0, size)
                revert(ptr, size)
            }
        }
        emit ScriptExecuted(msg.sender, _evmScript);
        return output;
    }
}
