// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;


interface IAllowedRecipientsFactory {
    function deployAllowedRecipientsRegistry(
        uint256 _limit, 
        uint256 _periodDurationMonths,
        address[] memory _recipients, 
        string[] memory _titles,
        uint256 _spentAmount
    ) external returns(address);

    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    ) external returns(address);

    function deployAddAllowedRecipient(
        address _trustedCaller, 
        address _allowedRecipientsRegistry
    ) external returns(address);

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) external returns(address);
}

contract AllowedRecipientsBuilder {

    IAllowedRecipientsFactory public immutable factory;

    constructor(
        IAllowedRecipientsFactory _factory
    ){
        factory = _factory;
    }

    function deployFullSetup(
        address _trustedCaller,
        address _token, 
        uint256 _limit, 
        uint256 _periodDurationMonths,
        address[] memory _recipients, 
        string[] memory _titles,
        uint256 _spentAmount
    ) public returns (
        address allowedRecipientsRegistry,
        address topUpAllowedRecipients,
        address addAllowedRecipient,
        address removeAllowedRecipient
    ) {
        allowedRecipientsRegistry = factory.deployAllowedRecipientsRegistry(
            _limit, 
            _periodDurationMonths,
            _recipients,
            _titles,
            _spentAmount
        );

        topUpAllowedRecipients = factory.deployTopUpAllowedRecipients(
            _trustedCaller, 
            address(allowedRecipientsRegistry),
            _token
        );

        addAllowedRecipient = factory.deployAddAllowedRecipient(
            _trustedCaller, 
            address(allowedRecipientsRegistry)
        );

        removeAllowedRecipient = factory.deployRemoveAllowedRecipient(
            _trustedCaller, 
            address(allowedRecipientsRegistry)
        );
    }

    function deploySingleRecipientTopUpOnlySetup(
        address _recipient, 
        string memory _title,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns (
        address allowedRecipientsRegistry,
        address topUpAllowedRecipients
    ) {
        address[] memory recipients = new address[](1);
        recipients[0] = _recipient;

        string[] memory titles = new string[](1);
        titles[0] = _title;

        allowedRecipientsRegistry = factory.deployAllowedRecipientsRegistry(
            _limit, 
            _periodDurationMonths,
            recipients,
            titles,
            _spentAmount
        );

        topUpAllowedRecipients = factory.deployTopUpAllowedRecipients(
            _recipient, 
            address(allowedRecipientsRegistry),
            _token
        );
    }
}
