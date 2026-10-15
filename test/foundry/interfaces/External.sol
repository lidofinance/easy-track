// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

// -----------------------------------------------------------------------------
// External contracts the factories interact with (Lido protocol + staking-modules).
//
// Declared here because `contracts/interfaces/` is pinned to solc 0.8.6 while this suite
// compiles with a modern solc/EVM, and because the tests need a state-construction
// surface the factories don't use, such as createNodeOperator, addValidatorKeysETH,
// obtainDepositData, resume and the bond-curve setup. Interface names and struct field
// order match the corresponding contracts.
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

/// @notice Lido Staking Router. `StakingModule` is truncated at `priorityExitShareThreshold`, the
///         last field this suite reads. Everything after it differs across StakingRouter versions:
///         mainnet ends the struct at `minDepositBlockDistance` with 13 fields, the reaudited/hoodi
///         one adds `withdrawalCredentialsType` + `validatorsBalanceGwei` for 15. Decoding only
///         this common prefix works against both, trailing return data is ignored.
interface IStakingRouter {
    /// @dev `getStakingModule` of an id the router has never registered
    error StakingModuleUnregistered();

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

/// @notice Lido locator, the root of the protocol contracts: the staking router, impersonated when
///         marking keys as deposited, Lido, the exit bus oracle and the vaults contracts.
interface ILidoLocator {
    function lido() external view returns (address);

    function stakingRouter() external view returns (address);

    function validatorsExitBusOracle() external view returns (address);

    function accountingOracle() external view returns (address);

    function vaultHub() external view returns (address);

    function vaultFactory() external view returns (address);

    function lazyOracle() external view returns (address);

    function operatorGrid() external view returns (address);
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
///         The events are declared for `expectEmit` and `.selector`. Their layout matches the
///         module.
interface IBaseModule {
    event GeneralDelayedPenaltySettled(uint256 indexed nodeOperatorId, uint256 amount);

    event ValidatorWithdrawn(
        uint256 indexed nodeOperatorId,
        uint256 keyIndex,
        uint256 exitBalance,
        uint256 slashingPenalty,
        bytes pubkey
    );

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

    function settleGeneralDelayedPenalty(
        uint256[] calldata nodeOperatorIds,
        uint256[] calldata bondLockNonces
    ) external;

    function reportValidatorSlashing(uint256 nodeOperatorId, uint256 keyIndex) external;

    function isValidatorSlashed(uint256 nodeOperatorId, uint256 keyIndex)
        external
        view
        returns (bool);

    function isValidatorWithdrawn(uint256 nodeOperatorId, uint256 keyIndex)
        external
        view
        returns (bool);

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

    function reportSlashedWithdrawnValidators(WithdrawnValidatorInfo[] calldata validatorInfos)
        external;
}

/// @notice Lido bond accounting.
interface IAccounting {
    function getLockedBond(uint256 nodeOperatorId) external view returns (uint256);

    function getBondLockNonce(uint256 nodeOperatorId) external view returns (uint256);

    function getBondAmountByKeysCount(uint256 keysCount, uint256 curveId)
        external
        view
        returns (uint256);

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

    function getExternalOperatorGroupId(ExternalOperator calldata op)
        external
        view
        returns (uint256);

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

    function isPairAllowed(uint256 sourceOperatorId, uint256 targetOperatorId)
        external
        view
        returns (bool);

    function getSubmitter(uint256 sourceOperatorId, uint256 targetOperatorId)
        external
        view
        returns (address);
}

/// @notice Legacy NodeOperatorsRegistry (consolidation source, external-operator module, SimpleDVT).
///         An Aragon app: `canPerform` evaluates the sender's ACL permission against `params`, the
///         node operator id for `MANAGE_SIGNING_KEYS`.
interface INodeOperatorsRegistry {
    function SET_NODE_OPERATOR_LIMIT_ROLE() external view returns (bytes32);

    function MANAGE_NODE_OPERATOR_ROLE() external view returns (bytes32);

    function getNodeOperatorsCount() external view returns (uint256);

    function addNodeOperator(string calldata name, address rewardAddress)
        external
        returns (uint256 id);

    function setNodeOperatorStakingLimit(uint256 nodeOperatorId, uint64 vettedSigningKeysCount)
        external;

    function getNodeOperator(uint256 id, bool fullInfo)
        external
        view
        returns (
            bool active,
            string memory name,
            address rewardAddress,
            uint64 totalVettedValidators,
            uint64 totalExitedValidators,
            uint64 totalAddedValidators,
            uint64 totalDepositedValidators
        );

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

    function addSigningKeysOperatorBH(
        uint256 nodeOperatorId,
        uint256 keysCount,
        bytes calldata publicKeys,
        bytes calldata signatures
    ) external;

    function addSigningKeys(
        uint256 nodeOperatorId,
        uint256 keysCount,
        bytes calldata publicKeys,
        bytes calldata signatures
    ) external;

    function getSigningKey(uint256 nodeOperatorId, uint256 index)
        external
        view
        returns (bytes memory key, bytes memory depositSignature, bool used);

    function getSigningKeys(uint256 nodeOperatorId, uint256 offset, uint256 limit)
        external
        view
        returns (bytes memory pubkeys, bytes memory signatures, bool[] memory used);

    function canPerform(address sender, bytes32 role, uint256[] calldata params)
        external
        view
        returns (bool);
}

/// @notice Aragon ACL of the DAO. `MANAGE_SIGNING_KEYS` on a registry is granted per operator with
///         a parameter, so the three-argument `hasPermission` reads a plain grant only. The
///         four-argument one evaluates the grant's parameters against `how`.
interface IACL {
    function hasPermission(address who, address where, bytes32 what) external view returns (bool);

    function hasPermission(address who, address where, bytes32 what, uint256[] calldata how)
        external
        view
        returns (bool);

    function getPermissionManager(address app, bytes32 role) external view returns (address);

    function getPermissionParamsLength(address entity, address app, bytes32 role)
        external
        view
        returns (uint256);

    function getPermissionParam(address entity, address app, bytes32 role, uint256 index)
        external
        view
        returns (uint8 id, uint8 op, uint240 value);

    function createPermission(address entity, address app, bytes32 role, address manager) external;

    function grantPermission(address entity, address app, bytes32 role) external;

    function grantPermissionP(address entity, address app, bytes32 role, uint256[] calldata params)
        external;

    function revokePermission(address entity, address app, bytes32 role) external;

    function setPermissionManager(address newManager, address app, bytes32 role) external;
}

/// @notice Any Aragon app of the DAO, the Agent included. Its kernel resolves the ACL.
interface IAragonApp {
    function kernel() external view returns (address);
}

/// @notice Aragon Kernel of the DAO.
interface IKernel {
    function acl() external view returns (address);
}

/// @notice Aragon Finance app, the payer `TopUpRewardPrograms` targets.
interface IFinance {
    function CREATE_PAYMENTS_ROLE() external view returns (bytes32);

    function newImmediatePayment(
        address _token,
        address _receiver,
        uint256 _amount,
        string calldata _reference
    ) external;
}

/// @notice LDO, the governance token. Its controller is the Aragon TokenManager.
interface IMiniMeToken {
    function balanceOf(address _owner) external view returns (uint256);

    function approve(address _spender, uint256 _amount) external returns (bool);

    function controller() external view returns (address);
}

/// @notice The Aragon Agent as the DAO vault Finance pays from: it takes deposits of ETH and
///         tokens and reports what it holds.
interface IAgent {
    function deposit(address _token, uint256 _value) external payable;

    function balance(address _token) external view returns (uint256);
}

/// @notice Any payout token: LDO, DAI and USDC on the fork.
interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
}

/// @notice The deployed BokkyPooBahsDateTimeContract, the calendar `LimitsChecker` computes its
///         periods with.
interface IBokkyPooBahsDateTimeContract {
    function timestampToDate(uint256 timestamp)
        external
        pure
        returns (uint256 year, uint256 month, uint256 day);

    function timestampFromDate(uint256 year, uint256 month, uint256 day)
        external
        pure
        returns (uint256 timestamp);

    function addMonths(uint256 timestamp, uint256 _months)
        external
        pure
        returns (uint256 newTimestamp);
}

/// @notice Lido, the target of `SetDepositsReserveTarget` and the stETH `TopUpLegoProgram` pays.
interface ILido {
    function getDepositsReserveTarget() external view returns (uint256);

    function setDepositsReserveTarget(uint256 _newDepositsReserveTarget) external;

    function submit(address _referral) external payable returns (uint256);

    function approve(address _spender, uint256 _amount) external returns (bool);

    function balanceOf(address _account) external view returns (uint256);

    function sharesOf(address _account) external view returns (uint256);
}

/// @notice The Validators Exit Bus Oracle: a motion submits the hash of a batch of exit requests,
///         then anyone delivers the batch against it and the oracle requests every exit.
interface IValidatorsExitBusOracle {
    /// @dev `ValidatorsExitBus.ExitRequestsData`
    struct ExitRequestsData {
        bytes data;
        uint256 dataFormat;
    }

    /// @dev `submitExitRequestsData` of a batch whose hash was not submitted
    error ExitHashNotSubmitted();

    event RequestsHashSubmitted(bytes32 exitRequestsHash);

    event ValidatorExitRequest(
        uint256 indexed stakingModuleId,
        uint256 indexed nodeOperatorId,
        uint256 indexed validatorIndex,
        bytes validatorPubkey,
        uint256 timestamp
    );

    function SUBMIT_REPORT_HASH_ROLE() external view returns (bytes32);

    function submitExitRequestsHash(bytes32 exitRequestsHash) external;

    function submitExitRequestsData(ExitRequestsData calldata request) external;
}

/// @notice The MEV-Boost relay allowed list, a Vyper contract its owner or manager edits. The
///         MEV-Boost factories target it with the executor as manager.
interface IMEVBoostRelayAllowedList {
    struct Relay {
        string uri;
        string operator;
        bool is_mandatory;
        string description;
    }

    function get_relays() external view returns (Relay[] memory);

    function get_relays_amount() external view returns (uint256);

    function get_relay_by_uri(string calldata relay_uri) external view returns (Relay memory);

    function get_owner() external view returns (address);

    function get_manager() external view returns (address);

    function set_manager(address manager) external;

    function add_relay(
        string calldata uri,
        string calldata operator,
        bool is_mandatory,
        string calldata description
    ) external;

    function remove_relay(string calldata uri) external;
}
