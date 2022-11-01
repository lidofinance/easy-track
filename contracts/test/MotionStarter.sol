// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "../EasyTrack.sol";

interface IMiniMeTokenERC20 is IMiniMeToken {
    function transfer(address _recipient, uint256 _amount) external;

    function balanceOf(address _holder) external view returns (uint256);
}

contract MotionStarter {
    EasyTrack immutable easyTrack;

    constructor(address _easyTrack) {
        easyTrack = EasyTrack(_easyTrack);
    }

    function startMotionTransferringLDO(
        address _evmScriptFactory,
        bytes memory _evmScriptCallData,
        address _ldoRecipient
    ) public {
        IMiniMeTokenERC20 govToken = IMiniMeTokenERC20(address(easyTrack.governanceToken()));

        uint256 prevBlock = block.number - 1;

        uint256 myBalanceAtPrevBlock = govToken.balanceOfAt(address(this), prevBlock);
        assert(myBalanceAtPrevBlock == govToken.balanceOf(address(this)));

        assert(govToken.balanceOfAt(_ldoRecipient, prevBlock) == 0);
        assert(govToken.balanceOf(_ldoRecipient) == 0);

        govToken.transfer(_ldoRecipient, myBalanceAtPrevBlock);

        assert(govToken.balanceOf(_ldoRecipient) == myBalanceAtPrevBlock);
        assert(govToken.balanceOf(address(this)) == 0);

        easyTrack.createMotion(_evmScriptFactory, _evmScriptCallData);
    }
}
