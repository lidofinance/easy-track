// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

struct TierParams {
    uint256 shareLimit;
    uint256 reserveRatioBP;
    uint256 forcedRebalanceThresholdBP;
    uint256 treasuryFeeBP;
}

contract OperatorGridStub is AccessControl {

    bytes32 public constant REGISTRY_ROLE = keccak256("vaults.OperatorsGrid.Registry");

    /// @notice Default group address
    uint256 public constant DEFAULT_TIER_ID = 0;
    address public constant DEFAULT_TIER_OPERATOR = address(uint160(type(uint160).max));

    /// @dev basis points base
    uint256 internal constant TOTAL_BASIS_POINTS = 100_00;

    // -----------------------------
    //            STRUCTS
    // -----------------------------
    struct Group {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint128[] tierIds;
    }

    struct Tier {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 treasuryFeeBP;
    }

    struct VaultTier {
        uint128 currentTierId;
        uint128 requestedTierId;
    }

    struct ERC7201Storage {
        Tier[] tiers;
        mapping(address => VaultTier) vaultTier;
        mapping(address => Group) groups;
        address[] nodeOperators;
    }

    /**
     * @notice Storage offset slot for ERC-7201 namespace
     *         The storage namespace is used to prevent upgrade collisions
     *         keccak256(abi.encode(uint256(keccak256("Lido.Vaults.OperatorGrid")) - 1)) & ~bytes32(uint256(0xff))
     */
    bytes32 private constant ERC7201_STORAGE_LOCATION =
        0x6b64617c951381e2c1eff2be939fe368ab6d76b7d335df2e47ba2309eba1c700;

    constructor(address _admin, TierParams memory _defaultTierParams) {
        if (_admin == address(0)) revert ZeroArgument("_admin");

        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(REGISTRY_ROLE, _admin);

        ERC7201Storage storage $ = _getStorage();

        //create default tier with default share limit
        $.tiers.push(
            Tier({
                operator: DEFAULT_TIER_OPERATOR,
                shareLimit: uint96(_defaultTierParams.shareLimit),
                reserveRatioBP: uint16(_defaultTierParams.reserveRatioBP),
                forcedRebalanceThresholdBP: uint16(_defaultTierParams.forcedRebalanceThresholdBP),
                treasuryFeeBP: uint16(_defaultTierParams.treasuryFeeBP),
                liabilityShares: 0
            })
        );
    }

    /// @notice Registers a new group
    /// @param _nodeOperator address of the node operator
    /// @param _shareLimit Maximum share limit for the group
    function registerGroup(address _nodeOperator, uint256 _shareLimit) external onlyRole(REGISTRY_ROLE) {
        if (_nodeOperator == address(0)) revert ZeroArgument("_nodeOperator");

        ERC7201Storage storage $ = _getStorage();
        if ($.groups[_nodeOperator].operator != address(0)) revert GroupExists();

        $.groups[_nodeOperator] = Group({
            operator: _nodeOperator,
            shareLimit: uint96(_shareLimit),
            liabilityShares: 0,
            tierIds: new uint128[](0)
        });
        $.nodeOperators.push(_nodeOperator);

        emit GroupAdded(_nodeOperator, uint96(_shareLimit));
    }

    /// @notice Updates the share limit of a group
    /// @param _nodeOperator address of the node operator
    /// @param _shareLimit New share limit value
    function updateGroupShareLimit(address _nodeOperator, uint256 _shareLimit) external onlyRole(REGISTRY_ROLE) {
        if (_nodeOperator == address(0)) revert ZeroArgument("_nodeOperator");

        ERC7201Storage storage $ = _getStorage();
        Group storage group_ = $.groups[_nodeOperator];
        if (group_.operator == address(0)) revert GroupNotExists();

        group_.shareLimit = uint96(_shareLimit);

        emit GroupShareLimitUpdated(_nodeOperator, uint96(_shareLimit));
    }

    /// @notice Returns a group by node operator address
    /// @param _nodeOperator address of the node operator
    /// @return Group
    function group(address _nodeOperator) external view returns (Group memory) {
        return _getStorage().groups[_nodeOperator];
    }

    /// @notice Registers a new tier
    /// @param _nodeOperator address of the node operator
    /// @param _tiers array of tiers to register
    function registerTiers(
        address _nodeOperator,
        TierParams[] calldata _tiers
    ) external onlyRole(REGISTRY_ROLE) {
        if (_nodeOperator == address(0)) revert ZeroArgument("_nodeOperator");

        ERC7201Storage storage $ = _getStorage();
        Group storage group_ = $.groups[_nodeOperator];
        if (group_.operator == address(0)) revert GroupNotExists();

        uint128 tierId = uint128($.tiers.length);
        uint256 length = _tiers.length;
        for (uint256 i = 0; i < length; i++) {
            _validateParams(tierId, _tiers[i].reserveRatioBP, _tiers[i].forcedRebalanceThresholdBP, _tiers[i].treasuryFeeBP);

            Tier memory tier_ = Tier({
                operator: _nodeOperator,
                shareLimit: uint96(_tiers[i].shareLimit),
                reserveRatioBP: uint16(_tiers[i].reserveRatioBP),
                forcedRebalanceThresholdBP: uint16(_tiers[i].forcedRebalanceThresholdBP),
                treasuryFeeBP: uint16(_tiers[i].treasuryFeeBP),
                liabilityShares: 0
            });
            $.tiers.push(tier_);
            group_.tierIds.push(tierId);

            emit TierAdded(
                _nodeOperator,
                tierId,
                uint96(_tiers[i].shareLimit),
                uint16(_tiers[i].reserveRatioBP),
                uint16(_tiers[i].forcedRebalanceThresholdBP),
                uint16(_tiers[i].treasuryFeeBP)
            );

            tierId++;
        }
    }

    /// @notice Returns a tier by ID
    /// @param _tierId id of the tier
    /// @return Tier
    function tier(uint256 _tierId) external view returns (Tier memory) {
        ERC7201Storage storage $ = _getStorage();
        if (_tierId >= $.tiers.length) revert TierNotExists();
        return $.tiers[_tierId];
    }

    /// @notice Returns the number of tiers
    /// @return Number of tiers
    function tiersCount() external view returns (uint256) {
        return _getStorage().tiers.length;
    }

    /// @notice Alters a tier
    /// @dev We do not enforce to update old vaults with the new tier params, only new ones.
    /// @param _tierId id of the tier
    /// @param _tierParams new tier params
    function alterTier(uint256 _tierId, TierParams calldata _tierParams) external onlyRole(REGISTRY_ROLE) {
        ERC7201Storage storage $ = _getStorage();
        if (_tierId >= $.tiers.length) revert TierNotExists();

        _validateParams(_tierId, _tierParams.reserveRatioBP, _tierParams.forcedRebalanceThresholdBP, _tierParams.treasuryFeeBP);

        Tier storage tier_ = $.tiers[_tierId];

        tier_.shareLimit = uint96(_tierParams.shareLimit);
        tier_.reserveRatioBP = uint16(_tierParams.reserveRatioBP);
        tier_.forcedRebalanceThresholdBP = uint16(_tierParams.forcedRebalanceThresholdBP);
        tier_.treasuryFeeBP = uint16(_tierParams.treasuryFeeBP);

        emit TierUpdated(_tierId, tier_.shareLimit, tier_.reserveRatioBP, tier_.forcedRebalanceThresholdBP, tier_.treasuryFeeBP);
    }

    /// @notice Validates tier parameters
    /// @param _reserveRatioBP Reserve ratio
    /// @param _forcedRebalanceThresholdBP Forced rebalance threshold
    /// @param _treasuryFeeBP Treasury fee
    function _validateParams(
      uint256 _tierId,
      uint256 _reserveRatioBP,
      uint256 _forcedRebalanceThresholdBP,
      uint256 _treasuryFeeBP
    ) internal pure {
        if (_reserveRatioBP == 0) revert ZeroArgument("_reserveRatioBP");
        if (_reserveRatioBP > TOTAL_BASIS_POINTS)
            revert ReserveRatioTooHigh(_tierId, _reserveRatioBP, TOTAL_BASIS_POINTS);

        if (_forcedRebalanceThresholdBP == 0) revert ZeroArgument("_forcedRebalanceThresholdBP");
        if (_forcedRebalanceThresholdBP > _reserveRatioBP)
            revert ForcedRebalanceThresholdTooHigh(_tierId, _forcedRebalanceThresholdBP, _reserveRatioBP);

        if (_treasuryFeeBP > TOTAL_BASIS_POINTS)
            revert TreasuryFeeTooHigh(_tierId, _treasuryFeeBP, TOTAL_BASIS_POINTS);
    }

    function _getStorage() private pure returns (ERC7201Storage storage $) {
        assembly {
            $.slot := ERC7201_STORAGE_LOCATION
        }
    }

    // -----------------------------
    //            EVENTS
    // -----------------------------
    event GroupAdded(address indexed nodeOperator, uint256 shareLimit);
    event GroupShareLimitUpdated(address indexed nodeOperator, uint256 shareLimit);
    event TierAdded(address indexed nodeOperator, uint256 indexed tierId, uint256 shareLimit, uint256 reserveRatioBP, uint256 forcedRebalanceThresholdBP, uint256 treasuryFee);
    event VaultAdded(address indexed vault);
    event TierChanged(address indexed vault, uint256 indexed tierId);
    event TierChangeRequested(address indexed vault, uint256 indexed currentTierId, uint256 indexed requestedTierId);
    event TierUpdated(uint256 indexed tierId, uint256 shareLimit, uint256 reserveRatioBP, uint256 forcedRebalanceThresholdBP, uint256 treasuryFee);

    // -----------------------------
    //            ERRORS
    // -----------------------------
    error NotAuthorized(string operation, address sender);
    error ZeroArgument(string argument);
    error GroupExists();
    error GroupNotExists();
    error GroupLimitExceeded();
    error GroupMintedSharesUnderflow();
    error NodeOperatorNotExists();
    error TierExists();
    error TiersNotAvailable();
    error TierLimitExceeded();
    error TierMintedSharesUnderflow();

    error TierNotExists();
    error TierAlreadySet();
    error TierAlreadyRequested();
    error TierNotInOperatorGroup();
    error InvalidTierId(uint256 requestedTierId, uint256 confirmedTierId);
    error CannotChangeToDefaultTier();

    error ReserveRatioTooHigh(uint256 tierId, uint256 reserveRatioBP, uint256 maxReserveRatioBP);
    error ForcedRebalanceThresholdTooHigh(uint256 tierId, uint256 forcedRebalanceThresholdBP, uint256 reserveRatioBP);
    error TreasuryFeeTooHigh(uint256 tierId, uint256 treasuryFeeBP, uint256 maxTreasuryFeeBP);
}
