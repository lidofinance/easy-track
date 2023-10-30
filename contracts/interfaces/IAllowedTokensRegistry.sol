// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

interface IAllowedTokensRegistry {
    function addToken(address _token) external;
    
    function removeToken(address _token) external;

    function renounceRole(bytes32 role, address account) external;

    function isTokenAllowed(address _token) external view returns (bool);

    function hasRole(bytes32 role, address account) external view returns (bool);

    function getAllowedTokens() external view returns (address[] memory);

    function decimals() external view returns (uint8);

    function normalizeAmount(uint256 _amount, address _token) external view returns (uint256);
}