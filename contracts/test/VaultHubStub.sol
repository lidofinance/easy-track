// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

contract VaultHubStub is AccessControl {
    struct VaultConnection {
        address owner;
        uint96 shareLimit;
        uint96 vaultIndex;
        bool pendingDisconnect;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
        bool isBeaconDepositsManuallyPaused;
    }

    struct Int112WithRefSlotCache {
        int112 value;
        int112 valueOnRefSlot;
        uint32 refSlot;
    }

    struct VaultRecord {
        Report report;
        uint128 locked;
        uint96 liabilityShares;
        Int112WithRefSlotCache inOutDelta;
        uint64 reportTimestamp;
    }

    struct Report {
        uint128 totalValue;
        int112 inOutDelta;
    }

    struct VaultObligations {
        uint128 settledLidoFees;
        uint128 unsettledLidoFees;
        uint128 redemptions;
    }

    mapping(address => VaultConnection) connections;
    mapping(address => VaultRecord) records;
    mapping(address => VaultObligations) obligations;

    uint96 public vaultIndex = 1;

    bytes32 public constant VAULT_MASTER_ROLE = keccak256("vaults.VaultHub.VaultMasterRole");
    bytes32 public constant VALIDATOR_EXIT_ROLE = keccak256("vaults.VaultHub.ValidatorExitRole");
    bytes32 public constant REDEMPTION_MASTER_ROLE = keccak256("vaults.VaultHub.RedemptionMasterRole");
    bytes32 public constant BAD_DEBT_MASTER_ROLE = keccak256("vaults.VaultHub.BadDebtMasterRole");

    constructor(address _admin) {
        require(_admin != address(0), "Zero admin address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(VAULT_MASTER_ROLE, _admin);
        _setupRole(VALIDATOR_EXIT_ROLE, _admin);
        _setupRole(REDEMPTION_MASTER_ROLE, _admin);
        _setupRole(BAD_DEBT_MASTER_ROLE, _admin);
    }

    function connectVault(address _vault) external {
        connections[_vault] = VaultConnection(
            msg.sender,
            1000,
            vaultIndex++,
            false,
            100,
            50,
            1000,
            500,
            500,
            false
        );

        records[_vault] = VaultRecord(
            Report(0, 0),
            0,
            0,
            Int112WithRefSlotCache(0, 0, 0),
            uint64(block.timestamp)
        );

        obligations[_vault] = VaultObligations(0, 0, 0);
    }

    function vaultConnection(address _vault) external view returns (VaultConnection memory) {
        return connections[_vault];
    }

    function vaultRecord(address _vault) external view returns (VaultRecord memory) {
        return records[_vault];
    }

    function vaultObligations(address _vault) external view returns (VaultObligations memory) {
        return obligations[_vault];
    }

    /// @return true if the vault is connected to the hub
    function isVaultConnected(address _vault) external view returns (bool) {
        return connections[_vault].vaultIndex != 0;
    }

    function updateShareLimit(address _vault, uint256 _shareLimit) external onlyRole(VAULT_MASTER_ROLE) {
        connections[_vault].shareLimit = uint96(_shareLimit);
        emit VaultShareLimitUpdated(_vault, _shareLimit);
    }

    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external onlyRole(VAULT_MASTER_ROLE) {
        uint16 preInfraFeeBP = connections[_vault].infraFeeBP;
        uint16 preLiquidityFeeBP = connections[_vault].liquidityFeeBP;
        uint16 preReservationFeeBP = connections[_vault].reservationFeeBP;

        connections[_vault].infraFeeBP = uint16(_infraFeeBP);
        connections[_vault].liquidityFeeBP = uint16(_liquidityFeeBP);
        connections[_vault].reservationFeeBP = uint16(_reservationFeeBP);

        emit VaultFeesUpdated(
            _vault,
            preInfraFeeBP,
            preLiquidityFeeBP,
            preReservationFeeBP,
            _infraFeeBP,
            _liquidityFeeBP,
            _reservationFeeBP
        );
    }

    function forceValidatorExit(
        address _vault,
        bytes calldata _pubkeys,
        address _refundRecipient
    ) external payable onlyRole(VALIDATOR_EXIT_ROLE) {
        // First vault is special and will revert
        if (connections[_vault].vaultIndex == 1) {
            revert("Special vault revert 1");
        }
        emit ForcedValidatorExitTriggered(_vault, _pubkeys, _refundRecipient);
    }

    function socializeBadDebt(
        address _badDebtVault,
        address _vaultAcceptor,
        uint256 _maxSharesToSocialize
    ) external onlyRole(BAD_DEBT_MASTER_ROLE) {
        // First vault is special and will revert
        if (connections[_badDebtVault].vaultIndex == 1) {
            revert("Special vault revert 1");
        }
        emit BadDebtSocialized(_badDebtVault, _vaultAcceptor, _maxSharesToSocialize);
    }

    function setVaultRedemptions(
        address _vault,
        uint256 _redemptionsValue
    ) external onlyRole(REDEMPTION_MASTER_ROLE) {
        obligations[_vault].redemptions = uint128(_redemptionsValue);
        emit RedemptionsUpdated(_vault, _redemptionsValue);
    }

    event VaultShareLimitUpdated(address indexed vault, uint256 newShareLimit);
    event VaultFeesUpdated(
        address indexed vault,
        uint256 preInfraFeeBP,
        uint256 preLiquidityFeeBP,
        uint256 preReservationFeeBP,
        uint256 infraFeeBP,
        uint256 liquidityFeeBP,
        uint256 reservationFeeBP
    );
    event ForcedValidatorExitTriggered(address indexed vault, bytes pubkeys, address refundRecipient);
    event BadDebtSocialized(address indexed vaultDonor, address indexed vaultAcceptor, uint256 badDebtShares);
    event RedemptionsUpdated(address indexed vault, uint256 unsettledRedemptions);
}
