// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @notice Stands in for the LDO MiniMe token `EasyTrack` reads objection weights from.
/// @dev Keeps the MiniMe checkpoints, one per block a balance or the supply changed in, so the
/// snapshot getters return the value at the block asked for, not the live one.
contract MiniMeTokenStub {
    struct Checkpoint {
        uint256 fromBlock;
        uint256 value;
    }

    mapping(address => Checkpoint[]) private _balances;
    Checkpoint[] private _totalSupply;

    function mint(address _to, uint256 _amount) external {
        _update(_balances[_to], balanceOf(_to) + _amount);
        _update(_totalSupply, totalSupply() + _amount);
    }

    function transfer(address _to, uint256 _amount) external returns (bool) {
        _update(_balances[msg.sender], balanceOf(msg.sender) - _amount);
        _update(_balances[_to], balanceOf(_to) + _amount);
        return true;
    }

    function balanceOf(address _owner) public view returns (uint256) {
        return _valueAt(_balances[_owner], block.number);
    }

    function totalSupply() public view returns (uint256) {
        return _valueAt(_totalSupply, block.number);
    }

    function balanceOfAt(address _owner, uint256 _blockNumber) external view returns (uint256) {
        return _valueAt(_balances[_owner], _blockNumber);
    }

    function totalSupplyAt(uint256 _blockNumber) external view returns (uint256) {
        return _valueAt(_totalSupply, _blockNumber);
    }

    /// @dev MiniMe `updateValueAtNow`: a new checkpoint per block, overwritten within the block
    function _update(Checkpoint[] storage checkpoints, uint256 value) private {
        if (checkpoints.length == 0 || checkpoints[checkpoints.length - 1].fromBlock < block.number)
        {
            checkpoints.push(Checkpoint(block.number, value));
        } else {
            checkpoints[checkpoints.length - 1].value = value;
        }
    }

    /// @dev MiniMe `getValueAt`: the value of the last checkpoint at or before `blockNumber`
    function _valueAt(Checkpoint[] storage checkpoints, uint256 blockNumber)
        private
        view
        returns (uint256)
    {
        if (checkpoints.length == 0 || blockNumber < checkpoints[0].fromBlock) return 0;
        if (blockNumber >= checkpoints[checkpoints.length - 1].fromBlock) {
            return checkpoints[checkpoints.length - 1].value;
        }

        uint256 min;
        uint256 max = checkpoints.length - 1;
        while (max > min) {
            uint256 mid = (max + min + 1) / 2;
            if (checkpoints[mid].fromBlock <= blockNumber) {
                min = mid;
            } else {
                max = mid - 1;
            }
        }

        return checkpoints[min].value;
    }
}
