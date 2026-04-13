// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "./IMetaRegistry.sol";

interface ICuratedModule {
    function META_REGISTRY() external view returns (IMetaRegistry);

    function getNodeOperatorIsActive(
        uint256 nodeOperatorId
    ) external view returns (bool);
}
