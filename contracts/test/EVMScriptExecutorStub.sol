// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "@openzeppelin/contracts/proxy/utils/UUPSUpgradeable.sol";
import "../OwnableUpgradeable.sol";

contract EVMScriptExecutorStub is UUPSUpgradeable, OwnableUpgradeable {
    bytes public evmScript;

    function executeEVMScript(bytes memory _evmScript) external returns (bytes memory) {
        evmScript = _evmScript;
    }

    function _authorizeUpgrade(address newImplementation) internal override onlyOwner {}
}
