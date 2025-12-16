// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IStakingVault {
    /**
     * @notice Returns the node operator address
     * @return Address of the node operator
     */
    function nodeOperator() external view returns (address);
}
