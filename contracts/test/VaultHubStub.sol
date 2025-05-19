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
        uint128 totalValue;
        int128 inOutDelta;
        uint128 locked;
        uint96 liabilityShares;
        uint64 reportTimestamp;
        int128 reportInOutDelta;
        uint96 feeSharesCharged;
    }

    mapping(address => VaultConnection) connections;
    mapping(address => VaultRecord) records;

    uint96 public vaultIndex = 1;

    bytes32 public constant VAULT_MASTER_ROLE = keccak256("Vaults.VaultHub.VaultMasterRole");

    constructor(address _admin) {
        require(_admin != address(0), "Zero admin address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(VAULT_MASTER_ROLE, _admin);
    }

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external {
        connections[_vault] = VaultConnection(
            msg.sender, // owner
            1000, // shareLimit
            vaultIndex++, // vaultIndex
            false, // pendingDisconnect
            100, // reserveRatioBP
            50, // forcedRebalanceThresholdBP
            1000, // infraFeeBP
            500, // liquidityFeeBP
            500 // reservationFeeBP
        );

        records[_vault] = VaultRecord(
            0, // totalValue
            0, // inOutDelta
            0, // locked
            0, // liabilityShares
            uint64(block.timestamp), // reportTimestamp
            0, // reportInOutDelta
            0 // feeSharesCharged
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

    event ShareLimitUpdated(address indexed vault, uint256 newShareLimit);
    event VaultFeesUpdated(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);
}
