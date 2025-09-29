// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

contract StakingVaultStub {

    address nodeOperator_storage;

    constructor(address _nodeOperator) {
        if (_nodeOperator == address(0)) revert("ZERO_NODE_OPERATOR");

        nodeOperator_storage = _nodeOperator;
    }

    function nodeOperator() public view returns (address) {
        return nodeOperator_storage;
    }
}
