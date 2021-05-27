// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "../EasyTrackExecutor.sol";

contract EasyTrackExecutorStub is EasyTrackExecutor {
    bool public isBeforeCreateGuardCalled;
    bool public isBeforeCancelGuardCalled;

    constructor(address _easyTraksRegistry) EasyTrackExecutor(_easyTraksRegistry) {}

    string public constant override description = "Stub Executor";
    bytes4 public constant override executeMethodId = hex"4a7acdae";
    string public constant override executeCalldataSignature = "(uint256,address)";

    function _beforeCreateMotionGuard(address _caller, bytes memory _data) internal override {
        isBeforeCreateGuardCalled = true;
    }

    function _beforeCancelMotionGuard(
        address _caller,
        uint256 _motionId,
        bytes memory _data
    ) internal override {
        isBeforeCancelGuardCalled = true;
    }

    function dataSignature(uint256 _key, address _value) public {}
}
