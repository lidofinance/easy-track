from brownie import chain, network, AllowedRecipientsRegistry, TopUpAllowedRecipients, AddAllowedRecipient, RemoveAllowedRecipient

from utils.config import (
    get_is_live,
    get_deployer_account,
    prompt_bool,
    get_network_name,
)
from utils import (
    lido,
    deployed_easy_track,
    log
)

ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE = "0xec20c52871c824e5437859e75ac830e83aaaaeb7b0ffd850de830ddd3e385276"
REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE = "0x491d7752c25cfca0f73715cde1130022a9b815373f91a996bbb1ba8943efc99b"
SET_PARAMETERS_ROLE = "0x260b83d52a26066d8e9db550fa70395df5f3f064b50ff9d8a94267d9f1fe1967"
UPDATE_SPENT_AMOUNT_ROLE = "0xc5260260446719a726d11a6faece21d19daa48b4cbcca118345832d4cb71df99"
DEFAULT_ADMIN_ROLE = "0x00"

def main():
    network_name = get_network_name()

    if (not (network_name == "goerli" or network_name == "goerli-fork")):
        raise EnvironmentError("network is not supported")

    recipients = [
        "0xbbe8dDEf5BF31b71Ff5DbE89635f9dB4DeFC667E",
        "0x07fC01f46dC1348d7Ce43787b5Bbd52d8711a92D",
        "0xa5F1d7D49F581136Cf6e58B32cBE9a2039C48bA1",
        "0xDDFFac49946D1F6CE4d9CaF3B9C7d340d4848A1C",
        "0xc6e2459991BfE27cca6d86722F35da23A1E4Cb97"
    ]
    titles = [
        'Default Reward Program',
        'Happy',
        'Sergey\'2 #add RewardProgram',
        'Jumpgate Test',
        'tester',
    ]
    trusted_caller = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    tx = chain.get_transaction("0xd8bfe8b817231afb4851ac5926a84feb69b0a204f6ac37c3f3b91c6b8180981d")

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    easy_track = et_contracts.easy_track
    evm_script_executor = et_contracts.evm_script_executor


    regestryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]
    addRecipientAddress = tx.events["AddAllowedRecipientDeployed"]["addAllowedRecipient"]
    removeAllowedRecipientAddress = tx.events["RemoveAllowedRecipientDeployed"]["removeAllowedRecipient"]

    registry = AllowedRecipientsRegistry.at(regestryAddress)
    topUpAllowedRecipients = TopUpAllowedRecipients.at(topUpAddress)
    addAllowedRecipient = AddAllowedRecipient.at(addRecipientAddress)
    removeAllowedRecipient = RemoveAllowedRecipient.at(removeAllowedRecipientAddress) 

    assert topUpAllowedRecipients.token() == contracts.ldo
    assert topUpAllowedRecipients.allowedRecipientsRegistry() == registry
    assert topUpAllowedRecipients.trustedCaller() == trusted_caller
    assert addAllowedRecipient.allowedRecipientsRegistry() == registry
    assert addAllowedRecipient.trustedCaller() == trusted_caller
    assert removeAllowedRecipient.allowedRecipientsRegistry() == registry
    assert removeAllowedRecipient.trustedCaller() == trusted_caller

    assert len(registry.getAllowedRecipients()) == len(recipients)
    for recipient in recipients:
        assert registry.isRecipientAllowed(recipient)
    
    registryLimit, registryPeriodDuration = registry.getLimitParameters()
    assert registryLimit == limit
    assert registryPeriodDuration == period

    assert registry.spendableBalance() == limit - spent_amount
    
    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, contracts.aragon.agent)
    assert registry.hasRole(SET_PARAMETERS_ROLE, contracts.aragon.agent)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, contracts.aragon.agent)
    assert registry.hasRole(DEFAULT_ADMIN_ROLE, contracts.aragon.agent)

    assert registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, regestryAddress)
    assert not registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, regestryAddress)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, regestryAddress)
    assert not registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, regestryAddress)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, regestryAddress)

    
