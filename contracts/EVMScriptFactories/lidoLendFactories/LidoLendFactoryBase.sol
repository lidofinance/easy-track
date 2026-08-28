// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Shared Lido Lend core wiring and market resolution for EVMScript factories
abstract contract LidoLendFactoryBase is TrustedCaller {
    string internal constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    /// @notice Address of the Lido Lend core
    address public immutable lidoLend;

    constructor(address _trustedCaller, address _lidoLend) TrustedCaller(_trustedCaller) {
        lidoLend = _lidoLend;
    }

    function _marketController(bytes32 _marketId)
        internal
        view
        returns (ILidoLendMarketController)
    {
        return ILidoLendMarketController(ILidoLend(lidoLend).marketController(_marketId));
    }

    function _controllerOf(bytes32 _marketId)
        internal
        view
        returns (ILidoLendMarketController controller)
    {
        controller = _marketController(_marketId);
        require(address(controller) != address(0), ERROR_MARKET_NOT_FOUND);
    }
}
