// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "./IBaseModule.sol";
import "./IMetaRegistry.sol";

interface ICuratedModule is IBaseModule {
    function META_REGISTRY() external view returns (IMetaRegistry);
}
