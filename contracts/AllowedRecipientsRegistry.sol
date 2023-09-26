// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./LimitsChecker.sol";

/// @author psirex, zuzueeka
/// @title Registry of allowed addresses for payouts
/// @notice Stores list of allowed addresses
contract AllowedRecipientsRegistry is LimitsChecker {
    // -------------
    // EVENTS
    // -------------
    event RecipientAdded(address indexed _recipient, string _title);
    event RecipientRemoved(address indexed _recipient);
    event TokenAdded(address indexed _token);
    event TokenRemoved(address indexed _token);

    // -------------
    // ROLES
    // -------------
    bytes32 public constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 public constant ADD_TOKEN_TO_ALLOWED_LIST_ROLE = keccak256("ADD_TOKEN_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE = keccak256("REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE");

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST = "RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST";
    string private constant ERROR_RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST = "RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST";
    string private constant ERROR_TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST = "TOKEN_ALREADY_ADDED_TO_ALLOWED_LIST";
    string private constant ERROR_TOKEN_NOT_FOUND_IN_ALLOWED_LIST = "TOKEN_NOT_FOUND_IN_ALLOWED_LIST";

    // -------------
    // VARIABLES
    // -------------

    /// @dev List of allowed addresses for payouts
    address[] public allowedRecipients;

    // Position of the address in the `allowedRecipients` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private allowedRecipientIndices;

    /// @dev List of allowed tokens for payouts
    address[] public allowedTokens;

    // Position of the address in the `allowedTokens` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private allowedTokenIndices;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _admin Address which will be granted with role DEFAULT_ADMIN_ROLE
    /// @param _addRecipientToAllowedListRoleHolders List of addresses which will be
    ///     granted with role ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE
    /// @param _removeRecipientFromAllowedListRoleHolders List of addresses which will
    ///     be granted with role REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE
    /// @param _setParametersRoleHolders List of addresses which will
    ///     be granted with role SET_PARAMETERS_ROLE
    /// @param _updateSpentAmountRoleHolders List of addresses which will
    ///     be granted with role UPDATE_SPENT_AMOUNT_ROLE
    /// @param _bokkyPooBahsDateTimeContract Address of bokkyPooBahs DateTime Contract
    constructor(
        address _admin,
        address[] memory _addRecipientToAllowedListRoleHolders,
        address[] memory _removeRecipientFromAllowedListRoleHolders,
        address[] memory _addTokenToAllowedListRoleHolders,
        address[] memory _removeTokenFromAllowedListRoleHolders,
        address[] memory _setParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) LimitsChecker(_setParametersRoleHolders, _updateSpentAmountRoleHolders, _bokkyPooBahsDateTimeContract) {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        for (uint256 i = 0; i < _addRecipientToAllowedListRoleHolders.length; i++) {
            _setupRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, _addRecipientToAllowedListRoleHolders[i]);
        }
        for (uint256 i = 0; i < _removeRecipientFromAllowedListRoleHolders.length; i++) {
            _setupRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, _removeRecipientFromAllowedListRoleHolders[i]);
        }
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

    /// @notice Adds address to list of allowed addresses for payouts
    function addRecipient(address _recipient, string memory _title)
        external
        onlyRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE)
    {
        require(allowedRecipientIndices[_recipient] == 0, ERROR_RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST);

        allowedRecipients.push(_recipient);
        allowedRecipientIndices[_recipient] = allowedRecipients.length;
        emit RecipientAdded(_recipient, _title);
    }

    /// @notice Removes address from list of allowed addresses for payouts
    /// @dev To delete an allowed address from the allowedRecipients array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeRecipient(address _recipient) external onlyRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE) {
        uint256 index = _getAllowedRecipientIndex(_recipient);
        uint256 lastIndex = allowedRecipients.length - 1;

        if (index != lastIndex) {
            address lastAllowedRecipient = allowedRecipients[lastIndex];
            allowedRecipients[index] = lastAllowedRecipient;
            allowedRecipientIndices[lastAllowedRecipient] = index + 1;
        }

        allowedRecipients.pop();
        delete allowedRecipientIndices[_recipient];
        emit RecipientRemoved(_recipient);
    }

    /// @notice Returns if passed address is listed as allowed recipient in the registry
    function isRecipientAllowed(address _recipient) external view returns (bool) {
        return allowedRecipientIndices[_recipient] > 0;
    }

    /// @notice Returns current list of allowed recipients
    function getAllowedRecipients() external view returns (address[] memory) {
        return allowedRecipients;
    }

    /// @notice Adds address to list of allowed tokens for payouts
    function addToken(address _token) external onlyRole(ADD_TOKEN_TO_ALLOWED_LIST_ROLE) {
        require(allowedTokenIndices[_token] == 0, ERROR_RECIPIENT_ALREADY_ADDED_TO_ALLOWED_LIST);

        allowedTokens.push(_token);
        allowedTokenIndices[_token] = allowedTokens.length;
        emit TokenAdded(_token);
    }

    /// @notice Removes address from list of allowed tokens for payouts
    /// @dev To delete an allowed token from the allowedTokens array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeToken(address _token) external onlyRole(REMOVE_TOKEN_FROM_ALLOWED_LIST_ROLE) {
        uint256 index = _getAllowedRecipientIndex(_token);
        uint256 lastIndex = allowedTokens.length - 1;

        if (index != lastIndex) {
            address lastAllowedToken = allowedTokens[lastIndex];
            allowedTokens[index] = lastAllowedToken;
            allowedTokenIndices[lastAllowedToken] = index + 1;
        }

        allowedRecipients.pop();
        delete allowedTokenIndices[_token];
        emit TokenRemoved(_token);
    }

    /// @notice Returns if passed address is listed as allowed token in the registry
    function isTokenAllowed(address _token) external view returns (bool) {
        return true;
        // return allowedTokenIndices[_token] > 0;
    }

    /// @notice Returns current list of allowed tokens
    function getAllowedTokens() external view returns (address[] memory) {
        return allowedTokens;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getAllowedRecipientIndex(address _recipient) private view returns (uint256 _index) {
        _index = allowedRecipientIndices[_recipient];
        require(_index > 0, ERROR_RECIPIENT_NOT_FOUND_IN_ALLOWED_LIST);
        _index -= 1;
    }

    function _getAllowedTokenIndex(address _token) private view returns (uint256 _index) {
        _index = allowedTokenIndices[_token];
        require(_index > 0, ERROR_TOKEN_NOT_FOUND_IN_ALLOWED_LIST);
        _index -= 1;
    }
}
