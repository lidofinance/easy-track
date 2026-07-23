// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to set the suspect window on one Lido Lend market's GuardianSignals registry
contract LidoLendSetSuspectWindow is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SAME_SUSPECT_WINDOW = "SAME_SUSPECT_WINDOW";
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

    /// @notice Creates EVMScript to set the suspect window on one Lido Lend market's GuardianSignals registry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 suspectWindow)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newSuspectWindow) = _decodeEVMScriptCallData(_evmScriptCallData);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(newSuspectWindow != guardianSignals.getSuspectWindow(), ERROR_SAME_SUSPECT_WINDOW);

        return
            EVMScriptCreator.createEVMScript(
                address(lidoLendOwner),
                lidoLendOwner.setGuardiansSuspectWindow.selector,
                abi.encode(marketId, newSuspectWindow)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 suspectWindow)
    /// @return marketId Id of the market whose registry to set
    /// @return suspectWindow New suspect window
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, uint256 suspectWindow)
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
        returns (bytes32 marketId, uint256 suspectWindow)
    {
        (marketId, suspectWindow) = abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
