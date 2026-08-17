// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to set the guardian quorum on one Lido Lend market's GuardianSignals registry
contract LidoLendSetGuardiansQuorum is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SAME_QUORUM = "SAME_QUORUM";
    string private constant ERROR_INVALID_QUORUM = "INVALID_QUORUM";

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to set the guardian quorum on one Lido Lend market's GuardianSignals registry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 quorum)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newQuorum) = _decodeEVMScriptCallData(_evmScriptCallData);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(newQuorum != guardianSignals.getQuorum(), ERROR_SAME_QUORUM);
        require(
            newQuorum != 0 && newQuorum <= guardianSignals.getGuardianCount(),
            ERROR_INVALID_QUORUM
        );

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setGuardiansQuorum.selector,
                abi.encode(marketId, newQuorum)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, uint256 quorum)
    /// @return marketId Id of the market whose registry to set
    /// @return quorum New quorum
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, uint256 quorum)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, uint256 quorum)
    {
        (marketId, quorum) = abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
