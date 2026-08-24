// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to set a Lido Lend market fee through the owner facade
contract LidoLendSetFee is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    string private constant ERROR_FEE_ALREADY_SET = "FEE_ALREADY_SET";

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    /// @param _evmScriptCallData Encoded tuple: (bytes32 marketId, uint256 newFee)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newFee) = _decodeEVMScriptCallData(_evmScriptCallData);
        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        ILidoLend core = owner.LIDO_LEND();
        Market memory currentMarket = core.market(marketId);
        require(currentMarket.lastUpdate != 0, ERROR_MARKET_NOT_FOUND);
        require(currentMarket.fee != newFee, ERROR_FEE_ALREADY_SET);

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                owner.setFee.selector,
                abi.encode(core.idToMarketParams(marketId), newFee)
            );
    }

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32 marketId, uint256 newFee)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32 marketId, uint256 newFee)
    {
        return abi.decode(_evmScriptCallData, (bytes32, uint256));
    }
}
