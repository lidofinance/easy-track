// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to remove a guardian from one Lido Lend market's GuardianSignals registry
contract LidoLendRemoveGuardian is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_GUARDIAN_NOT_FOUND = "GUARDIAN_NOT_FOUND";
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

    /// @notice Creates EVMScript to remove a guardian from one Lido Lend market's GuardianSignals registry
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address guardian, uint256 newQuorum)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address guardian, uint256 newQuorum) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(guardianSignals.isGuardian(guardian), ERROR_GUARDIAN_NOT_FOUND);
        require(
            newQuorum != 0 && newQuorum < guardianSignals.getGuardianCount(),
            ERROR_INVALID_QUORUM
        );

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = owner.setGuardiansQuorum.selector;
        methodIds[1] = owner.removeGuardian.selector;

        bytes[] memory encodedCalldata = new bytes[](2);
        encodedCalldata[0] = abi.encode(marketId, newQuorum);
        encodedCalldata[1] = abi.encode(marketId, guardian);

        return EVMScriptCreator.createEVMScript(lidoLendOwner, methodIds, encodedCalldata);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded (bytes32 marketId, address guardian, uint256 newQuorum)
    /// @return marketId Id of the market whose registry to remove from
    /// @return guardian Guardian address to remove
    /// @return newQuorum Quorum to set before removing the guardian
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (
            bytes32 marketId,
            address guardian,
            uint256 newQuorum
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
            address guardian,
            uint256 newQuorum
        )
    {
        (marketId, guardian, newQuorum) = abi.decode(
            _evmScriptCallData,
            (bytes32, address, uint256)
        );
    }
}
