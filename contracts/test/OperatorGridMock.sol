// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

struct TierParams {
    uint256 shareLimit;
    uint256 reserveRatioBP;
    uint256 rebalanceThresholdBP;
    uint256 treasuryFeeBP;
}

contract OperatorGridMock is AccessControl {

    bytes32 public constant REGISTRY_ROLE = keccak256("vaults.OperatorsGrid.Registry");

    /// @notice Default group ID
    address public constant DEFAULT_GROUP_OPERATOR_ADDRESS = address(1);

    // -----------------------------
    //            STRUCTS
    // -----------------------------
    struct Group {
        uint96 shareLimit;
        uint96 mintedShares;
        address operator;
        uint256[] tiersId;
        address[] vaults;
    }

    struct Tier {
        uint96 shareLimit;
        uint96 mintedShares;
        uint16 reserveRatioBP;
        uint16 rebalanceThresholdBP;
        uint16 treasuryFeeBP;
    }

    // -----------------------------
    //        STORAGE
    // -----------------------------
    struct ERC7201Storage {
        Tier[] tiers;
        mapping(address => Group) groups;
        mapping(address => uint256) tierIndex;
    }

    /**
     * @notice Storage offset slot for ERC-7201 namespace
     *         The storage namespace is used to prevent upgrade collisions
     *         keccak256(abi.encode(uint256(keccak256("Lido.Vaults.OperatorGrid")) - 1)) & ~bytes32(uint256(0xff))
     */
    bytes32 private constant ERC7201_STORAGE_LOCATION =
        0x6b64617c951381e2c1eff2be939fe368ab6d76b7d335df2e47ba2309eba1c700;

    constructor(address _owner) {
        if (_owner == address(0)) revert ZeroArgument("_owner");

        _setupRole(DEFAULT_ADMIN_ROLE, _owner);
        _setupRole(REGISTRY_ROLE, _owner);

        ERC7201Storage storage $ = _getStorage();

        $.tiers.push(Tier(0, 0, 0, 0, 0));
    }

    /// @notice Registers a new group
    /// @param nodeOperator identifier of the group
    /// @param shareLimit Maximum share limit for the group
    function registerGroup(address nodeOperator, uint256 shareLimit) external onlyRole(REGISTRY_ROLE) {
        ERC7201Storage storage $ = _getStorage();

        if ($.groups[nodeOperator].operator != address(0)) revert GroupExists();

        $.groups[nodeOperator] = Group({
            shareLimit: uint96(shareLimit),
            mintedShares: 0,
            operator: nodeOperator,
            tiersId: new uint256[](0),
            vaults: new address[](0)
        });

        emit GroupAdded(nodeOperator, uint96(shareLimit));
    }

    /// @notice Updates the share limit of a group
    /// @param nodeOperator Group ID to update
    /// @param newShareLimit New share limit value
    function updateGroupShareLimit(address nodeOperator, uint256 newShareLimit) external onlyRole(REGISTRY_ROLE) {
        ERC7201Storage storage $ = _getStorage();

        Group storage group_ = $.groups[nodeOperator];
        if (group_.operator == address(0)) revert GroupNotExists();

        group_.shareLimit = uint96(newShareLimit);

        emit GroupShareLimitUpdated(nodeOperator, uint96(newShareLimit));
    }

    function group(address _nodeOperator) external view returns (Group memory) {
        ERC7201Storage storage $ = _getStorage();
        return $.groups[_nodeOperator];
    }

    /// @notice Registers a new tier
    /// @param nodeOperator address of the operator
    /// @param tiers array of tiers to register
    function registerTiers(
        address nodeOperator,
        TierParams[] calldata tiers
    ) external onlyRole(REGISTRY_ROLE) {
        ERC7201Storage storage $ = _getStorage();

        Group storage group_ = $.groups[nodeOperator];
        if (group_.operator == address(0)) revert GroupNotExists();

        uint256 tierIndex = $.tiers.length;
        uint256 length = tiers.length;
        for (uint256 i = 0; i < length; i++) {

            Tier memory tier = Tier({
                shareLimit: uint96(tiers[i].shareLimit),
                reserveRatioBP: uint16(tiers[i].reserveRatioBP),
                rebalanceThresholdBP: uint16(tiers[i].rebalanceThresholdBP),
                treasuryFeeBP: uint16(tiers[i].treasuryFeeBP),
                mintedShares: 0
            });
            $.tiers.push(tier);
            group_.tiersId.push(tierIndex);

            emit TierAdded(
                nodeOperator,
                tierIndex,
                uint96(tiers[i].shareLimit),
                uint16(tiers[i].reserveRatioBP),
                uint16(tiers[i].rebalanceThresholdBP),
                uint16(tiers[i].treasuryFeeBP)
            );

            tierIndex++;
        }
    }

    function _getStorage() private pure returns (ERC7201Storage storage $) {
        assembly {
            $.slot := ERC7201_STORAGE_LOCATION
        }
    }

    function getTiers() public view returns (Tier[] memory) {
        ERC7201Storage storage $ = _getStorage();
        return $.tiers;
    }

    // -----------------------------
    //            EVENTS
    // -----------------------------

    event GroupAdded(address indexed nodeOperator, uint256 shareLimit);
    event GroupShareLimitUpdated(address indexed nodeOperator, uint256 shareLimit);
    event TierAdded(address indexed nodeOperator, uint256 indexed tierId, uint256 shareLimit, uint256 reserveRatioBP, uint256 rebalanceThresholdBP, uint256 treasuryFee);
    event VaultAdded(address indexed nodeOperator, uint256 tierId, address indexed vault);
    event SharesLimitChanged(address indexed vault, address indexed nodeOperator, uint256 indexed tierId, uint256 tierSharesMinted, uint256 groupSharesMinted);

    // -----------------------------
    //            ERRORS
    // -----------------------------
    error NotAuthorized(string operation, address sender);
    error ZeroArgument(string argument);
    error GroupExists();
    error GroupNotExists();
    error GroupLimitExceeded();
    error GroupMintedSharesUnderflow();

    error TierExists();
    error TiersNotAvailable();
    error TierLimitExceeded();
    error TierMintedSharesUnderflow();

    error VaultExists();
    error VaultNotExists();
}
