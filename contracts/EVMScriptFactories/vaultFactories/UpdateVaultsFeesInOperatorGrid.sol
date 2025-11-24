// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultsAdapter.sol";
import "../../interfaces/IOperatorGrid.sol";
import "../../interfaces/ILidoLocator.sol";

/// @author dry914
/// @notice Creates EVMScript to update fees for multiple vaults in OperatorGrid
/// @notice This motion might be temporary non-enactable, requiring a fresh report to be presented for each vault
contract UpdateVaultsFeesInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_ADAPTER = "ZERO_ADAPTER";
    string private constant ERROR_ZERO_LIDO_LOCATOR = "ZERO_LIDO_LOCATOR";
    string private constant ERROR_EMPTY_VAULTS = "EMPTY_VAULTS";
    string private constant ERROR_ARRAY_LENGTH_MISMATCH = "ARRAY_LENGTH_MISMATCH";
    string private constant ERROR_ZERO_VAULT = "ZERO_VAULT";
    string private constant ERROR_INFRA_FEE_TOO_HIGH = "INFRA_FEE_TOO_HIGH";
    string private constant ERROR_LIQUIDITY_FEE_TOO_HIGH = "LIQUIDITY_FEE_TOO_HIGH";
    string private constant ERROR_RESERVATION_FEE_TOO_HIGH = "RESERVATION_FEE_TOO_HIGH";

    // -------------
    // CONSTANTS
    // -------------

    /// @dev max value for fees in basis points - it's about 650%
    uint256 internal constant MAX_FEE_BP = type(uint16).max;

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of Vaults adapter
    IVaultsAdapter public immutable vaultsAdapter;

    /// @notice Address of Lido Locator
    ILidoLocator public immutable lidoLocator;

    /// @notice Maximum fee basis points
    uint256 public immutable maxLiquidityFeeBP;
    uint256 public immutable maxReservationFeeBP;
    uint256 public immutable maxInfraFeeBP;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _adapter, address _lidoLocator, uint256 _maxLiquidityFeeBP, uint256 _maxReservationFeeBP, uint256 _maxInfraFeeBP)
        TrustedCaller(_trustedCaller)
    {
        require(_adapter != address(0), ERROR_ZERO_ADAPTER);
        require(_lidoLocator != address(0), ERROR_ZERO_LIDO_LOCATOR);
        vaultsAdapter = IVaultsAdapter(_adapter);
        lidoLocator = ILidoLocator(_lidoLocator);

        require(_maxLiquidityFeeBP <= MAX_FEE_BP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
        require(_maxReservationFeeBP <= MAX_FEE_BP, ERROR_RESERVATION_FEE_TOO_HIGH);
        require(_maxInfraFeeBP <= MAX_FEE_BP, ERROR_INFRA_FEE_TOO_HIGH);
        maxLiquidityFeeBP = _maxLiquidityFeeBP;
        maxReservationFeeBP = _maxReservationFeeBP;
        maxInfraFeeBP = _maxInfraFeeBP;
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update fees for multiple vaults in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _infraFeesBP, uint256[] _liquidityFeesBP, uint256[] _reservationFeesBP
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _vaults,
            uint256[] memory _infraFeesBP,
            uint256[] memory _liquidityFeesBP,
            uint256[] memory _reservationFeesBP
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_vaults, _infraFeesBP, _liquidityFeesBP, _reservationFeesBP);

        address toAddress = address(vaultsAdapter);
        bytes4 methodId = vaultsAdapter.updateVaultFees.selector;
        bytes[] memory calldataArray = new bytes[](_vaults.length);

        for (uint256 i = 0; i < _vaults.length; i++) {
            calldataArray[i] = abi.encode(
                _vaults[i],
                _infraFeesBP[i],
                _liquidityFeesBP[i],
                _reservationFeesBP[i]
            );
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodId, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: address[] _vaults, uint256[] _infraFeesBP, uint256[] _liquidityFeesBP, uint256[] _reservationFeesBP
    /// @return Vault addresses and new fee values in basis points
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory, uint256[] memory, uint256[] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory, uint256[] memory, uint256[] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[], uint256[], uint256[]));
    }

    function _validateInputData(
        address[] memory _vaults,
        uint256[] memory _infraFeesBP,
        uint256[] memory _liquidityFeesBP,
        uint256[] memory _reservationFeesBP
    ) private view {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(
            _vaults.length == _infraFeesBP.length &&
            _vaults.length == _liquidityFeesBP.length &&
            _vaults.length == _reservationFeesBP.length,
            ERROR_ARRAY_LENGTH_MISMATCH
        );

        IOperatorGrid operatorGrid = IOperatorGrid(lidoLocator.operatorGrid());

        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);

            (,,,,,uint256 tierInfraFeeBP,uint256 tierLiquidityFeeBP,uint256 tierReservationFeeBP
                ) = operatorGrid.vaultTierInfo(_vaults[i]);
            require(_infraFeesBP[i] <= tierInfraFeeBP, ERROR_INFRA_FEE_TOO_HIGH);
            require(_infraFeesBP[i] <= maxInfraFeeBP, ERROR_INFRA_FEE_TOO_HIGH);
            require(_liquidityFeesBP[i] <= tierLiquidityFeeBP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
            require(_liquidityFeesBP[i] <= maxLiquidityFeeBP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
            require(_reservationFeesBP[i] <= tierReservationFeeBP, ERROR_RESERVATION_FEE_TOO_HIGH);
            require(_reservationFeesBP[i] <= maxReservationFeeBP, ERROR_RESERVATION_FEE_TOO_HIGH);
            // more checks in adapter function to prevent motion failure in case vault disconnected while motion is in progress
        }
    }
}
