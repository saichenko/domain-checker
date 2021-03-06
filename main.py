#!/usr/bin/env python3

import csv
import itertools
import multiprocessing as mp
from os import listdir, remove
from time import sleep

import requests
from fake_headers import Headers
from requests.exceptions import RequestException, SSLError
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

TIMEOUT = 20


def divide_list(lst, n):
    amt = len(lst) // n
    for _ in range(n):
        yield lst[:amt]
        lst = lst[amt:]


def remove_temp_files():
    file_names = list(filter(lambda x: 'temp_file_' in x, listdir()))
    for file_name in file_names:
        remove(file_name)


def check_domain(domain):
    """ Checks the domain and returns a dict object containing information about it """
    redirect_domains = []
    header = Headers(os='win', browser='Chrome')

    try:
        url = 'https://' + domain
        response = requests.get(url, timeout=TIMEOUT, verify=False, headers=header.generate())
    except SSLError:
        try:
            url = 'http://' + domain
            response = requests.get(url, timeout=TIMEOUT, verify=False, headers=header.generate())
        except RequestException:
            try:
                url = 'http://www.' + domain
                response = requests.get(url, timeout=TIMEOUT, verify=False, headers=header.generate())
                print(url)
            except Exception:
                pass
            return dict(domain=domain, accessible=False, redirect_domains=redirect_domains, status_code=None)
    except RequestException:
        try:
            url = 'https://www.' + domain
            response = requests.get(url, timeout=TIMEOUT, verify=False, headers=header.generate())
            print(url)
        except Exception:
            pass
        return dict(domain=domain, accessible=False, redirect_domains=redirect_domains, status_code=None)

    if response.history:
        redirect_domains = list(filter(lambda x: x[:-1] != url, (map(lambda x: x.url, response.history))))

    if response.status_code == 430:
        sleep(2)  # Sleep for 2 seconds if too much requests error

    return dict(
        domain=domain,
        accessible=response.status_code,
        redirect_domains=redirect_domains,
        status_code=response.status_code
    )


def parse_and_create_temp_files(domains):
    """
        Temporary files are saved with names in 'temp_file_<ID>.csv' format.
        They will be deleted later automatically.
    """
    pid = mp.current_process().pid
    amount = len(domains)

    with open(f'temp_file_{pid}.csv', 'w') as file:
        writer = csv.writer(file, delimiter=';')

        for i, domain in enumerate(domains):
            data = check_domain(domain)

            writer.writerow([
                data['domain'],
                'yes' if data['accessible'] else 'no',
                ', '.join(data['redirect_domains']) if data['redirect_domains'] else '',
                data['status_code'] if data['status_code'] else ''
            ])
            print(f'{pid}: {i}/{amount} {int(i/amount * 100)}%', flush=True)


def collect_data():
    """ Combines data from `temp_file_` files to result.csv """
    file_names = list(filter(lambda x: 'temp_file_' in x, listdir()))

    with open('result.csv', 'w') as file:
        writer = csv.writer(file, delimiter=';')
        writer.writerow(['domain', 'domain_status', 'redirected_domains', 'status_code'])

        for file_name in file_names:
            with open(file_name, 'r') as temp_file:
                reader = csv.reader(temp_file, delimiter=';')
                for row in reader:
                    writer.writerow(row)
            remove(file_name)  # Removes temp file after appending its data to result.csv


def run():
    with open('domains.csv', 'r') as file:
        reader = csv.reader(file, delimiter=',')
        domains = list(itertools.chain(*list(reader)))[1:]

    cpus = mp.cpu_count() * 2 + 1
    with mp.Pool(processes=cpus) as p:
        p.map(parse_and_create_temp_files, list(divide_list(domains, cpus)))

    collect_data()


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        remove_temp_files()  # Remove all temp files if program was stopped
