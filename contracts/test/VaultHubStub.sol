// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

contract VaultHubStub is AccessControl {
    struct VaultSocket {
        address vault;
        uint96 liabilityShares;
        uint96 shareLimit;
        uint16 reserveRatioBP;
        uint16 forcedRebalanceThresholdBP;
        uint16 treasuryFeeBP;
        bool pendingDisconnect;
        uint96 feeSharesCharged;
    }

    mapping(address => VaultSocket) sockets;

    bytes32 public constant VAULT_MASTER_ROLE = keccak256("Vaults.VaultHub.VaultMasterRole");

    constructor(address _admin) {
        require(_admin != address(0), "Zero admin address");
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        _setupRole(VAULT_MASTER_ROLE, _admin);
    }

    /// @notice connects a vault to the hub in permissionless way, get limits from the Operator Grid
    /// @param _vault vault address
    function connectVault(address _vault) external {
        sockets[_vault] = VaultSocket(
            _vault,
            0, // liabilityShares
            1000, // shareLimit
            100, // reserveRatioBP
            50, // forcedRebalanceThresholdBP
            2000, // treasuryFeeBP
            false, // pendingDisconnect
            0
        );
    }

    function vaultSocket(address _vault) external view returns (VaultSocket memory) {
        return sockets[_vault];
    }

    function updateShareLimit(address _vault, uint256 _shareLimit) external onlyRole(VAULT_MASTER_ROLE) {
        sockets[_vault].shareLimit = uint96(_shareLimit);
        emit ShareLimitUpdated(_vault, _shareLimit);
    }

    function updateTreasuryFeeBP(address _vault, uint256 _treasuryFeeBP) external onlyRole(VAULT_MASTER_ROLE) {
        sockets[_vault].treasuryFeeBP = uint16(_treasuryFeeBP);
        emit TreasuryFeeBPUpdated(_vault, _treasuryFeeBP);
    }

    event ShareLimitUpdated(address indexed vault, uint256 newShareLimit);
    event TreasuryFeeBPUpdated(address indexed vault, uint256 newTreasuryFeeBP);
}
