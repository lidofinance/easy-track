// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

contract MockERC20 {
    uint8 public decimals;
    bool public approveReturnsNoData;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(uint8 _decimals) {
        decimals = _decimals;
    }

    function mint(address account, uint256 amount) external {
        balanceOf[account] += amount;
    }

    function setApproveReturnsNoData(bool value) external {
        approveReturnsNoData = value;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        if (approveReturnsNoData) {
            assembly {
                return(0, 0)
            }
        }
        return true;
    }

    function transfer(address recipient, uint256 amount) external returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }

    function transferFrom(
        address sender,
        address recipient,
        uint256 amount
    ) external returns (bool) {
        uint256 allowed = allowance[sender][msg.sender];
        require(allowed >= amount, "INSUFFICIENT_ALLOWANCE");
        allowance[sender][msg.sender] = allowed - amount;
        _transfer(sender, recipient, amount);
        return true;
    }

    function _transfer(
        address sender,
        address recipient,
        uint256 amount
    ) private {
        require(balanceOf[sender] >= amount, "INSUFFICIENT_BALANCE");
        balanceOf[sender] -= amount;
        balanceOf[recipient] += amount;
    }
}
