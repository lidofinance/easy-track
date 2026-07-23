// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to replace a guardian (remove old + add new) on one Lido Lend market's registry
contract LidoLendReplaceGuardian is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_GUARDIAN = "ZERO_GUARDIAN";
    string private constant ERROR_GUARDIAN_NOT_FOUND = "GUARDIAN_NOT_FOUND";
    string private constant ERROR_GUARDIAN_ALREADY_ADDED = "GUARDIAN_ALREADY_ADDED";
    string private constant ERROR_WOULD_BREAK_QUORUM = "WOULD_BREAK_QUORUM";
    string private constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLendOwner facade
    ILidoLendOwner public immutable lidoLendOwner;
    /// @notice Address of the LidoLend core (resolves a market's controller by id, for validation)
    ILidoLend public immutable lidoLend;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner) TrustedCaller(_trustedCaller) {
        lidoLendOwner = ILidoLendOwner(_lidoLendOwner);
        lidoLend = ILidoLendOwner(_lidoLendOwner).LIDO_LEND();
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to replace a guardian (remove old + add new) on one Lido Lend market's registry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address oldGuardian, address newGuardian)
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
        require(
            guardianSignals.getGuardianCount() > guardianSignals.getQuorum(),
            ERROR_WOULD_BREAK_QUORUM
        );

        address[] memory to = new address[](2);
        to[0] = address(lidoLendOwner);
        to[1] = address(lidoLendOwner);

        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = lidoLendOwner.removeGuardian.selector;
        methodIds[1] = lidoLendOwner.addGuardian.selector;

        bytes[] memory callData = new bytes[](2);
        callData[0] = abi.encode(marketId, oldGuardian);
        callData[1] = abi.encode(marketId, newGuardian);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address oldGuardian, address newGuardian)
    /// @return marketId Id of the market whose registry to edit
    /// @return oldGuardian Guardian address to remove
    /// @return newGuardian Guardian address to add
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

    function _guardianSignalsOf(bytes32 marketId) private view returns (IGuardianSignals) {
        address controller = lidoLend.marketController(marketId);
        require(controller != address(0), ERROR_MARKET_NOT_FOUND);
        return IGuardianSignals(ILidoLendMarketController(controller).guardianSignals());
    }

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
