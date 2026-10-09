// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {SubmitExitRequestHashesUtils} from "contracts/libraries/SubmitExitRequestHashesUtils.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";

/// @notice Ports of `utils/submit_exit_requests_test_helpers.py`
library ExitRequests {
    uint256 internal constant PUBKEY_SIZE = 48;
    uint256 internal constant MAX_REQUESTS = 200;
    uint256 internal constant DATA_FORMAT_LIST = 1;

    /// @dev python: make_test_bytes. `i` as 3 big-endian bytes, then `length - 3` copies of `i % 256`
    function makeTestBytes(uint256 i, uint256 length) internal pure returns (bytes memory result) {
        require(length >= 3, "Length must be at least 3 bytes");

        result = new bytes(length);

        bytes3 prefix = bytes3(uint24(i));
        result[0] = prefix[0];
        result[1] = prefix[1];
        result[2] = prefix[2];

        bytes1 filler = bytes1(uint8(i % 256));
        for (uint256 j = 3; j < length; ++j) {
            result[j] = filler;
        }
    }

    /// @dev `makeTestBytes` at the default pubkey length
    function makeTestBytes(uint256 i) internal pure returns (bytes memory) {
        return makeTestBytes(i, PUBKEY_SIZE);
    }

    /// @dev python: pubkeys[index] of submit_exit_hashes_factory_config. The key the registry stubs
    /// hold at `index`
    function pubkeyAt(uint256 index) internal pure returns (bytes memory) {
        return makeTestBytes(index + 1);
    }

    /// @dev python: b"".join(pubkeys). All MAX_REQUESTS keys, the `setSigningKeys` argument
    function concatenatedPubkeys() internal pure returns (bytes memory keys) {
        for (uint256 i; i < MAX_REQUESTS; ++i) {
            keys = abi.encodePacked(keys, pubkeyAt(i));
        }
    }

    /// @dev python: create_exit_request_data. 64 bytes per request: moduleId as 3 bytes, nodeOpId as
    /// 5, valIndex as 8, then the 48-byte pubkey
    function createExitRequestData(SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests)
        internal
        pure
        returns (bytes memory data)
    {
        for (uint256 i; i < requests.length; ++i) {
            SubmitExitRequestHashesUtils.ExitRequestInput memory request = requests[i];
            data = abi.encodePacked(
                data,
                bytes3(uint24(request.moduleId)),
                bytes5(uint40(request.nodeOpId)),
                bytes8(request.valIndex),
                request.valPubkey
            );
        }
    }

    /// @dev python: create_exit_requests_hashes. `keccak256(abi.encode(packed, dataFormat))`, with
    /// `abi.encode` and not `encodePacked`
    function createExitRequestsHashes(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests,
        uint256 dataFormat
    ) internal pure returns (bytes32) {
        return keccak256(abi.encode(createExitRequestData(requests), dataFormat));
    }

    /// @dev python: add_node_operator. Registers one more operator on the stub, seeds its signing
    /// keys and returns its id. The Python hardcodes `accounts[0]` as the reward address.
    function addNodeOperator(
        NodeOperatorsRegistryStub registry,
        bytes memory pubkey,
        address rewardAddress
    ) internal returns (uint256 nodeOpId) {
        registry.addNodeOperator("test_node_op_1", rewardAddress, 200, 400);
        nodeOpId = registry.getNodeOperatorsCount() - 1;

        registry.setSigningKeys(nodeOpId, pubkey);
    }
}
