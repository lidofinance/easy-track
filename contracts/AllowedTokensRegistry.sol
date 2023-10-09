// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";
import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/token/ERC20/extensions/IERC20Metadata.sol";

contract AllowedTokensRegistry is AccessControl {
    // -------------
    // EVENTS
    // -------------
    event TokenAdded(address indexed _token);
    event TokenRemoved(address indexed _token);

    // -------------
    // ROLES
    // -------------

    bytes32 public constant ADD_TOKEN_TO_ALLOWED_LIST_ROLE = keccak256("ADD_TOKEN_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = keccak256("REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE");

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST = "TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST";
    string private constant ERROR_TOKEN_NOT_FOUND_IN_ALLOWED_LIST = "TOKEN_NOT_FOUND_IN_ALLOWED_LIST";
    string private constant ERROR_TOKEN_ADDRESS_IS_ZERO = "TOKEN_ADDRESS_IS_ZERO";

    // -------------
    // VARIABLES
    // -------------
    /// @dev List of allowed tokens for payouts
    address[] public allowedTokens;
 
    // Position of the address in the `allowedTokens` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private allowedTokenIndices;

    /// @notice Precise number of tokens in the system
    uint8 internal constant DECIMALS = 18;

    constructor(
        address _admin,
        address[] memory _addTokenToAllowedListRoleHolders,
        address[] memory _removeTokenFromAllowedListRoleHolders
    ) {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        for (uint256 i = 0; i < _addTokenToAllowedListRoleHolders.length; i++) {
            _setupRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE, _addTokenToAllowedListRoleHolders[i]);
        }
        for (uint256 i = 0; i < _removeTokenFromAllowedListRoleHolders.length; i++) {
            _setupRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE, _removeTokenFromAllowedListRoleHolders[i]);
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Adds address to list of allowed tokens for payouts
    function addToken(address _token) external onlyRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE) {
        require(_token != address(0), ERROR_TOKEN_ADDRESS_IS_ZERO);
        require(allowedTokenIndices[_token] == 0, ERROR_TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST);

        allowedTokens.push(_token);
        allowedTokenIndices[_token] = allowedTokens.length;
        emit TokenAdded(_token);
    }

    /// @notice Removes address from list of allowed tokens for payouts
    /// @dev To delete an allowed token from the allowedTokens array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeToken(address _token) external onlyRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE) {
        uint256 index = _getAllowedTokenIndex(_token);
        uint256 lastIndex = allowedTokens.length - 1;

        if (index != lastIndex) {
            address lastAllowedToken = allowedTokens[lastIndex];
            allowedTokens[index] = lastAllowedToken;
            allowedTokenIndices[lastAllowedToken] = index + 1;
        }

        allowedTokens.pop();
        delete allowedTokenIndices[_token];
        emit TokenRemoved(_token);
    }

    /// @notice Returns if passed address is listed as allowed token in the registry
    function isTokenAllowed(address _token) external view returns (bool) {
        return allowedTokenIndices[_token] > 0;
    }

    /// @notice Returns current list of allowed tokens
    function getAllowedTokens() external view returns (address[] memory) {
        return allowedTokens;
    }

    /// @notice Transforms amout from token format to precise format
    function normalizeAmount(uint256 _tokenAmount, address _token) external view returns (uint256) {
        require(_token != address(0), ERROR_TOKEN_ADDRESS_IS_ZERO);

        uint8 tokenDecimals = IERC20Metadata(_token).decimals();

        if (tokenDecimals == DECIMALS) return _tokenAmount;
        if (tokenDecimals > DECIMALS) {
            // It's rounded up to fit into limits
            // https://github.com/OpenZeppelin/openzeppelin-contracts/blob/3e6c86392c97fbc30d3d20a378a6f58beba08eba/contracts/utils/math/Math.sol#L107
            return (_tokenAmount - 1) / 10 ** (tokenDecimals - DECIMALS) + 1;
        }
        return _tokenAmount * 10 ** (DECIMALS - tokenDecimals);
    }

    /// @notice Returns precision of the token
    function decimals() pure external returns (uint8) {
        return DECIMALS;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getAllowedTokenIndex(address _token) private view returns (uint256 _index) {
        _index = allowedTokenIndices[_token];
        require(_index > 0, ERROR_TOKEN_NOT_FOUND_IN_ALLOWED_LIST);
        _index -= 1;
    }
}
