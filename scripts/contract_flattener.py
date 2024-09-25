import re
import os
from brownie import (
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
)

IMPORT_PATTERN = re.compile(
    r"(?<=\n)?import(?P<prefix>.*)(?P<quote>[\"'])(?P<path>.*)(?P=quote)(?P<suffix>.*)(?=\n)"
)
PRAGMA_PATTERN = re.compile(r"^pragma.*;$", re.MULTILINE)
LICENSE_PATTERN = re.compile(r"^// SPDX-License-Identifier: (.*)$", re.MULTILINE)


def find_dependencies(contract, available_contract_list, sources):
    result = []
    current_deps = [x[2] for x in IMPORT_PATTERN.findall(sources[contract]["content"])]

    for contract_dep in current_deps:
        inner_results = find_dependencies(contract_dep, available_contract_list, sources)

        for inner_result in inner_results:
            result.append(inner_result)

        result.append(contract_dep)

    result.append(contract)

    return result


def flatten_contract(container):
    contract_name = container.get_verification_info()["contract_name"]
    sources = container.get_verification_info()["standard_json_input"]["sources"]
    content = []

    contracts_to_be_included = list(sources.keys())

    dependencies = find_dependencies(contract_name + ".sol", contracts_to_be_included, sources)

    for dependency in dependencies:
        if dependency in contracts_to_be_included:
            content.append(sources[dependency]["content"])
            contracts_to_be_included.remove(dependency)

    licenses = set([])
    for i in range(len(content)):
        license_search = LICENSE_PATTERN.search(content[i])
        licenses.add(license_search.group(1))

    licenses_list = list(licenses)

    for i in range(len(content)):
        content[i] = IMPORT_PATTERN.sub("", LICENSE_PATTERN.sub("", content[i]))
        if i == 0:
            continue

        content[i] = PRAGMA_PATTERN.sub("", content[i])

    content.insert(0, "// SPDX-License-Identifier: " + " & ".join(licenses_list) + "\n")
    result = "".join(content)

    filename = "./contracts_flattened/" + contract_name + ".sol"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(result)


def main():
    flatten_contract(AllowedRecipientsRegistry)
    flatten_contract(TopUpAllowedRecipients)
    flatten_contract(AddAllowedRecipient)
    flatten_contract(RemoveAllowedRecipient)
