// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Creates EVMScripts for the manager actions of the Lido Lend Trailing Anchor Oracles
/// @dev Each script calls the Trailing Anchor Oracle adapter, which holds MANAGER_ROLE on the oracles. The
///      factory checks the parameters against the range checks of the oracle. It does not check the sizing
///      rule, because it does not know the markets that read the oracle. The motion reviewers must check the
///      sizing rule for each market that reads the oracle.
contract LidoLendTrailingAnchorOracleActions is TrustedCaller, IEVMScriptFactory {
    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        SetParameters,
        SetPricingResumesAt
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_ZERO_ADAPTER = "ZERO_ADAPTER";
    string private constant ERROR_ZERO_ORACLE = "ZERO_ORACLE";
    string private constant ERROR_ORACLE_NOT_MANAGED = "ORACLE_NOT_MANAGED";
    string private constant ERROR_MAX_PRICE_ABOVE_ANCHOR_IS_ZERO = "MAX_PRICE_ABOVE_ANCHOR_IS_ZERO";
    string private constant ERROR_MAX_PRICE_BELOW_ANCHOR_IS_ZERO = "MAX_PRICE_BELOW_ANCHOR_IS_ZERO";
    string private constant ERROR_MAX_PRICE_ABOVE_ANCHOR_NOT_BELOW_WAD =
        "MAX_PRICE_ABOVE_ANCHOR_NOT_BELOW_WAD";
    string private constant ERROR_MAX_PRICE_BELOW_ANCHOR_NOT_BELOW_WAD =
        "MAX_PRICE_BELOW_ANCHOR_NOT_BELOW_WAD";
    string private constant ERROR_MAX_ANCHOR_BELOW_BASE_NOT_BELOW_WAD =
        "MAX_ANCHOR_BELOW_BASE_NOT_BELOW_WAD";
    string private constant ERROR_MAX_ANCHOR_ABOVE_BASE_NOT_BELOW_WAD =
        "MAX_ANCHOR_ABOVE_BASE_NOT_BELOW_WAD";
    string private constant ERROR_MAX_ANCHOR_CONTINUOUS_RISE_RATE_EXCEEDS_WAD =
        "MAX_ANCHOR_CONTINUOUS_RISE_RATE_EXCEEDS_WAD";
    string private constant ERROR_MAX_ANCHOR_CONTINUOUS_FALL_RATE_EXCEEDS_WAD =
        "MAX_ANCHOR_CONTINUOUS_FALL_RATE_EXCEEDS_WAD";
    string private constant ERROR_REANCHOR_DELAY_BELOW_MIN_REANCHOR_DELAY =
        "REANCHOR_DELAY_BELOW_MIN_REANCHOR_DELAY";
    string private constant ERROR_REANCHOR_WINDOW_BELOW_MIN_REANCHOR_WINDOW =
        "REANCHOR_WINDOW_BELOW_MIN_REANCHOR_WINDOW";
    string private constant ERROR_RISE_OVER_DELAY_EXCEEDS_MAX_PRICE_ABOVE_ANCHOR =
        "RISE_OVER_DELAY_EXCEEDS_MAX_PRICE_ABOVE_ANCHOR";
    string private constant ERROR_FALL_OVER_DELAY_EXCEEDS_MAX_PRICE_BELOW_ANCHOR =
        "FALL_OVER_DELAY_EXCEEDS_MAX_PRICE_BELOW_ANCHOR";
    string private constant ERROR_SAME_PARAMETERS = "SAME_PARAMETERS";
    string private constant ERROR_PRICING_RESUMES_AT_NOT_IN_FUTURE =
        "PRICING_RESUMES_AT_NOT_IN_FUTURE";
    string private constant ERROR_INVALID_PRICING_RESUMES_AT = "INVALID_PRICING_RESUMES_AT";

    // -------------
    // CONSTANTS
    // -------------

    uint256 private constant WAD = 1e18;
    // Mirrors YEAR in lido-lend-markets/src/oracle/TrailingAnchorOracleBase.sol.
    uint256 private constant YEAR = 365 days;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of the Trailing Anchor Oracle adapter
    address public immutable adapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _adapter) TrustedCaller(_trustedCaller) {
        require(_adapter != address(0), ERROR_ZERO_ADAPTER);
        adapter = _adapter;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for one manager action of an oracle
    /// @param _creator Address that creates the EVMScript
    /// @param _evmScriptCallData Encoded envelope: abi.encode(Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.SetParameters) {
            return _createSetParametersEVMScript(payload);
        }
        if (action == Action.SetPricingResumesAt) {
            return _createSetPricingResumesAtEVMScript(payload);
        }
        revert(ERROR_INVALID_ACTION);
    }

    // -------------
    // PUBLIC DECODERS
    // -------------

    /// @notice Decodes the outer action envelope used by createEVMScript
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes a SetParameters payload
    /// @return oracle Address of the Trailing Anchor Oracle
    /// @return parameters New parameters of the oracle
    function decodeSetParametersPayload(bytes memory _payload)
        public
        pure
        returns (address oracle, ITrailingAnchorOracle.Parameters memory parameters)
    {
        (oracle, parameters) = abi.decode(_payload, (address, ITrailingAnchorOracle.Parameters));
    }

    /// @notice Decodes a SetPricingResumesAt payload
    /// @return oracle Address of the Trailing Anchor Oracle
    /// @return resumesAt Time at which pricing resumes; zero ends the suspension
    function decodeSetPricingResumesAtPayload(bytes memory _payload)
        public
        pure
        returns (address oracle, uint40 resumesAt)
    {
        (oracle, resumesAt) = abi.decode(_payload, (address, uint40));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createSetParametersEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (
            address oracle,
            ITrailingAnchorOracle.Parameters memory parameters
        ) = decodeSetParametersPayload(_payload);
        _requireManagedOracle(oracle);
        _validateParameters(ITrailingAnchorOracle(oracle), parameters);
        // A call with the current values would only drop the pending anchor of the oracle.
        require(
            keccak256(abi.encode(parameters)) !=
                keccak256(abi.encode(_currentParameters(ITrailingAnchorOracle(oracle)))),
            ERROR_SAME_PARAMETERS
        );

        return
            EVMScriptCreator.createEVMScript(
                adapter,
                ILidoLendTrailingAnchorOracleAdapter.setParameters.selector,
                abi.encode(oracle, parameters)
            );
    }

    function _createSetPricingResumesAtEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (address oracle, uint40 resumesAt) = decodeSetPricingResumesAtPayload(_payload);
        _requireManagedOracle(oracle);
        // Anyone can enact a motion at any time after it passes. A suspension motion that is enacted after
        // its end time would end a newer suspension. Thus only zero can end a suspension.
        require(
            resumesAt == 0 || resumesAt > block.timestamp,
            ERROR_PRICING_RESUMES_AT_NOT_IN_FUTURE
        );
        // EasyTrack runs this check when the motion is created and again when it is enacted. Thus the
        // suspension ends at most MAX_PRICING_SUSPENSION after the creation of the motion.
        require(
            resumesAt <= block.timestamp + ITrailingAnchorOracle(oracle).MAX_PRICING_SUSPENSION(),
            ERROR_INVALID_PRICING_RESUMES_AT
        );

        return
            EVMScriptCreator.createEVMScript(
                adapter,
                ILidoLendTrailingAnchorOracleAdapter.setPricingResumesAt.selector,
                abi.encode(oracle, resumesAt)
            );
    }

    /// @dev The adapter can change only an oracle that gave it MANAGER_ROLE. The check makes a motion for
    ///      another oracle fail when it is created, not when it is enacted.
    function _requireManagedOracle(address _oracle) private view {
        require(_oracle != address(0), ERROR_ZERO_ORACLE);
        ITrailingAnchorOracle oracle = ITrailingAnchorOracle(_oracle);
        require(oracle.hasRole(oracle.MANAGER_ROLE(), adapter), ERROR_ORACLE_NOT_MANAGED);
    }

    function _currentParameters(ITrailingAnchorOracle _oracle)
        private
        view
        returns (ITrailingAnchorOracle.Parameters memory)
    {
        return
            ITrailingAnchorOracle.Parameters({
                maxPriceAboveAnchor: _oracle.maxPriceAboveAnchor(),
                maxPriceBelowAnchor: _oracle.maxPriceBelowAnchor(),
                maxAnchorContinuousRiseRate: _oracle.maxAnchorContinuousRiseRate(),
                maxAnchorContinuousFallRate: _oracle.maxAnchorContinuousFallRate(),
                maxAnchorBelowBase: _oracle.maxAnchorBelowBase(),
                maxAnchorAboveBase: _oracle.maxAnchorAboveBase(),
                reanchorDelay: _oracle.reanchorDelay(),
                reanchorWindow: _oracle.reanchorWindow()
            });
    }

    /// @dev Mirrors the checks of _setParameters in lido-lend-markets/src/oracle/TrailingAnchorOracleBase.sol,
    ///      in the same order.
    function _validateParameters(
        ITrailingAnchorOracle _oracle,
        ITrailingAnchorOracle.Parameters memory _parameters
    ) private view {
        require(_parameters.maxPriceAboveAnchor != 0, ERROR_MAX_PRICE_ABOVE_ANCHOR_IS_ZERO);
        require(_parameters.maxPriceBelowAnchor != 0, ERROR_MAX_PRICE_BELOW_ANCHOR_IS_ZERO);
        require(_parameters.maxPriceAboveAnchor < WAD, ERROR_MAX_PRICE_ABOVE_ANCHOR_NOT_BELOW_WAD);
        require(_parameters.maxPriceBelowAnchor < WAD, ERROR_MAX_PRICE_BELOW_ANCHOR_NOT_BELOW_WAD);
        require(_parameters.maxAnchorBelowBase < WAD, ERROR_MAX_ANCHOR_BELOW_BASE_NOT_BELOW_WAD);
        require(_parameters.maxAnchorAboveBase < WAD, ERROR_MAX_ANCHOR_ABOVE_BASE_NOT_BELOW_WAD);
        require(
            _parameters.maxAnchorContinuousRiseRate <= WAD,
            ERROR_MAX_ANCHOR_CONTINUOUS_RISE_RATE_EXCEEDS_WAD
        );
        require(
            _parameters.maxAnchorContinuousFallRate <= WAD,
            ERROR_MAX_ANCHOR_CONTINUOUS_FALL_RATE_EXCEEDS_WAD
        );
        require(
            _parameters.reanchorDelay >= _oracle.MIN_REANCHOR_DELAY(),
            ERROR_REANCHOR_DELAY_BELOW_MIN_REANCHOR_DELAY
        );
        require(
            _parameters.reanchorWindow >= _oracle.MIN_REANCHOR_WINDOW(),
            ERROR_REANCHOR_WINDOW_BELOW_MIN_REANCHOR_WINDOW
        );
        // A source that moves at a rate must stay inside its bound for one delay.
        require(
            _compoundedRise(_parameters.maxAnchorContinuousRiseRate, _parameters.reanchorDelay) <=
                _parameters.maxPriceAboveAnchor,
            ERROR_RISE_OVER_DELAY_EXCEEDS_MAX_PRICE_ABOVE_ANCHOR
        );
        require(
            _compoundedFall(_parameters.maxAnchorContinuousFallRate, _parameters.reanchorDelay) <=
                _parameters.maxPriceBelowAnchor,
            ERROR_FALL_OVER_DELAY_EXCEEDS_MAX_PRICE_BELOW_ANCHOR
        );
    }

    /// @dev e^(rate * elapsed / YEAR) - 1 from its first three Taylor terms, WAD, each term rounded down.
    ///      Mirrors _compoundedRise in lido-lend-markets/src/oracle/TrailingAnchorOracleBase.sol.
    function _compoundedRise(uint256 _rate, uint256 _elapsed) private pure returns (uint256) {
        uint256 firstTerm = (_rate * _elapsed) / YEAR;
        uint256 secondTerm = (firstTerm * firstTerm) / (2 * WAD);
        uint256 thirdTerm = (secondTerm * firstTerm) / (3 * WAD);
        return firstTerm + secondTerm + thirdTerm;
    }

    /// @dev 1 - e^(-rate * elapsed / YEAR), computed as c / (1 + c) with c from `_compoundedRise`, WAD,
    ///      rounded down. Mirrors _compoundedFall in lido-lend-markets/src/oracle/TrailingAnchorOracleBase.sol.
    function _compoundedFall(uint256 _rate, uint256 _elapsed) private pure returns (uint256) {
        uint256 compounded = _compoundedRise(_rate, _elapsed);
        return (compounded * WAD) / (WAD + compounded);
    }
}
