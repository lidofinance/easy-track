import os
import re
import time
from typing import Dict
from urllib.parse import urlparse

import requests
from brownie._config import CONFIG, REQUEST_HEADERS
from brownie.network.contract import ContractContainer
from brownie.network.web3 import _resolve_address
from brownie.utils import color

from scripts.contract_flattener import flatten_contract

IMPORT_PATTERN = re.compile(
    r"(?<=\n)?import(?P<prefix>.*)(?P<quote>[\"'])(?P<path>.*)(?P=quote)(?P<suffix>.*)(?=\n)"
)
PRAGMA_PATTERN = re.compile(r"^pragma.*;$", re.MULTILINE)
LICENSE_PATTERN = re.compile(r"^// SPDX-License-Identifier: (.*)$", re.MULTILINE)


_explorer_tokens = {
    "etherscan": "ETHERSCAN_TOKEN",
    "bscscan": "BSCSCAN_TOKEN",
    "polygonscan": "POLYGONSCAN_TOKEN",
    "ftmscan": "FTMSCAN_TOKEN",
    "arbiscan": "ARBISCAN_TOKEN",
    "snowtrace": "SNOWTRACE_TOKEN",
    "aurorascan": "AURORASCAN_TOKEN",
    "moonscan": "MOONSCAN_TOKEN",
}


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

    return result


def write_file(filename, content): 
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(content)


def flatten_contract_to_file(container):
    contract_name = container.get_verification_info()["contract_name"]
    content = flatten_contract(container)
    filename = "./contracts_flattened/" + contract_name + ".sol"
    write_file(filename, content)


def publish_source(contract: ContractContainer, container, constructor_params) -> bool:
        url = CONFIG.active_network.get("explorer")
        if url is None:
            raise ValueError("Explorer API not set for this network")
        env_token = next((v for k, v in _explorer_tokens.items() if k in url), None)
        if env_token is None:
            raise ValueError(
                f"Publishing source is only supported on {', '.join(_explorer_tokens)},"
                "change the Explorer API"
            )

        if os.getenv(env_token):
            api_key = os.getenv(env_token)
        else:
            host = urlparse(url).netloc
            host = host[host.index(".") + 1 :]
            raise ValueError(
                f"An API token is required to verify contract source code. Visit https://{host}/ "
                f"to obtain a token, and then store it as the environment variable ${env_token}"
            )

        address = _resolve_address(contract.address)

        # Submit verification
        payload_verification: Dict = {
            "apikey": api_key,
            "module": "contract",
            "action": "verifysourcecode",
            "contractaddress": address,
            "sourceCode": flatten_contract(container),
            "codeformat": "solidity-single-file",
            "contractname": "Contract",
            "compilerversion": "v0.8.6",
            "optimizationUsed": 1,
            "runs": 200,
            "constructorArguements": constructor_params,
            "licenseType": 5,
        }
        print(payload_verification)
        response = requests.post(url, data=payload_verification, headers=REQUEST_HEADERS)
        if response.status_code != 200:
            raise ConnectionError(
                f"Status {response.status_code} when querying {url}: {response.text}"
            )
        data = response.json()
        if int(data["status"]) != 1:
            raise ValueError(f"Failed to submit verification request: {data['result']}")

        # Status of request
        guid = data["result"]
        print("Verification submitted successfully. Waiting for result...")
        time.sleep(10)
        params_status: Dict = {
            "apikey": api_key,
            "module": "contract",
            "action": "checkverifystatus",
            "guid": guid,
        }
        while True:
            response = requests.get(url, params=params_status, headers=REQUEST_HEADERS)
            if response.status_code != 200:
                raise ConnectionError(
                    f"Status {response.status_code} when querying {url}: {response.text}"
                )
            data = response.json()
            if data["result"] == "Pending in queue":
                print("Verification pending...")
            else:
                col = "bright green" if data["message"] == "OK" else "bright red"
                print(f"Verification complete. Result: {color(col)}{data['result']}{color}")
                return data["message"] == "OK"
            time.sleep(10)
