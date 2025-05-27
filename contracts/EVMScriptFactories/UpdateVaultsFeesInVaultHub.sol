// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../TrustedCaller.sol";
import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to update fees for multiple vaults in VaultHub
contract UpdateVaultsFeesInVaultHub is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of VaultHub
    IVaultHub public immutable vaultHub;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _vaultHub)
        TrustedCaller(_trustedCaller)
    {
        vaultHub = IVaultHub(_vaultHub);
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

        address toAddress = address(vaultHub);
        bytes4 methodId = IVaultHub.updateVaultFees.selector;
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
        require(_vaults.length > 0, "Empty vaults array");
        require(
            _vaults.length == _infraFeesBP.length &&
            _vaults.length == _liquidityFeesBP.length &&
            _vaults.length == _reservationFeesBP.length,
            "Array length mismatch"
        );
        
        for (uint256 i = 0; i < _vaults.length; i++) {
            require(_vaults[i] != address(0), "Zero vault address");
            require(_infraFeesBP[i] <= 10000, "Infra fee BP exceeds 100%");
            require(_liquidityFeesBP[i] <= 10000, "Liquidity fee BP exceeds 100%");
            require(_reservationFeesBP[i] <= 10000, "Reservation fee BP exceeds 100%");
            
            IVaultHub.VaultConnection memory connection = vaultHub.vaultConnection(_vaults[i]);
            require(connection.owner != address(0), "Vault not registered");
        }
    }
}
