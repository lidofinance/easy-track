import re
import os
from brownie import AddRewardProgram, RemoveRewardProgram, TopUpRewardPrograms

IMPORT_PATTERN = re.compile(
    r"(?<=\n)?import(?P<prefix>.*)(?P<quote>[\"'])(?P<path>.*)(?P=quote)(?P<suffix>.*)(?=\n)"
)
PRAGMA_PATTERN = re.compile(r"^pragma.*;$", re.MULTILINE)
LICENSE_PATTERN = re.compile(r"^// SPDX-License-Identifier: (.*)$", re.MULTILINE)


def flatten_contract(container):
    contract_name = container.get_verification_info()["contract_name"]

    content = [
        x["content"]
        for x in container.get_verification_info()["standard_json_input"]["sources"].values()
    ]
    licenses = set([])

    content.reverse()

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
    flatten_contract(AddRewardProgram)
    flatten_contract(RemoveRewardProgram)
    flatten_contract(TopUpRewardPrograms)
