// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../interfaces/ILidoLend.sol";

/// @notice Shared LidoLendOwner wiring and market resolution for Lido Lend EVMScript factories
abstract contract LidoLendOwnerFactoryBase is TrustedCaller {
    string internal constant ERROR_MARKET_NOT_FOUND = "MARKET_NOT_FOUND";

    /// @notice Address of the LidoLendOwner facade
    address public immutable lidoLendOwner;

    constructor(address _trustedCaller, address _lidoLendOwner) TrustedCaller(_trustedCaller) {
        lidoLendOwner = _lidoLendOwner;
    }

    function _controllerOf(bytes32 _marketId)
        internal
        view
        returns (ILidoLendMarketController controller)
    {
        ILidoLend core = ILidoLendOwner(lidoLendOwner).LIDO_LEND();
        controller = ILidoLendMarketController(core.marketController(_marketId));
        require(address(controller) != address(0), ERROR_MARKET_NOT_FOUND);
    }

    function _guardianSignalsOf(bytes32 _marketId) internal view returns (IGuardianSignals) {
        return IGuardianSignals(_controllerOf(_marketId).guardianSignals());
    }
}
