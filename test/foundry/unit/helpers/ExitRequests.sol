// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {SubmitExitRequestHashesUtils} from "contracts/libraries/SubmitExitRequestHashesUtils.sol";
import {NodeOperatorsRegistryStub} from "contracts/test/NodeOperatorsRegistryStub.sol";
import {Bytes} from "test/foundry/unit/helpers/Bytes.sol";

/// @notice Ports of `utils/submit_exit_requests_test_helpers.py`
library ExitRequests {
    uint256 internal constant PUBKEY_SIZE = 48;
    uint256 internal constant MAX_REQUESTS = 200;
    uint256 internal constant DATA_FORMAT_LIST = 1;

    /// @dev Deterministic test bytes: `i` as 3 big-endian bytes, then `length - 3` copies of
    /// `i % 256`
    function makeTestBytes(uint256 i, uint256 length) internal pure returns (bytes memory result) {
        require(length >= 3, "Length must be at least 3 bytes");

        bytes memory prefix = Bytes.toBytes(i, 3);
        bytes1 filler = bytes32(i)[31];

        result = new bytes(length);
        for (uint256 j; j < length; ++j) {
            result[j] = j < 3 ? prefix[j] : filler;
        }
    }

    /// @dev `makeTestBytes` at the default pubkey length
    function makeTestBytes(uint256 i) internal pure returns (bytes memory) {
        return makeTestBytes(i, PUBKEY_SIZE);
    }

    /// @dev The key the registry stubs hold at `index`
    function pubkeyAt(uint256 index) internal pure returns (bytes memory) {
        return makeTestBytes(index + 1);
    }

    /// @dev All MAX_REQUESTS keys, the `setSigningKeys` argument
    function concatenatedPubkeys() internal pure returns (bytes memory keys) {
        for (uint256 i; i < MAX_REQUESTS; ++i) {
            keys = abi.encodePacked(keys, pubkeyAt(i));
        }
    }

    /// @dev Packs the requests, 64 bytes each: moduleId as 3 bytes, nodeOpId as 5, valIndex as 8,
    /// then the 48-byte pubkey
    function createExitRequestData(SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests)
        internal
        pure
        returns (bytes memory data)
    {
        for (uint256 i; i < requests.length; ++i) {
            SubmitExitRequestHashesUtils.ExitRequestInput memory request = requests[i];
            data = bytes.concat(
                data,
                Bytes.toBytes(request.moduleId, 3),
                Bytes.toBytes(request.nodeOpId, 5),
                bytes8(request.valIndex),
                request.valPubkey
            );
        }
    }

    /// @dev The hash of the packed requests, `keccak256(abi.encode(packed, dataFormat))`, with
    /// `abi.encode` and not `encodePacked`
    function createExitRequestsHashes(
        SubmitExitRequestHashesUtils.ExitRequestInput[] memory requests,
        uint256 dataFormat
    ) internal pure returns (bytes32) {
        return keccak256(abi.encode(createExitRequestData(requests), dataFormat));
    }

    /// @dev Registers one more operator on the stub, seeds its signing keys and returns its id
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
