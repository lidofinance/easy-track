// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

interface IAllowedRecipientsRegistry {
    function addRecipient(address _recipient, string memory _title) external;
    function renounceRole(bytes32 role, address account) external;
    function isRecipientAllowed(address _recipient) external view returns (bool);
    function setLimitParameters(uint256 _limit, uint256 _periodDurationMonths) external;
    function getLimitParameters() external view returns (uint256, uint256);
    function updateSpentAmount(uint256 _payoutAmount) external;
    function spendableBalance() external view returns (uint256);
    function hasRole(bytes32 role, address account) external view returns (bool);
    function getAllowedRecipients() external view returns (address[] memory);
}

interface ITopUpAllowedRecipients {
    function token() external view returns (address);
    function allowedRecipientsRegistry() external view returns (address);
}

interface IAddAllowedRecipient {
    function allowedRecipientsRegistry() external view returns (address);
}

interface IRemoveAllowedRecipient {
    function allowedRecipientsRegistry() external view returns (address);
}

interface IAllowedRecipientsFactory {
    function deployAllowedRecipientsRegistry(
        address[] memory addRecipientToAllowedListRoleHolders,
        address[] memory removeRecipientFromAllowedListRoleHolders,
        address[] memory setLimitParametersRoleHolders,
        address[] memory updateSpentAmountRoleHolders
    ) external returns(IAllowedRecipientsRegistry);

    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    ) external returns(ITopUpAllowedRecipients);

    function deployAddAllowedRecipient(
        address _trustedCaller, 
        address _allowedRecipientsRegistry
    ) external returns(IAddAllowedRecipient);

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) external returns(IRemoveAllowedRecipient);
}

contract AllowedRecipientsBuilder {

    bytes32 public constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant SET_LIMIT_PARAMETERS_ROLE = keccak256("SET_LIMIT_PARAMETERS_ROLE");
    bytes32 public constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");

    IAllowedRecipientsFactory public immutable factory;
    address public immutable evmScriptExecutor;
    address public immutable defaultAdmin;

    constructor(
        IAllowedRecipientsFactory _factory,
        address _evmScriptExecutor,
        address _defaultAdmin
    ){
        factory = _factory;
        evmScriptExecutor = _evmScriptExecutor;
        defaultAdmin = _defaultAdmin;
    }

    function deployAllowedRecipientsRegistry(
        uint256 _limit, 
        uint256 _periodDurationMonths,
        address[] memory _recipients, 
        string[] memory _titles,
        uint256 _spentAmount
    ) public returns(IAllowedRecipientsRegistry registry) 
    {
        require(_recipients.length == _titles.length);
        require(_spentAmount <= _limit);
        
        address[] memory addRecipientToAllowedListRoleHolders = new address[](3);
        addRecipientToAllowedListRoleHolders[0] = defaultAdmin;
        addRecipientToAllowedListRoleHolders[1] = evmScriptExecutor;
        addRecipientToAllowedListRoleHolders[2] = address(this);
        address[] memory removeRecipientFromAllowedListRoleHolders = new address[](2);
        removeRecipientFromAllowedListRoleHolders[0] = defaultAdmin;
        removeRecipientFromAllowedListRoleHolders[1] = evmScriptExecutor;
        address[] memory setLimitParametersRoleHolders = new address[](2);
        setLimitParametersRoleHolders[0] = defaultAdmin;
        setLimitParametersRoleHolders[1] = address(this);
        address[] memory updateSpentAmountRoleHolders = new address[](3);
        updateSpentAmountRoleHolders[0] = defaultAdmin;
        updateSpentAmountRoleHolders[1] = evmScriptExecutor;
        updateSpentAmountRoleHolders[2] = address(this);

        registry = factory.deployAllowedRecipientsRegistry( 
            addRecipientToAllowedListRoleHolders,
            removeRecipientFromAllowedListRoleHolders,
            setLimitParametersRoleHolders,
            updateSpentAmountRoleHolders
        );
        
        for (uint256 i = 0; i < _recipients.length; i++) {
            registry.addRecipient(_recipients[i], _titles[i]);
        }
        registry.renounceRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this));

        require(registry.getAllowedRecipients().length == _recipients.length);
        for (uint256 i = 0; i < _recipients.length; i++) {
            require(registry.isRecipientAllowed(_recipients[i]));
        }       

        registry.setLimitParameters(_limit, _periodDurationMonths);
        registry.renounceRole(SET_LIMIT_PARAMETERS_ROLE, address(this));

        (uint256 registryLimit,  uint256 registryPeriodDuration) = registry.getLimitParameters();
        require(registryLimit == _limit);
        require(registryPeriodDuration == _periodDurationMonths);

        registry.updateSpentAmount(_spentAmount);
        registry.renounceRole(UPDATE_SPENT_AMOUNT_ROLE, address(this));

        require(registry.spendableBalance() == _limit - _spentAmount);

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, defaultAdmin));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, defaultAdmin));
        require(registry.hasRole(DEFAULT_ADMIN_ROLE, defaultAdmin));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evmScriptExecutor));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evmScriptExecutor));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evmScriptExecutor));
        require(!registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, evmScriptExecutor));
        require(!registry.hasRole(DEFAULT_ADMIN_ROLE, evmScriptExecutor));

        require(!registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, address(this)));
        require(!registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, address(this)));
        require(!registry.hasRole(DEFAULT_ADMIN_ROLE, address(this)));
    }

    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    )   public returns(ITopUpAllowedRecipients topUpAllowedRecipients) 
    {      
        topUpAllowedRecipients = factory.deployTopUpAllowedRecipients(
            _trustedCaller, 
            _allowedRecipientsRegistry, 
            _token
        );

        require(topUpAllowedRecipients.token() == _token);
        require(
            address(topUpAllowedRecipients.allowedRecipientsRegistry()) == 
            _allowedRecipientsRegistry
        );
    }


    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(IAddAllowedRecipient addAllowedRecipient) 
    {
        addAllowedRecipient = factory.deployAddAllowedRecipient(
            _trustedCaller, 
            _allowedRecipientsRegistry
        );

        require(
            address(addAllowedRecipient.allowedRecipientsRegistry()) == 
            _allowedRecipientsRegistry
        );
    }

    
    function deployRemoveAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(IRemoveAllowedRecipient removeAllowedRecipient) 
    {
        removeAllowedRecipient = factory.deployRemoveAllowedRecipient(
            _trustedCaller, 
            _allowedRecipientsRegistry
        );

        require(address(removeAllowedRecipient.allowedRecipientsRegistry()) == _allowedRecipientsRegistry);
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
        IAllowedRecipientsRegistry allowedRecipientsRegistry,
        ITopUpAllowedRecipients topUpAllowedRecipients,
        IAddAllowedRecipient addAllowedRecipient,
        IRemoveAllowedRecipient removeAllowedRecipient
    ) {
        allowedRecipientsRegistry = deployAllowedRecipientsRegistry(
            _limit, 
            _periodDurationMonths,
            _recipients,
            _titles,
            _spentAmount
        );

        topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _trustedCaller, 
            address(allowedRecipientsRegistry),
            _token
        );

        addAllowedRecipient = deployAddAllowedRecipient(
            _trustedCaller, 
            address(allowedRecipientsRegistry)
        );

        removeAllowedRecipient = deployRemoveAllowedRecipient(
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
        IAllowedRecipientsRegistry allowedRecipientsRegistry,
        ITopUpAllowedRecipients topUpAllowedRecipients
    ) {
        address[] memory recipients = new address[](1);
        recipients[0] = _recipient;

        string[] memory titles = new string[](1);
        titles[0] = _title;

        allowedRecipientsRegistry = deployAllowedRecipientsRegistry(
            _limit, 
            _periodDurationMonths,
            recipients,
            titles,
            _spentAmount
        );

        topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _recipient, 
            address(allowedRecipientsRegistry),
            _token
        );
    }
}
