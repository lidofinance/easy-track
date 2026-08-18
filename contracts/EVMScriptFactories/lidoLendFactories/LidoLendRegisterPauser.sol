// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScript to register, replace, or unregister a pauser for one Lido Lend market
contract LidoLendRegisterPauser is TrustedCaller, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_ZERO_CONTROLLER = "ZERO_CONTROLLER";
    string private constant ERROR_CIRCUIT_BREAKER_NOT_PAUSER = "CIRCUIT_BREAKER_NOT_PAUSER";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the LidoLend core
    address public immutable lidoLend;
    /// @notice Address of the CircuitBreaker instance
    address public immutable circuitBreaker;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLend,
        address _circuitBreaker
    ) TrustedCaller(_trustedCaller) {
        lidoLend = _lidoLend;
        circuitBreaker = _circuitBreaker;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to register, replace, or unregister a pauser for one Lido Lend market
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address pauser)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, address pauser) = _decodeEVMScriptCallData(_evmScriptCallData);

        address controller = ILidoLend(lidoLend).marketController(marketId);
        require(controller != address(0), ERROR_ZERO_CONTROLLER);
        ILidoLendMarketController marketController = ILidoLendMarketController(controller);
        require(
            marketController.hasRole(marketController.PAUSER_ROLE(), circuitBreaker),
            ERROR_CIRCUIT_BREAKER_NOT_PAUSER
        );

        return
            EVMScriptCreator.createEVMScript(
                circuitBreaker,
                ICircuitBreaker.registerPauser.selector,
                abi.encode(controller, pauser)
            );
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, address pauser)
    /// @return marketId Id of the market
    /// @return pauser Pauser address to register
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, address pauser)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, address pauser)
    {
        (marketId, pauser) = abi.decode(_evmScriptCallData, (bytes32, address));
    }
}
