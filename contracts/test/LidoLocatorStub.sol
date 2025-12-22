// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;


contract LidoLocatorStub {
    address public operatorGrid;
    address public vaultHub;
    address public vaultFactory;
    address public lazyOracle;
    address public accountingOracle;

    constructor(address _operatorGrid, address _vaultHub, address _vaultFactory, address _lazyOracle, address _accountingOracle) {
        require(_operatorGrid != address(0), "Zero operator grid address");
        require(_vaultHub != address(0), "Zero vault hub address");
        require(_vaultFactory != address(0), "Zero vault factory address");
        require(_lazyOracle != address(0), "Zero lazy oracle address");
        require(_accountingOracle != address(0), "Zero accounting oracle address");

        operatorGrid = _operatorGrid;
        vaultHub = _vaultHub;
        vaultFactory = _vaultFactory;
        lazyOracle = _lazyOracle;
        accountingOracle = _accountingOracle;
    }
}
