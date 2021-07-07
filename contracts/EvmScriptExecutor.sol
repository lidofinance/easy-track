// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.2.0/contracts/utils/StorageSlot.sol";

interface ICallsScript {
    function execScript(
        bytes memory _script,
        bytes memory,
        address[] memory _blacklist
    ) external returns (bytes memory);
}

contract EVMScriptExecutor {
    event ScriptExecuted(address indexed _caller, bytes _evmScript);

    // keccak256("aragonOS.initializable.initializationBlock")
    bytes32 internal constant INITIALIZATION_BLOCK_POSITION =
        0xebb05b386a8d34882b8711d156f463690983dc47815980fb82aeeff1aa43579e;

    address public immutable callsScript;
    address public immutable easyTrack;
    address public immutable voting;

    constructor(
        address _callsScript,
        address _easyTrack,
        address _voting
    ) {
        voting = _voting;
        easyTrack = _easyTrack;
        callsScript = _callsScript;
        StorageSlot.getUint256Slot(INITIALIZATION_BLOCK_POSITION).value = block.number;
    }

    function executeEVMScript(bytes memory _evmScript) external returns (bytes memory) {
        require(msg.sender == voting || msg.sender == easyTrack, "CALLER_IS_FORBIDDEN");
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
