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
        uint16 infraFeeBP;
        uint16 liquidityFeeBP;
        uint16 reservationFeeBP;
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
            1000, // infraFeeBP
            500, // liquidityFeeBP
            500, // reservationFeeBP
            false, // pendingDisconnect
            0 // feeSharesCharged
        );
    }

    function vaultSocket(address _vault) external view returns (VaultSocket memory) {
        return sockets[_vault];
    }

    function updateShareLimits(address[] calldata _vaults, uint256[] calldata _shareLimits) external onlyRole(VAULT_MASTER_ROLE) {
        for (uint256 i = 0; i < _vaults.length; i++) {
            sockets[_vaults[i]].shareLimit = uint96(_shareLimits[i]);
            emit ShareLimitUpdated(_vaults[i], _shareLimits[i]);
        }
    }

    function updateVaultsFees(
        address[] calldata _vaults,
        uint256[] calldata _infraFeesBP,
        uint256[] calldata _liquidityFeesBP,
        uint256[] calldata _reservationFeesBP
    ) external onlyRole(VAULT_MASTER_ROLE) {
        for (uint256 i = 0; i < _vaults.length; i++) {
            sockets[_vaults[i]].infraFeeBP = uint16(_infraFeesBP[i]);
            sockets[_vaults[i]].liquidityFeeBP = uint16(_liquidityFeesBP[i]);
            sockets[_vaults[i]].reservationFeeBP = uint16(_reservationFeesBP[i]);
            emit VaultFeesUpdated(_vaults[i], _infraFeesBP[i], _liquidityFeesBP[i], _reservationFeesBP[i]);
        }
    }

    event ShareLimitUpdated(address indexed vault, uint256 newShareLimit);
    event VaultFeesUpdated(address indexed vault, uint256 infraFeeBP, uint256 liquidityFeeBP, uint256 reservationFeeBP);
}
