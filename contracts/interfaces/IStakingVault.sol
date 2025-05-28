// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Interface for staking vault contract
interface IStakingVault {
    /// @notice Calculates fee for validator withdrawal
    /// @param _numKeys Number of validators to exit
    /// @return Fee amount in wei
    function calculateValidatorWithdrawalFee(uint256 _numKeys) external pure returns (uint256);
}
