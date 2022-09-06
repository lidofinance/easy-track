// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";
import "./LimitsChecker.sol";

/// @author psirex, zuzueeka
/// @title Registry of allowed addresses for payouts
/// @notice Stores list of whitelisted addresses
contract WhitelistedRecipientsRegistry is AccessControl, LimitsChecker {
    // -------------
    // EVENTS
    // -------------
    event WhitelistedRecipientAdded(address indexed _whitelistedRecipient, string _title);
    event WhitelistedRecipientRemoved(address indexed _whitelistedRecipient);

    // -------------
    // ROLES
    // -------------
    bytes32 public constant ADD_WHITELISTED_RECIPIENT_ROLE =
        keccak256("ADD_WHITELISTED_RECIPIENT_ROLE");
    bytes32 public constant REMOVE_WHITELISTED_RECIPIENT_ROLE =
        keccak256("REMOVE_WHITELISTED_RECIPIENT_ROLE");

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_WHITELISTED_RECIPIENT_ALREADY_ADDED =
        "WHITELISTED_RECIPIENT_ALREADY_ADDED";
    string private constant ERROR_WHITELISTED_RECIPIENT_NOT_FOUND =
        "WHITELISTED_RECIPIENT_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @dev List of allowed addresses for payouts
    address[] public whitelistedRecipients;

    // Position of the addredd in the `whitelistedRecipients` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private whitelistedRecipientIndices;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _admin Address which will be granted with role DEFAULT_ADMIN_ROLE
    /// @param _addWhitelistedRecipientRoleHolders List of addresses which will be
    ///     granted with role ADD_WHITELISTED_RECIPIENT_ROLE
    /// @param _removeWhitelistedRecipientRoleHolders List of addresses which will
    ///     be granted with role REMOVE_WHITELISTED_RECIPIENT_ROLE
    constructor(
        address _admin,
        address[] memory _addWhitelistedRecipientRoleHolders,
        address[] memory _removeWhitelistedRecipientRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        EasyTrack _easy_track
    ) LimitsChecker(_easy_track, _setLimitParametersRoleHolders) {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        for (uint256 i = 0; i < _addWhitelistedRecipientRoleHolders.length; i++) {
            _setupRole(ADD_WHITELISTED_RECIPIENT_ROLE, _addWhitelistedRecipientRoleHolders[i]);
        }
        for (uint256 i = 0; i < _removeWhitelistedRecipientRoleHolders.length; i++) {
            _setupRole(
                REMOVE_WHITELISTED_RECIPIENT_ROLE,
                _removeWhitelistedRecipientRoleHolders[i]
            );
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Adds address to list of allowed addresses for payouts
    function addWhitelistedRecipient(address _whitelistedRecipient, string memory _title)
        external
        onlyRole(ADD_WHITELISTED_RECIPIENT_ROLE)
    {
        require(
            whitelistedRecipientIndices[_whitelistedRecipient] == 0,
            ERROR_WHITELISTED_RECIPIENT_ALREADY_ADDED
        );

        whitelistedRecipients.push(_whitelistedRecipient);
        whitelistedRecipientIndices[_whitelistedRecipient] = whitelistedRecipients.length;
        emit WhitelistedRecipientAdded(_whitelistedRecipient, _title);
    }

    /// @notice Removes address from list of allowed addresses for payouts
    /// @dev To delete an allowed address from the whitelistedRecipients array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeWhitelistedRecipient(address _whitelistedRecipient)
        external
        onlyRole(REMOVE_WHITELISTED_RECIPIENT_ROLE)
    {
        uint256 index = _getWhitelistedRecipientIndex(_whitelistedRecipient);
        uint256 lastIndex = whitelistedRecipients.length - 1;

        if (index != lastIndex) {
            address lastWhitelistedRecipient = whitelistedRecipients[lastIndex];
            whitelistedRecipients[index] = lastWhitelistedRecipient;
            whitelistedRecipientIndices[lastWhitelistedRecipient] = index + 1;
        }

        whitelistedRecipients.pop();
        delete whitelistedRecipientIndices[_whitelistedRecipient];
        emit WhitelistedRecipientRemoved(_whitelistedRecipient);
    }

    /// @notice Returns if passed address are listed as whitelisted recipient in the registry
    function isWhitelistedRecipient(address _address) external view returns (bool) {
        return whitelistedRecipientIndices[_address] > 0;
    }

    /// @notice Returns current list of whitelisted recipients
    function getWhitelistedRecipients() external view returns (address[] memory) {
        return whitelistedRecipients;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getWhitelistedRecipientIndex(address _evmScriptFactory)
        private
        view
        returns (uint256 _index)
    {
        _index = whitelistedRecipientIndices[_evmScriptFactory];
        require(_index > 0, ERROR_WHITELISTED_RECIPIENT_NOT_FOUND);
        _index -= 1;
    }
}
