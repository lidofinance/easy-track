// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendFactoryBase.sol";

/// @notice Creates EVMScripts for shared Lido Lend CircuitBreaker actions
contract LidoLendCircuitBreakerActions is LidoLendFactoryBase, IEVMScriptFactory {
    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        RegisterPauser,
        SetPauseDuration,
        SetHeartbeatInterval
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_CIRCUIT_BREAKER_NOT_PAUSER = "CIRCUIT_BREAKER_NOT_PAUSER";
    string private constant ERROR_PAUSE_DURATION_OUT_OF_RANGE = "PAUSE_DURATION_OUT_OF_RANGE";
    string private constant ERROR_HEARTBEAT_INTERVAL_OUT_OF_RANGE =
        "HEARTBEAT_INTERVAL_OUT_OF_RANGE";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the CircuitBreaker instance
    address public immutable circuitBreaker;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(
        address _trustedCaller,
        address _lidoLend,
        address _circuitBreaker
    ) LidoLendFactoryBase(_trustedCaller, _lidoLend) {
        circuitBreaker = _circuitBreaker;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for one CircuitBreaker action
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded envelope: abi.encode(Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);
        if (action == Action.RegisterPauser) {
            return _createRegisterPauserEVMScript(payload);
        }
        if (action == Action.SetPauseDuration) {
            return _createSetPauseDurationEVMScript(payload);
        }
        if (action == Action.SetHeartbeatInterval) {
            return _createSetHeartbeatIntervalEVMScript(payload);
        }
        revert(ERROR_INVALID_ACTION);
    }

    /// @notice Decodes the action envelope used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes RegisterPauser payload: (bytes32 marketId, address pauser)
    /// @return marketId Id of the market
    /// @return pauser New pauser address; zero unregisters the current pauser
    function decodeRegisterPauserPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, address pauser)
    {
        (marketId, pauser) = abi.decode(_payload, (bytes32, address));
    }

    /// @notice Decodes the uint256 payload shared by CircuitBreaker configuration actions
    function decodeConfigValuePayload(bytes memory _payload) public pure returns (uint256 value) {
        value = abi.decode(_payload, (uint256));
    }

    function _createRegisterPauserEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address pauser) = decodeRegisterPauserPayload(_payload);
        ILidoLendMarketController marketController = _getMarketControllerOrRevert(marketId);
        if (pauser != address(0)) {
            require(
                marketController.hasRole(marketController.PAUSER_ROLE(), circuitBreaker),
                ERROR_CIRCUIT_BREAKER_NOT_PAUSER
            );
        }

        return
            EVMScriptCreator.createEVMScript(
                circuitBreaker,
                ICircuitBreaker.registerPauser.selector,
                abi.encode(address(marketController), pauser)
            );
    }

    function _createSetPauseDurationEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        uint256 newPauseDuration = decodeConfigValuePayload(_payload);
        ICircuitBreaker breaker = ICircuitBreaker(circuitBreaker);
        require(
            newPauseDuration >= breaker.MIN_PAUSE_DURATION() &&
                newPauseDuration <= breaker.MAX_PAUSE_DURATION(),
            ERROR_PAUSE_DURATION_OUT_OF_RANGE
        );
        return
            EVMScriptCreator.createEVMScript(
                circuitBreaker,
                breaker.setPauseDuration.selector,
                abi.encode(newPauseDuration)
            );
    }

    function _createSetHeartbeatIntervalEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        uint256 newHeartbeatInterval = decodeConfigValuePayload(_payload);
        ICircuitBreaker breaker = ICircuitBreaker(circuitBreaker);
        require(
            newHeartbeatInterval >= breaker.MIN_HEARTBEAT_INTERVAL() &&
                newHeartbeatInterval <= breaker.MAX_HEARTBEAT_INTERVAL(),
            ERROR_HEARTBEAT_INTERVAL_OUT_OF_RANGE
        );
        return
            EVMScriptCreator.createEVMScript(
                circuitBreaker,
                breaker.setHeartbeatInterval.selector,
                abi.encode(newHeartbeatInterval)
            );
    }
}
