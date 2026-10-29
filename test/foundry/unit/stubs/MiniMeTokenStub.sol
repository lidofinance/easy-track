// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Stands in for the LDO MiniMe token `EasyTrack` reads objection weights from.
/// @dev The snapshot getters return the live balances. The unit suite never moves tokens after a
/// motion is created, so the balance at the snapshot block and the current one are the same.
contract MiniMeTokenStub {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;

    function mint(address _to, uint256 _amount) external {
        balanceOf[_to] += _amount;
        totalSupply += _amount;
    }

    function transfer(address _to, uint256 _amount) external returns (bool) {
        balanceOf[msg.sender] -= _amount;
        balanceOf[_to] += _amount;
        return true;
    }

    function balanceOfAt(address _owner, uint256) external view returns (uint256) {
        return balanceOf[_owner];
    }

    function totalSupplyAt(uint256) external view returns (uint256) {
        return totalSupply;
    }
}
