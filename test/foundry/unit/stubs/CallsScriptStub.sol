// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {
    StorageSlot
} from "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/utils/StorageSlot.sol";
import {BytesUtils} from "contracts/libraries/BytesUtils.sol";

/// @notice Stands in for the deployed aragonOS v4.0.0 CallsScript that `EVMScriptExecutor`
/// delegatecalls into.
/// @dev Keeps what the executor depends on: the initialization-block guard, the call loop over
/// `target ‖ uint32(calldata.length) ‖ calldata` entries and the revert forwarding. The blacklist
/// is accepted and ignored, the executor always passes an empty one.
contract CallsScriptStub {
    using BytesUtils for bytes;

    /// @dev keccak256("aragonOS.initializable.initializationBlock")
    bytes32 internal constant INITIALIZATION_BLOCK_POSITION =
        0xebb05b386a8d34882b8711d156f463690983dc47815980fb82aeeff1aa43579e;

    /// @dev The first 4 bytes of a script hold the spec id
    uint256 internal constant SCRIPT_START_LOCATION = 4;
    uint256 internal constant ADDRESS_SIZE = 20;
    uint256 internal constant CALLDATA_LENGTH_SIZE = 4;

    event LogScriptCall(address indexed sender, address indexed src, address indexed dst);

    function execScript(
        bytes memory _script,
        bytes memory,
        address[] memory
    ) external returns (bytes memory) {
        uint256 initializationBlock = StorageSlot
            .getUint256Slot(INITIALIZATION_BLOCK_POSITION)
            .value;
        require(
            initializationBlock != 0 && block.number >= initializationBlock,
            "INIT_NOT_INITIALIZED"
        );

        uint256 location = SCRIPT_START_LOCATION;
        while (location < _script.length) {
            require(
                _script.length - location >= ADDRESS_SIZE + CALLDATA_LENGTH_SIZE,
                "EVMCALLS_INVALID_LENGTH"
            );

            address target = _script.addressAt(location);

            emit LogScriptCall(msg.sender, address(this), target);

            uint256 calldataLength = _script.uint32At(location + ADDRESS_SIZE);
            uint256 calldataStart = location + ADDRESS_SIZE + CALLDATA_LENGTH_SIZE;

            location = calldataStart + calldataLength;

            require(location <= _script.length, "EVMCALLS_INVALID_LENGTH");

            (bool success, bytes memory output) = target.call(
                _slice(_script, calldataStart, calldataLength)
            );

            if (!success) {
                _forwardRevert(output);
            }
        }

        return "";
    }

    function _slice(
        bytes memory data,
        uint256 start,
        uint256 length
    ) private pure returns (bytes memory result) {
        result = new bytes(length);

        for (uint256 i; i < length; ++i) {
            result[i] = data[start + i];
        }
    }

    /// @dev Re-raises the failed call's return data, or the Aragon reason when there is none
    function _forwardRevert(bytes memory output) private pure {
        if (output.length == 0) {
            revert("EVMCALLS_CALL_REVERTED");
        }

        assembly {
            revert(add(output, 32), mload(output))
        }
    }
}
