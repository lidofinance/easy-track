// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../interfaces/ILidoLend.sol";

/// @notice Test-only stub of the Lido Lend Trailing Anchor Oracle adapter. It forwards the calls to the oracle and
///         does not check the caller.
contract TrailingAnchorOracleAdapterStub is ILidoLendTrailingAnchorOracleAdapter {
    function setParameters(address _oracle, ITrailingAnchorOracle.Parameters calldata _parameters)
        external
        override
    {
        ITrailingAnchorOracle(_oracle).setParameters(_parameters);
    }

    function setPricingResumesAt(address _oracle, uint40 _resumesAt) external override {
        ITrailingAnchorOracle(_oracle).setPricingResumesAt(_resumesAt);
    }
}
