// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

/// @author psirex, dzhon
/// @title Registry of allowed referral partners
/// @notice Stores list of addresses with referral partners
contract ReferralPartnersRegistry is AccessControl {
    // -------------
    // EVENTS
    // -------------
    event ReferralPartnerAdded(address indexed _referralPartner, string _title);
    event ReferralPartnerRemoved(address indexed _referralPartner);

    // -------------
    // ROLES
    // -------------
    bytes32 public constant ADD_REFERRAL_PARTNER_ROLE = keccak256("ADD_REFERRAL_PARTNER_ROLE");
    bytes32 public constant REMOVE_REFERRAL_PARTNER_ROLE = keccak256("REMOVE_REFERRAL_PARTNER_ROLE");

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_REFERRAL_PARTNER_ALREADY_ADDED = "REFERRAL_PARTNER_ALREADY_ADDED";
    string private constant ERROR_REFERRAL_PARTNER_NOT_FOUND = "REFERRAL_PARTNER_NOT_FOUND";

    // -------------
    // VARIABLES
    // -------------

    /// @dev List of allowed referral partners addresses
    address[] public referralPartners;

    // Position of the referral partners in the `referralPartners` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private referralPartnersIndices;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _admin Address which will be granted with role DEFAULT_ADMIN_ROLE
    /// @param _addReferralPartnerRoleHolders List of addresses which will be
    ///     granted with role ADD_REFERRAL_PARTNER_ROLE
    /// @param _removeReferralPartnerRoleHolders List of addresses which will
    ///     be granted with role REMOVE_REFERRAL_PARTNER_ROLE
    constructor(
        address _admin,
        address[] memory _addReferralPartnerRoleHolders,
        address[] memory _removeReferralPartnerRoleHolders
    ) {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);
        for (uint256 i = 0; i < _addReferralPartnerRoleHolders.length; i++) {
            _setupRole(ADD_REFERRAL_PARTNER_ROLE, _addReferralPartnerRoleHolders[i]);
        }
        for (uint256 i = 0; i < _removeReferralPartnerRoleHolders.length; i++) {
            _setupRole(REMOVE_REFERRAL_PARTNER_ROLE, _removeReferralPartnerRoleHolders[i]);
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Adds address to list of allowed referral partners
    function addReferralPartner(address _referralPartner, string memory _title)
        external
        onlyRole(ADD_REFERRAL_PARTNER_ROLE)
    {
        require(referralPartnersIndices[_referralPartner] == 0, ERROR_REFERRAL_PARTNER_ALREADY_ADDED);

        referralPartners.push(_referralPartner);
        referralPartnersIndices[_referralPartner] = referralPartners.length;
        emit ReferralPartnerAdded(_referralPartner, _title);
    }

    /// @notice Removes address from list of allowed referral partners
    /// @dev To delete a referral partner from the referralPartners array in O(1), we swap the element to delete with the last one in
    /// the array, and then remove the last element (sometimes called as 'swap and pop').
    function removeReferralPartner(address _referralPartner)
        external
        onlyRole(REMOVE_REFERRAL_PARTNER_ROLE)
    {
        uint256 index = _getReferralPartnerIndex(_referralPartner);
        uint256 lastIndex = referralPartners.length - 1;

        if (index != lastIndex) {
            address lastReferralPartner = referralPartners[lastIndex];
            referralPartners[index] = lastReferralPartner;
            referralPartnersIndices[lastReferralPartner] = index + 1;
        }

        referralPartners.pop();
        delete referralPartnersIndices[_referralPartner];
        emit ReferralPartnerRemoved(_referralPartner);
    }

    /// @notice Returns if passed address are listed as referral partner in the registry
    function isReferralPartner(address _maybeReferralPartner) external view returns (bool) {
        return referralPartnersIndices[_maybeReferralPartner] > 0;
    }

    /// @notice Returns current list of referral partners
    function getReferralPartners() external view returns (address[] memory) {
        return referralPartners;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getReferralPartnerIndex(address _evmScriptFactory)
        private
        view
        returns (uint256 _index)
    {
        _index = referralPartnersIndices[_evmScriptFactory];
        require(_index > 0, ERROR_REFERRAL_PARTNER_NOT_FOUND);
        _index -= 1;
    }
}
