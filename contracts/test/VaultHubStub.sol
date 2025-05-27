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
    }

    struct VaultRecord {
        Report report;
        uint128 locked;
        uint96 liabilityShares;
        uint64 reportTimestamp;
        int128 inOutDelta;
    }

    struct Report {
        uint128 totalValue;
        int128 inOutDelta;
    }

    mapping(address => VaultConnection) connections;
    mapping(address => VaultRecord) records;

    uint96 public vaultIndex = 1;

    bytes32 public constant VAULT_MASTER_ROLE = keccak256("vaults.VaultHub.VaultMasterRole");
    bytes32 public constant WITHDRAWAL_EXECUTOR_ROLE = keccak256("vaults.VaultHub.WithdrawalExecutorRole");

    constructor(address _admin) {
        require(_admin != address(0), "Zero admin address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(VAULT_MASTER_ROLE, _admin);
        _setupRole(WITHDRAWAL_EXECUTOR_ROLE, _admin);
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
            500
        );

        records[_vault] = VaultRecord(
            Report(0, 0),
            0,
            0,
            uint64(block.timestamp),
            0
        );
    }

    function vaultConnection(address _vault) external view returns (VaultConnection memory) {
        return connections[_vault];
    }

    function vaultRecord(address _vault) external view returns (VaultRecord memory) {
        return records[_vault];
    }

    function updateShareLimit(address _vault, uint256 _shareLimit) external onlyRole(VAULT_MASTER_ROLE) {
        connections[_vault].shareLimit = uint96(_shareLimit);
        emit ShareLimitUpdated(_vault, _shareLimit);
    }

    function updateVaultFees(
        address _vault,
        uint256 _infraFeeBP,
        uint256 _liquidityFeeBP,
        uint256 _reservationFeeBP
    ) external onlyRole(VAULT_MASTER_ROLE) {
        connections[_vault].infraFeeBP = uint16(_infraFeeBP);
        connections[_vault].liquidityFeeBP = uint16(_liquidityFeeBP);
        connections[_vault].reservationFeeBP = uint16(_reservationFeeBP);
        emit VaultFeesUpdated(_vault, _infraFeeBP, _liquidityFeeBP, _reservationFeeBP);
    }

    function forceValidatorExits(
        address _vault,
        bytes calldata _pubkeys,
        address _refundRecipient
    ) external payable onlyRole(WITHDRAWAL_EXECUTOR_ROLE) {
        emit ValidatorExitsForced(_vault, _pubkeys, _refundRecipient);
    }

    event ShareLimitUpdated(address indexed vault, uint256 newShareLimit);
    event VaultFeesUpdated(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);
    event ValidatorExitsForced(address indexed vault, bytes pubkeys, address refundRecipient);
}
