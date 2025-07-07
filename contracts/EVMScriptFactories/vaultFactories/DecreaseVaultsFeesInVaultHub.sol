// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IVaultHubAdapter.sol";

/// @author dry914
/// @notice Creates EVMScript to update fees for multiple vaults in VaultHub
contract DecreaseVaultsFeesInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // ERROR MESSAGES
    // -------------

    string private constant ERROR_ZERO_ADAPTER = "ZERO_ADAPTER";
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

    /// @notice Address of VaultHub adapter
    IVaultHubAdapter public immutable vaultHubAdapter;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _adapter)
        TrustedCaller(_trustedCaller)
    {   
        require(_adapter != address(0), ERROR_ZERO_ADAPTER);
        vaultHubAdapter = IVaultHubAdapter(_adapter);
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to update fees for multiple vaults in VaultHub
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

        address toAddress = address(vaultHubAdapter);
        bytes4 methodId = vaultHubAdapter.updateVaultFees.selector;
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
    ) private pure {
        require(_vaults.length > 0, ERROR_EMPTY_VAULTS);
        require(
            _vaults.length == _infraFeesBP.length &&
            _vaults.length == _liquidityFeesBP.length &&
            _vaults.length == _reservationFeesBP.length,
            ERROR_ARRAY_LENGTH_MISMATCH
        );
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), ERROR_ZERO_VAULT);
            require(_infraFeesBP[i] <= MAX_FEE_BP, ERROR_INFRA_FEE_TOO_HIGH);
            require(_liquidityFeesBP[i] <= MAX_FEE_BP, ERROR_LIQUIDITY_FEE_TOO_HIGH);
            require(_reservationFeesBP[i] <= MAX_FEE_BP, ERROR_RESERVATION_FEE_TOO_HIGH);
            // more checks in adapter function to prevent motion failure in case vault disconnected while motion is in progress
        }
    }
}
