// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to set the suspect window on one Lido Lend market's GuardianSignals registry
contract LidoLendSetSuspectWindow is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SAME_SUSPECT_WINDOW = "SAME_SUSPECT_WINDOW";
    string private constant ERROR_SUSPECT_WINDOW_TOO_HIGH = "SUSPECT_WINDOW_TOO_HIGH";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

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

        require(
            newSuspectWindow <= guardianSignals.MAX_SUSPECT_WINDOW(),
            ERROR_SUSPECT_WINDOW_TOO_HIGH
        );
        require(newSuspectWindow != guardianSignals.getSuspectWindow(), ERROR_SAME_SUSPECT_WINDOW);

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setGuardiansSuspectWindow.selector,
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

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, uint256 suspectWindow)
    {
        (marketId, suspectWindow) = abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
