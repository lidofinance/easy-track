// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../interfaces/ILidoLend.sol";
import "./LidoLendFactoryBase.sol";

/// @notice Shared LidoLendOwner wiring and market resolution for Lido Lend EVMScript factories
abstract contract LidoLendOwnerFactoryBase is LidoLendFactoryBase {
    /// @notice Address of the LidoLendOwner facade
    address public immutable lidoLendOwner;

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendFactoryBase(_trustedCaller, address(ILidoLendOwner(_lidoLendOwner).LIDO_LEND()))
    {
        lidoLendOwner = _lidoLendOwner;
    }
}
