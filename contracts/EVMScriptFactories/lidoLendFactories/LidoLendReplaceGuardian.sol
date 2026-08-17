// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to atomically replace a guardian through the LidoLendOwner facade
/// @dev The facade selects a safe add/remove order and temporarily adjusts a full quorum when necessary.
contract LidoLendReplaceGuardian is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_GUARDIAN = "ZERO_GUARDIAN";
    string private constant ERROR_GUARDIAN_NOT_FOUND = "GUARDIAN_NOT_FOUND";
    string private constant ERROR_GUARDIAN_ALREADY_ADDED = "GUARDIAN_ALREADY_ADDED";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to replace one guardian with another
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address oldGuardian, address newGuardian)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address oldGuardian, address newGuardian) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        require(newGuardian != address(0), ERROR_ZERO_GUARDIAN);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(guardianSignals.isGuardian(oldGuardian), ERROR_GUARDIAN_NOT_FOUND);
        require(!guardianSignals.isGuardian(newGuardian), ERROR_GUARDIAN_ALREADY_ADDED);

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.replaceGuardian.selector,
                abi.encode(marketId, oldGuardian, newGuardian)
            );
    }

    /// @notice Decodes call data used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            bytes32 marketId,
            address oldGuardian,
            address newGuardian
        )
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (
            bytes32 marketId,
            address oldGuardian,
            address newGuardian
        )
    {
        (marketId, oldGuardian, newGuardian) = abi.decode(
            _evmScriptCallData,
            (bytes32, address, address)
        );
    }
}
