// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";
import "./LimitsChecker.sol";

/// @author psirex, zuzueeka
/// @title Registry of allowed addresses for payouts
/// @notice Stores list of allowed addresses
contract AllowedRecipientsRegistry is AccessControl, LimitsChecker {
    // -------------
    // EVENTS
    // -------------
    event AllowedRecipientAdded(address indexed _allowedRecipient, string _title);
    event AllowedRecipientRemoved(address indexed _allowedRecipient);

    // -------------
    // ROLES
    // -------------
    bytes32 public constant ADD_ALLOWED_RECIPIENT_ROLE = keccak256("ADD_ALLOWED_RECIPIENT_ROLE");
    bytes32 public constant REMOVE_ALLOWED_RECIPIENT_ROLE =
        keccak256("REMOVE_ALLOWED_RECIPIENT_ROLE");

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_ALLOWED_RECIPIENT_ALREADY_ADDED =
        "ALLOWED_RECIPIENT_ALREADY_ADDED";
    string private constant ERROR_ALLOWED_RECIPIENT_NOT_FOUND = "ALLOWED_RECIPIENT_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @dev List of allowed addresses for payouts
    address[] public allowedRecipients;

    // Position of the address in the `allowedRecipients` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private allowedRecipientIndices;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _admin Address which will be granted with role DEFAULT_ADMIN_ROLE
    /// @param _addAllowedRecipientRoleHolders List of addresses which will be
    ///     granted with role ADD_ALLOWED_RECIPIENT_ROLE
    /// @param _removeAllowedRecipientRoleHolders List of addresses which will
    ///     be granted with role REMOVE_ALLOWED_RECIPIENT_ROLE
    constructor(
        address _admin,
        address[] memory _addAllowedRecipientRoleHolders,
        address[] memory _removeAllowedRecipientRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateLimitSpendingsRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    )
        LimitsChecker(
            _setLimitParametersRoleHolders,
            _updateLimitSpendingsRoleHolders,
            _bokkyPooBahsDateTimeContract
        )
    {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        for (uint256 i = 0; i < _addAllowedRecipientRoleHolders.length; i++) {
            _setupRole(ADD_ALLOWED_RECIPIENT_ROLE, _addAllowedRecipientRoleHolders[i]);
        }
        for (uint256 i = 0; i < _removeAllowedRecipientRoleHolders.length; i++) {
            _setupRole(REMOVE_ALLOWED_RECIPIENT_ROLE, _removeAllowedRecipientRoleHolders[i]);
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Adds address to list of allowed addresses for payouts
    function addAllowedRecipient(address _allowedRecipient, string memory _title)
        external
        onlyRole(ADD_ALLOWED_RECIPIENT_ROLE)
    {
        require(
            allowedRecipientIndices[_allowedRecipient] == 0,
            ERROR_ALLOWED_RECIPIENT_ALREADY_ADDED
        );

        allowedRecipients.push(_allowedRecipient);
        allowedRecipientIndices[_allowedRecipient] = allowedRecipients.length;
        emit AllowedRecipientAdded(_allowedRecipient, _title);
    }

    /// @notice Removes address from list of allowed addresses for payouts
    /// @dev To delete an allowed address from the allowedRecipients array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeAllowedRecipient(address _allowedRecipient)
        external
        onlyRole(REMOVE_ALLOWED_RECIPIENT_ROLE)
    {
        uint256 index = _getAllowedRecipientIndex(_allowedRecipient);
        uint256 lastIndex = allowedRecipients.length - 1;

        if (index != lastIndex) {
            address lastAllowedRecipient = allowedRecipients[lastIndex];
            allowedRecipients[index] = lastAllowedRecipient;
            allowedRecipientIndices[lastAllowedRecipient] = index + 1;
        }

        allowedRecipients.pop();
        delete allowedRecipientIndices[_allowedRecipient];
        emit AllowedRecipientRemoved(_allowedRecipient);
    }

    /// @notice Returns if passed address are listed as allowed recipient in the registry
    function isAllowedRecipient(address _address) external view returns (bool) {
        return allowedRecipientIndices[_address] > 0;
    }

    /// @notice Returns current list of allowed recipients
    function getAllowedRecipients() external view returns (address[] memory) {
        return allowedRecipients;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getAllowedRecipientIndex(address _evmScriptFactory)
        private
        view
        returns (uint256 _index)
    {
        _index = allowedRecipientIndices[_evmScriptFactory];
        require(_index > 0, ERROR_ALLOWED_RECIPIENT_NOT_FOUND);
        _index -= 1;
    }
}
