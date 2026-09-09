// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/ILido.sol";

/// @author dgusakov
/// @notice Creates EVMScript to set deposits reserve target for Lido
contract SetDepositsReserveTarget is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_DEPOSITS_RESERVE_TARGET_TOO_HIGH =
        "DEPOSITS_RESERVE_TARGET_TOO_HIGH";
    string private constant ERROR_SAME_DEPOSITS_RESERVE_TARGET = "SAME_DEPOSITS_RESERVE_TARGET";

    // -------------
    // IMMUTABLES
    // -------------
    uint256 public immutable MAX_DEPOSITS_RESERVE_TARGET;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of Lido contract
    ILido public immutable lido;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @notice Creates SetDepositsReserveTarget factory
    /// @param _trustedCaller Address of trusted caller (e.g. Easy Track)
    /// @param _maxDepositsReserveTarget Maximum allowed deposits reserve target in wei
    /// @param _lido Address of Lido contract
    constructor(
        address _trustedCaller,
        uint256 _maxDepositsReserveTarget,
        address _lido
    ) TrustedCaller(_trustedCaller) {
        MAX_DEPOSITS_RESERVE_TARGET = _maxDepositsReserveTarget;
        lido = ILido(_lido);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set deposits reserve target for Lido
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded value for deposits reserve target:
    ///    uint256 newDepositsReserveTarget
    function createEVMScript(
        address _creator,
        bytes calldata _evmScriptCallData
    ) external view override onlyTrustedCaller(_creator) returns (bytes memory) {
        uint256 newDepositsReserveTarget = _decodeEVMScriptCallData(_evmScriptCallData);

        if (newDepositsReserveTarget > MAX_DEPOSITS_RESERVE_TARGET) {
            revert(ERROR_DEPOSITS_RESERVE_TARGET_TOO_HIGH);
        }
        if (newDepositsReserveTarget == lido.getDepositsReserveTarget()) {
            revert(ERROR_SAME_DEPOSITS_RESERVE_TARGET);
        }

        return
            EVMScriptCreator.createEVMScript(
                address(lido),
                lido.setDepositsReserveTarget.selector,
                _evmScriptCallData
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded value for deposits reserve target: uint256 newDepositsReserveTarget
    /// @return newDepositsReserveTarget The new deposits reserve target
    function decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) external pure returns (uint256 newDepositsReserveTarget) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes calldata _evmScriptCallData
    ) private pure returns (uint256 newDepositsReserveTarget) {
        return abi.decode(_evmScriptCallData, (uint256));
    }
}
