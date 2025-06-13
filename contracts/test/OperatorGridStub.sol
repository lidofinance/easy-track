// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

struct TierParams {
    uint256 shareLimit;
    uint256 reserveRatioBP;
    uint256 forcedRebalanceThresholdBP;
    uint256 infraFeeBP;
    uint256 liquidityFeeBP;
    uint256 reservationFeeBP;
}

contract OperatorGridStub is AccessControl {
    bytes32 public constant REGISTRY_ROLE = keccak256("vaults.OperatorsGrid.Registry");
    uint256 public constant DEFAULT_TIER_ID = 0;
    address public constant DEFAULT_TIER_OPERATOR = address(uint160(type(uint160).max));
    uint256 internal constant TOTAL_BASIS_POINTS = 100_00;

    struct Group {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint256[] tierIds;
    }

    struct Tier {
        address operator;
        uint96 shareLimit;
        uint96 liabilityShares;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
    }

    Tier[] tiers;
    mapping(address => Group) groups;
    address[] nodeOperators;
    address public immutable LIDO_LOCATOR;

    constructor(address _admin, TierParams memory _defaultTierParams, address _lidoLocator) {
        require(_admin != address(0), "Zero admin address");
        require(_lidoLocator != address(0), "Zero lido locator address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(REGISTRY_ROLE, _admin);
        LIDO_LOCATOR = _lidoLocator;

        tiers.push(
            Tier({
                operator: DEFAULT_TIER_OPERATOR,
                shareLimit: uint96(_defaultTierParams.shareLimit),
                reserveRatioBP: uint16(_defaultTierParams.reserveRatioBP),
                forcedRebalanceThresholdBP: uint16(_defaultTierParams.forcedRebalanceThresholdBP),
                infraFeeBP: uint16(_defaultTierParams.infraFeeBP),
                liquidityFeeBP: uint16(_defaultTierParams.liquidityFeeBP),
                reservationFeeBP: uint16(_defaultTierParams.reservationFeeBP),
                liabilityShares: 0
            })
        );
    }

    function registerGroup(address _nodeOperator, uint256 _shareLimit) external onlyRole(REGISTRY_ROLE) {
        require(_nodeOperator != address(0), "Zero node operator address");
        require(groups[_nodeOperator].operator == address(0), "Group already exists");

        groups[_nodeOperator] = Group({
            operator: _nodeOperator,
            shareLimit: uint96(_shareLimit),
            liabilityShares: 0,
            tierIds: new uint256[](0)
        });
        nodeOperators.push(_nodeOperator);
    }

    function updateGroupShareLimit(address _nodeOperator, uint256 _shareLimit) external onlyRole(REGISTRY_ROLE) {
        require(_nodeOperator != address(0), "Zero node operator address");
        require(groups[_nodeOperator].operator != address(0), "Group does not exist");
        
        groups[_nodeOperator].shareLimit = uint96(_shareLimit);
    }

    function group(address _nodeOperator) external view returns (Group memory) {
        return groups[_nodeOperator];
    }

    function registerTiers(
        address _nodeOperator,
        TierParams[] calldata _tiers
    ) external onlyRole(REGISTRY_ROLE) {
        require(_nodeOperator != address(0), "Zero node operator address");
        require(groups[_nodeOperator].operator != address(0), "Group does not exist");

        uint256 tierId = tiers.length;
        uint256 length = _tiers.length;
        for (uint256 i = 0; i < length; i++) {
            Tier memory tier_ = Tier({
                operator: _nodeOperator,
                shareLimit: uint96(_tiers[i].shareLimit),
                reserveRatioBP: uint16(_tiers[i].reserveRatioBP),
                forcedRebalanceThresholdBP: uint16(_tiers[i].forcedRebalanceThresholdBP),
                infraFeeBP: uint16(_tiers[i].infraFeeBP),
                liquidityFeeBP: uint16(_tiers[i].liquidityFeeBP),
                reservationFeeBP: uint16(_tiers[i].reservationFeeBP),
                liabilityShares: 0
            });
            tiers.push(tier_);
            groups[_nodeOperator].tierIds.push(tierId);
            tierId++;
        }
    }

    function tier(uint256 _tierId) external view returns (Tier memory) {
        require(_tierId < tiers.length, "Tier does not exist");
        return tiers[_tierId];
    }

    function tiersCount() external view returns (uint256) {
        return tiers.length;
    }

    function alterTiers(uint256[] calldata _tierIds, TierParams[] calldata _tierParams) external onlyRole(REGISTRY_ROLE) {
        require(_tierIds.length == _tierParams.length, "Array length mismatch");

        uint256 length = _tierIds.length;
        
        for (uint256 i = 0; i < length; i++) {
            require(_tierIds[i] < tiers.length, "Tier does not exist");

            Tier storage tier_ = tiers[_tierIds[i]];
            tier_.shareLimit = uint96(_tierParams[i].shareLimit);
            tier_.reserveRatioBP = uint16(_tierParams[i].reserveRatioBP);
            tier_.forcedRebalanceThresholdBP = uint16(_tierParams[i].forcedRebalanceThresholdBP);
            tier_.infraFeeBP = uint16(_tierParams[i].infraFeeBP);
            tier_.liquidityFeeBP = uint16(_tierParams[i].liquidityFeeBP);
            tier_.reservationFeeBP = uint16(_tierParams[i].reservationFeeBP);
        }
    }
}
