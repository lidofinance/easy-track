// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface IVaultHubStub {
    function setObligationsShortfallValue(address _vault, uint256 _obligationsShortfallValue) external;
}
