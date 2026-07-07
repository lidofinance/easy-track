// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// External contracts the factories interact with (Lido protocol + staking-modules).
//
// Re-declared here (not imported from `contracts/interfaces/`) because those are
// pinned to solc 0.8.6 and this suite compiles with a modern solc/EVM; and because
// the tests need a state-construction surface (createNodeOperator, addValidatorKeysETH,
// obtainDepositData, resume, bond-curve setup, ...) the factories don't use. Interface
// names and struct field order match the corresponding contracts.
// -----------------------------------------------------------------------------

/// @notice OZ AccessControlEnumerable surface (Lido protocol contracts use it).
interface IAccessControlEnumerable {
    function hasRole(bytes32 role, address account) external view returns (bool);

    function getRoleAdmin(bytes32 role) external view returns (bytes32);

    function getRoleMember(bytes32 role, uint256 index) external view returns (address);

    function getRoleMemberCount(bytes32 role) external view returns (uint256);

    function grantRole(bytes32 role, address account) external;

    function revokeRole(bytes32 role, address account) external;
}

/// @notice Lido Staking Router. `StakingModule` is truncated at `priorityExitShareThreshold`
///         (the last field this suite reads): everything after it differs across StakingRouter
///         versions — mainnet ends the struct at `minDepositBlockDistance` (13 fields), the
///         reaudited/hoodi one adds `withdrawalCredentialsType` + `validatorsBalanceGwei` (15).
///         Decoding only this common prefix works against both (trailing return data is ignored).
interface IStakingRouter {
    struct StakingModule {
        uint24 id;
        address stakingModuleAddress;
        uint16 stakingModuleFee;
        uint16 treasuryFee;
        uint16 stakeShareLimit;
        uint8 status;
        string name;
        uint64 lastDepositAt;
        uint256 lastDepositBlock;
        uint256 exitedValidatorsCount;
        uint16 priorityExitShareThreshold;
    }

    function getStakingModule(uint256 _stakingModuleId) external view returns (StakingModule memory);

    function updateModuleShares(
        uint256 _stakingModuleId,
        uint16 _newStakeShareLimit,
        uint16 _newPriorityExitShareThreshold
    ) external;
}

/// @notice Lido locator — resolves the staking router (impersonated when marking keys as deposited).
interface ILidoLocator {
    function stakingRouter() external view returns (address);
}

/// @notice CSM `WithdrawnValidatorInfo` (field order per the module contract).
struct WithdrawnValidatorInfo {
    uint256 nodeOperatorId;
    uint256 keyIndex;
    uint256 exitBalance;
    uint256 slashingPenalty;
    bool isSlashed;
}

/// @notice Node operator management properties (module `createNodeOperator` input).
struct NodeOperatorManagementProperties {
    address managerAddress;
    address rewardAddress;
    bool extendedManagerPermissions;
}

/// @notice Shared surface of the CSM-like modules (CSModule & CuratedModule) used here.
///         Includes the state-construction methods the tests need (not just the factory reads).
interface IBaseModule {
    function ACCOUNTING() external view returns (address);

    function LIDO_LOCATOR() external view returns (address);

    function META_REGISTRY() external view returns (address); // curated modules only

    function getNodeOperatorsCount() external view returns (uint256);

    function getNodeOperatorIsActive(uint256 nodeOperatorId) external view returns (bool);

    function isPaused() external view returns (bool);

    function resume() external;

    // Deterministic state construction (create operator, add keys, mark deposited).
    function createNodeOperator(
        address from,
        NodeOperatorManagementProperties calldata props,
        address referrer
    ) external returns (uint256 nodeOperatorId);

    function addValidatorKeysETH(
        address from,
        uint256 nodeOperatorId,
        uint256 keysCount,
        bytes calldata publicKeys,
        bytes calldata signatures
    ) external payable;

    function obtainDepositData(uint256 depositsCount, bytes calldata depositCalldata)
        external
        returns (bytes memory publicKeys, bytes memory signatures);

    function batchDepositInfoUpdate(uint256 batchSize) external returns (uint256 operatorsLeft);

    function getStakingModuleSummary()
        external
        view
        returns (
            uint256 totalExitedValidators,
            uint256 totalDepositedValidators,
            uint256 depositableValidatorsCount
        );

    // Precondition setup + enacted calls.
    function reportGeneralDelayedPenalty(
        uint256 nodeOperatorId,
        bytes32 id,
        uint256 amount,
        string calldata description
    ) external;

    function reportValidatorSlashing(uint256 nodeOperatorId, uint256 keyIndex) external;

    function isValidatorSlashed(uint256 nodeOperatorId, uint256 keyIndex) external view returns (bool);

    function isValidatorWithdrawn(uint256 nodeOperatorId, uint256 keyIndex) external view returns (bool);

    function getNodeOperatorSummary(uint256 nodeOperatorId)
        external
        view
        returns (
            uint256 targetLimitMode,
            uint256 targetValidatorsCount,
            uint256 stuckValidatorsCount,
            uint256 refundedValidatorsCount,
            uint256 stuckPenaltyEndTimestamp,
            uint256 totalExitedValidators,
            uint256 totalDepositedValidators,
            uint256 depositableValidatorsCount
        );

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos) external;
}

/// @notice Lido bond accounting.
interface IAccounting {
    function getLockedBond(uint256 nodeOperatorId) external view returns (uint256);

    function getBondLockNonce(uint256 nodeOperatorId) external view returns (uint256);

    function getBondAmountByKeysCount(uint256 keysCount, uint256 curveId) external view returns (uint256);

    function getBondCurveId(uint256 nodeOperatorId) external view returns (uint256);
}

/// @notice MetaRegistry operator groups (struct field order matches the contract).
interface IMetaRegistry {
    struct SubNodeOperator {
        uint64 nodeOperatorId;
        uint16 share;
    }

    struct ExternalOperator {
        bytes data;
    }

    struct OperatorGroup {
        string name;
        SubNodeOperator[] subNodeOperators;
        ExternalOperator[] externalOperators;
    }

    function NO_GROUP_ID() external view returns (uint256);

    function getOperatorGroupsCount() external view returns (uint256);

    function getOperatorGroup(uint256 groupId) external view returns (OperatorGroup memory);

    function getNodeOperatorGroupId(uint256 nodeOperatorId) external view returns (uint256);

    function getExternalOperatorGroupId(ExternalOperator calldata op) external view returns (uint256);

    function createOrUpdateOperatorGroup(uint256 groupId, OperatorGroup calldata groupInfo) external;

    // Deterministic setup surface (make a freshly-created curated operator depositable).
    function getBondCurveWeight(uint256 curveId) external view returns (uint256);

    function setBondCurveWeight(uint256 curveId, uint256 weight) external;
}

/// @notice Merkle gate guarding node-operator creation (e.g. CSM VettedGate / CuratedGate).
interface IMerkleGate {
    function treeRoot() external view returns (bytes32);

    function treeCid() external view returns (string memory);

    function setTreeParams(bytes32 _treeRoot, string calldata _treeCid) external;
}

/// @notice Consolidation migrator targeted by `AllowConsolidationPair`.
interface IConsolidationMigrator {
    function sourceModuleId() external view returns (uint256);

    function targetModuleId() external view returns (uint256);

    function getStakingRouter() external view returns (address);

    function isPairAllowed(uint256 sourceOperatorId, uint256 targetOperatorId) external view returns (bool);
}

/// @notice Legacy curated NodeOperatorsRegistry (consolidation source / external-operator module).
interface INodeOperatorsRegistry {
    function getNodeOperatorsCount() external view returns (uint256);

    function addNodeOperator(string calldata name, address rewardAddress) external returns (uint256 id);

    function getNodeOperator(uint256 id, bool fullInfo)
        external
        view
        returns (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 stakingLimit,
            uint64 stoppedValidators,
            uint64 totalSigningKeys,
            uint64 usedSigningKeys
        );
}
