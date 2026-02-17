// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IMetaRegistry {
    struct SubNodeOperator {
        uint64 nodeOperatorId;
        uint16 share;
    }

    struct ExternalOperator {
        bytes data;
    }

    struct OperatorGroup {
        SubNodeOperator[] subNodeOperators;
        ExternalOperator[] externalOperators;
    }

    function NO_GROUP_ID() external view returns (uint256);

    function getOperatorGroupsCount() external view returns (uint256);

    function createOrUpdateOperatorGroup(
        uint256 groupId,
        OperatorGroup calldata groupInfo
    ) external;
}
