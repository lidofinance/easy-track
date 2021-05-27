// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

import "./IEasyTrackExecutor.sol";

pragma solidity 0.8.4;

abstract contract EasyTrackExecutor is IEasyTrackExecutor {
    address private easyTracksRegistry;

    constructor(address _easyTracksRegistry) {
        easyTracksRegistry = _easyTracksRegistry;
    }

    function beforeCreateMotionGuard(address _caller, bytes memory _data)
        external
        override
        onlyEasyTrackRegistry
    {
        _beforeCreateMotionGuard(_caller, _data);
    }

    function beforeCancelMotionGuard(
        address _caller,
        uint256 _motionId,
        bytes memory _data
    ) external override onlyEasyTrackRegistry {
        _beforeCancelMotionGuard(_caller, _motionId, _data);
    }

    function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal virtual;

    function _beforeCancelMotionGuard(
        address _caller,
        uint256 _motionId,
        bytes memory _data
    ) internal virtual;

    modifier onlyEasyTrackRegistry {
        require(msg.sender == easyTracksRegistry, "NOT_EASYTRACK_REGISTRY");
        _;
    }
}
