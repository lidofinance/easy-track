// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

interface ILidoLocator {
    function lido() external view returns(address);
    function vaultHub() external view returns (address);
}
