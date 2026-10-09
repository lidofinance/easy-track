// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import {Test} from "forge-std/Test.sol";
import {
    SettleGeneralDelayedPenalty
} from "contracts/EVMScriptFactories/SettleGeneralDelayedPenalty.sol";
import {IBaseModule} from "contracts/interfaces/IBaseModule.sol";
import {AccountingStub} from "contracts/test/AccountingStub.sol";
import {BaseModuleStub} from "contracts/test/BaseModuleStub.sol";
import {EVMScripts} from "test/foundry/unit/helpers/EVMScripts.sol";

contract SettleGeneralDelayedPenaltyTest is Test {
    string internal constant FACTORY_NAME = "CSM v3";
    uint256 internal constant LOCK_NONCE = 42;
    uint256 internal constant NODE_OPERATORS_COUNT = 1000;
    /// @dev python: Wei(1)
    uint256 internal constant LOCKED_BOND = 1;

    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    AccountingStub internal accountingStub;
    BaseModuleStub internal baseModuleStub;
    SettleGeneralDelayedPenalty internal settleGeneralDelayedPenalty;

    function setUp() public {
        accountingStub = new AccountingStub();
        baseModuleStub = new BaseModuleStub();
        baseModuleStub.mock_setNodeOperatorsCount(NODE_OPERATORS_COUNT);
        baseModuleStub.mock_setAccounting(accountingStub);

        vm.prank(owner);
        settleGeneralDelayedPenalty =
            new SettleGeneralDelayedPenalty(owner, FACTORY_NAME, address(baseModuleStub));

        vm.label(address(accountingStub), "accountingStub");
        vm.label(address(baseModuleStub), "baseModuleStub");
        vm.label(address(settleGeneralDelayedPenalty), "settleGeneralDelayedPenalty");
    }

    // python: test_deploy
    function test_Deploy() external view {
        assertEq(settleGeneralDelayedPenalty.trustedCaller(), owner, "trustedCaller");
        assertEq(address(settleGeneralDelayedPenalty.module()), address(baseModuleStub), "module");
        assertEq(settleGeneralDelayedPenalty.name(), FACTORY_NAME, "name");
    }

    // python: test_create_evm_script_called_by_stranger
    function test_RevertWhen_CreateEVMScriptCalledByStranger() external {
        vm.expectRevert("CALLER_IS_FORBIDDEN");
        settleGeneralDelayedPenalty.createEVMScript(stranger, "");
    }

    // python: test_empty_calldata
    function test_RevertWhen_LockInfoListIsEmpty() external {
        SettleGeneralDelayedPenalty.LockInfo[] memory lockInfoList =
            new SettleGeneralDelayedPenalty.LockInfo[](0);

        vm.expectRevert("EMPTY_LOCK_INFO_LIST");
        settleGeneralDelayedPenalty.createEVMScript(owner, abi.encode(lockInfoList));
    }

    // python: test_non_sorted_calldata
    function test_RevertWhen_NodeOperatorsAreOutOfOrder() external {
        _lockBond(0);
        _lockBond(1);

        vm.expectRevert("NODE_OPERATORS_OUT_OF_ORDER");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(1, LOCK_NONCE), _lockInfo(0, LOCK_NONCE)))
        );

        vm.expectRevert("NODE_OPERATORS_OUT_OF_ORDER");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(0, LOCK_NONCE), _lockInfo(0, LOCK_NONCE)))
        );
    }

    // python: test_operator_id_out_of_range
    function test_RevertWhen_NodeOperatorIdIsOutOfRange() external {
        uint256 nodeOperatorsCount = baseModuleStub.getNodeOperatorsCount();

        vm.expectRevert("OUT_OF_RANGE_NODE_OPERATOR_ID");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(nodeOperatorsCount, LOCK_NONCE)))
        );
    }

    // python: test_create_evm_script
    function test_CreatesEVMScript() external {
        _lockBond(0);

        bytes memory evmScript = settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(0, LOCK_NONCE)))
        );

        assertEq(evmScript, _settleGeneralDelayedPenaltyScript(0, LOCK_NONCE), "evmScript");
    }

    // python: test_decode_evm_script_call_data
    function test_DecodesEVMScriptCallData() external view {
        SettleGeneralDelayedPenalty.LockInfo[] memory lockInfoList =
            _lockInfos(_lockInfo(0, 1000), _lockInfo(1, 2000), _lockInfo(2, 3000));

        SettleGeneralDelayedPenalty.LockInfo[] memory decoded =
            settleGeneralDelayedPenalty.decodeEVMScriptCallData(abi.encode(lockInfoList));

        assertEq(decoded.length, lockInfoList.length, "length");

        for (uint256 i; i < lockInfoList.length; ++i) {
            assertEq(decoded[i].nodeOperatorId, lockInfoList[i].nodeOperatorId, "nodeOperatorId");
            assertEq(decoded[i].nonce, lockInfoList[i].nonce, "nonce");
        }
    }

    // python: test_decode_evm_script_call_data_reverts_on_invalid_calldata[empty]
    function test_RevertWhen_DecodingEmptyCallData() external {
        vm.expectRevert(bytes(""));
        settleGeneralDelayedPenalty.decodeEVMScriptCallData("");
    }

    // python: test_decode_evm_script_call_data_reverts_on_invalid_calldata[malformed]
    function test_RevertWhen_DecodingMalformedCallData() external {
        vm.expectRevert(bytes(""));
        settleGeneralDelayedPenalty.decodeEVMScriptCallData(hex"01");
    }

    // python: test_lock_should_be_greater_than_zero
    function test_RevertWhen_NoLockToSettle() external {
        vm.expectRevert("NO_LOCK_TO_SETTLE");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(0, LOCK_NONCE)))
        );
    }

    // python: test_lock_should_have_expected_nonce
    function test_RevertWhen_LockNonceDiffers() external {
        _lockBond(0);

        vm.expectRevert("INVALID_LOCK_NONCE");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(0, LOCK_NONCE - 1)))
        );

        vm.expectRevert("INVALID_LOCK_NONCE");
        settleGeneralDelayedPenalty.createEVMScript(
            owner, abi.encode(_lockInfos(_lockInfo(0, LOCK_NONCE + 1)))
        );
    }

    /// @dev python: lock_bond fixture, accounting.mock_setLock(no_id, Wei(1), LOCK_NONCE)
    function _lockBond(uint256 nodeOperatorId) private {
        accountingStub.mock_setLock(nodeOperatorId, LOCKED_BOND, LOCK_NONCE);
    }

    function _lockInfo(uint256 nodeOperatorId, uint256 nonce)
        private
        pure
        returns (SettleGeneralDelayedPenalty.LockInfo memory)
    {
        return SettleGeneralDelayedPenalty.LockInfo({nodeOperatorId: nodeOperatorId, nonce: nonce});
    }

    function _lockInfos(SettleGeneralDelayedPenalty.LockInfo memory single)
        private
        pure
        returns (SettleGeneralDelayedPenalty.LockInfo[] memory lockInfos)
    {
        lockInfos = new SettleGeneralDelayedPenalty.LockInfo[](1);
        lockInfos[0] = single;
    }

    function _lockInfos(
        SettleGeneralDelayedPenalty.LockInfo memory first,
        SettleGeneralDelayedPenalty.LockInfo memory second
    ) private pure returns (SettleGeneralDelayedPenalty.LockInfo[] memory lockInfos) {
        lockInfos = new SettleGeneralDelayedPenalty.LockInfo[](2);
        lockInfos[0] = first;
        lockInfos[1] = second;
    }

    function _lockInfos(
        SettleGeneralDelayedPenalty.LockInfo memory first,
        SettleGeneralDelayedPenalty.LockInfo memory second,
        SettleGeneralDelayedPenalty.LockInfo memory third
    ) private pure returns (SettleGeneralDelayedPenalty.LockInfo[] memory lockInfos) {
        lockInfos = new SettleGeneralDelayedPenalty.LockInfo[](3);
        lockInfos[0] = first;
        lockInfos[1] = second;
        lockInfos[2] = third;
    }

    /// @dev python: encode_call_script of one module.settleGeneralDelayedPenalty([no_id], [nonce])
    function _settleGeneralDelayedPenaltyScript(uint256 nodeOperatorId, uint256 nonce)
        private
        view
        returns (bytes memory)
    {
        uint256[] memory nodeOperatorIds = new uint256[](1);
        nodeOperatorIds[0] = nodeOperatorId;

        uint256[] memory nonces = new uint256[](1);
        nonces[0] = nonce;

        return EVMScripts.encodeCallScript(
            address(baseModuleStub),
            abi.encodeWithSelector(
                IBaseModule.settleGeneralDelayedPenalty.selector, nodeOperatorIds, nonces
            )
        );
    }
}
