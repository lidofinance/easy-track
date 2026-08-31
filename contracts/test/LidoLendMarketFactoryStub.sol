// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ILidoLend.sol";

contract LidoLendMarketFactoryStub {
    address public expectedController;
    bytes32 public expectedMarketId;
    address public expectedGuardianSignals;
    address public expectedWrapper;
    bytes32 public expectedMarketParamsHash;
    bool public rejectControllerValidation;
    bool public rejectWrapperValidation;

    function setExpectedValidation(
        address controller,
        bytes32 marketId,
        address guardianSignals,
        address wrapper,
        MarketParams calldata marketParams
    ) external {
        expectedController = controller;
        expectedMarketId = marketId;
        expectedGuardianSignals = guardianSignals;
        expectedWrapper = wrapper;
        expectedMarketParamsHash = keccak256(abi.encode(marketParams));
    }

    function setRejectControllerValidation(bool value) external {
        rejectControllerValidation = value;
    }

    function setRejectWrapperValidation(bool value) external {
        rejectWrapperValidation = value;
    }

    function validateMarketController(
        address controller,
        bytes32 marketId,
        address guardianSignals
    ) external view {
        require(
            !rejectControllerValidation &&
                controller == expectedController &&
                marketId == expectedMarketId &&
                guardianSignals == expectedGuardianSignals,
            "INVALID_CONTROLLER_VALIDATION"
        );
    }

    function validateERC4626Wrapper(
        address wrapper,
        address controller,
        MarketParams calldata marketParams
    ) external view {
        require(
            !rejectWrapperValidation &&
                wrapper == expectedWrapper &&
                controller == expectedController &&
                keccak256(abi.encode(marketParams)) == expectedMarketParamsHash,
            "INVALID_WRAPPER_VALIDATION"
        );
    }
}
