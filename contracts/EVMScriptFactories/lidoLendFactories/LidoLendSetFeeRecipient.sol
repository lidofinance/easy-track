// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScript to accrue listed Lido Lend markets before changing the global fee recipient
contract LidoLendSetFeeRecipient is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_FEE_RECIPIENT_ALREADY_SET = "FEE_RECIPIENT_ALREADY_SET";

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    /// @param _evmScriptCallData Encoded tuple: (bytes32[] marketIds, address newFeeRecipient)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (bytes32[] memory marketIds, address newFeeRecipient) = _decodeEVMScriptCallData(
            _evmScriptCallData
        );
        require(marketIds.length != 0, ERROR_EMPTY_MARKETS_LIST);

        ILidoLendOwner owner = ILidoLendOwner(lidoLendOwner);
        ILidoLend core = owner.LIDO_LEND();
        require(core.feeRecipient() != newFeeRecipient, ERROR_FEE_RECIPIENT_ALREADY_SET);

        uint256 callsCount = marketIds.length + 1;
        address[] memory to = new address[](callsCount);
        bytes4[] memory methodIds = new bytes4[](callsCount);
        bytes[] memory callData = new bytes[](callsCount);

        for (uint256 i = 0; i < marketIds.length; ++i) {
            MarketParams memory marketParams = core.idToMarketParams(marketIds[i]);
            require(core.market(marketIds[i]).lastUpdate != 0, ERROR_MARKET_NOT_FOUND);
            to[i] = address(core);
            methodIds[i] = core.accrueInterest.selector;
            callData[i] = abi.encode(marketParams);
        }

        to[marketIds.length] = lidoLendOwner;
        methodIds[marketIds.length] = owner.setFeeRecipient.selector;
        callData[marketIds.length] = abi.encode(newFeeRecipient);

        return EVMScriptCreator.createEVMScript(to, methodIds, callData);
    }

    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        external
        pure
        returns (bytes32[] memory marketIds, address newFeeRecipient)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (bytes32[] memory marketIds, address newFeeRecipient)
    {
        return abi.decode(_evmScriptCallData, (bytes32[], address));
    }
}
