from brownie import (
    chain, 
    AllowedRecipientsRegistry, 
    TopUpAllowedRecipients
)

from utils.config import (
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

    recipient = "0x3eaE0B337413407FB3C65324735D797ddc7E071D"
    token = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    limit = 10_000 * 1e18
    period = 1
    spent_amount = 0

    tx = chain.get_transaction("0xcf663eebff6ce76b03867a2f32c6456b5bbb4a11e6441798fb15409c7ca39fab")

    contracts = lido.contracts(network=network_name)
    et_contracts = deployed_easy_track.contracts(network=network_name)

    evm_script_executor = et_contracts.evm_script_executor

    registryAddress = tx.events["AllowedRecipientsRegistryDeployed"]["allowedRecipientsRegistry"]
    topUpAddress = tx.events["TopUpAllowedRecipientsDeployed"]["topUpAllowedRecipients"]

    log.br()

    log.nb("recipient", recipient)
    log.nb("token", token)
    log.nb("limit", limit)
    log.nb("period", period)
    log.nb("spent_amount", spent_amount)

    log.br()

    log.nb("AllowedRecipientsRegistryDeployed", registryAddress)
    log.nb("TopUpAllowedRecipientsDeployed", topUpAddress)

    log.br()

    registry = AllowedRecipientsRegistry.at(registryAddress)
    topUpAllowedRecipients = TopUpAllowedRecipients.at(topUpAddress)

    assert topUpAllowedRecipients.token() == token
    assert topUpAllowedRecipients.allowedRecipientsRegistry() == registry
    assert topUpAllowedRecipients.trustedCaller() == recipient

    assert len(registry.getAllowedRecipients()) == 1
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

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evm_script_executor)
    assert not registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evm_script_executor)
    assert registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evm_script_executor)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, evm_script_executor)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, evm_script_executor)

    assert not registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, registryAddress)
    assert not registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, registryAddress)
    assert not registry.hasRole(SET_PARAMETERS_ROLE, registryAddress)
    assert not registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, registryAddress)
    assert not registry.hasRole(DEFAULT_ADMIN_ROLE, registryAddress)

    print("Setup is valid")

