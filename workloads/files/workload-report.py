#!/usr/bin/env python3

import subprocess
import sys
import os
import json
from time import time
from datetime import datetime, timedelta
import urllib3
import argparse
import csv

# supress InsecureRequestWarning message
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import dependency
try:
    import requests
    from requests.auth import HTTPBasicAuth
except Exception as e:
    exit()

# parseMetrics
def parseMetrics(metrics_dictionary, result_type):
    metrics = []
    for row in (metrics_dictionary['data']['result']):
        if result_type == 'vector':
            metrics.append(str(row['value'][0]) + ',' + str(row['value'][1]))
        elif result_type == 'matrix':
            for value in row['values']:
                metrics.append(str(value[0]) + ',' + str(value[1]))
    return metrics

# create endpoint query
def createEndpoint(query_params_dict):
    query_params    = {}
    auth_credentials = {}
    # Range vector query
    if query_params_dict.get('end') is not None:
        query_params['query'] = query_params_dict.get('promql')
        query_params['start'] = query_params_dict.get('start')
        query_params['end']   = query_params_dict.get('end')
        if query_params_dict.get('step') is not None:
            query_params['step']  = query_params_dict.get('step')
        endpoint = query_params_dict['url'] + '/api/v1/query_range'
    # Instant vector query
    else:
        query_params['query'] = query_params_dict.get('promql')
        query_params['time']  = query_params_dict.get('start')
        endpoint = query_params_dict['url'] + '/api/v1/query'

    # Basic auth params
    if query_params_dict.get('user') is not None and query_params_dict.get('pass') is not None:
        auth_credentials['user'] = query_params_dict.get('user')
        auth_credentials['pass'] = query_params_dict.get('pass')

    # Request timeout param 
    if query_params_dict.get('timeout') is not None:
            query_params['timeout'] = query_params_dict.get('timeout')
    # return url , api query params and basic auth credentials

    return endpoint, query_params, auth_credentials

# Send promql request
def getMetrics(url, params, user, password):
    try:
        if user is not None and password is not None:
            res = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False, params=params)
        else:
            res = requests.get(url, verify=False, params=params)
        if res.status_code == 200:
            data = json.loads(res.text)
            if data['status'] != 'success': # check success or failure
                exit()
            if len(data['data']['result']) < 0: # check if resultset is empty
                exit()
            metrics = parseMetrics(data, data['data']['resultType'])
            return metrics   
        else:
           print("Something went wrong: {}".format(res.status_code))
    except requests.exceptions.RequestException as re:
        print(re)
    #except requests.exceptions.ConnectionError as ce:
    #    print(ce)
    #except requests.exceptions.ConnectTimeout as ct:
    #    print(ct)

# File path to store csv output
def writeToCsvFile(cmd_args, metrics):
    file_path = cmd_args.get('file_path')
    if os.path.exists(file_path) and os.path.isdir(file_path):
        file_name = os.path.join(file_path, cmd_args.get('file_name'))
        # write metrics to file
        print("Writing metrics to csv file: {}".format(file_name))
        with open(file_name, 'w') as csv_file:
            fieldNames = ['TIMESTAMP', 'METRIC_VALUE']
            csvWriter = csv.DictWriter(csv_file, fieldnames=fieldNames)
            csvWriter.writeheader() 
            print("{},{}".format(fieldNames[0], fieldNames[1]))
            for i in metrics:
                row = i.split(',')
                csvWriter.writerow({fieldNames[0]: row[0], fieldNames[1]: row[1]})
                print("{},{}".format(row[0], row[1]))
    else:
        print("Path is not a directory and/or does not exist")

# Process command line args
parser = argparse.ArgumentParser(description='Run Prometheus queries (promql) using promethues HTTP API.', epilog="Happy quering! :)")

# Args. Checkout ansible's argparse
parser.add_argument("--start",      help="Start timestamp, Defaults to time for instant vector time-series samples", required=True)
parser.add_argument("--end",        help="End timestamp", required=False)
parser.add_argument("--step",       help="Query resolution step width in duration format or float number of seconds", required=False)
parser.add_argument("--interval",   help="Prometheus range vector interval", required=False)
parser.add_argument("--promql",     help="Prometheus expression query string", required=True)
parser.add_argument("--user",  help="Prometheus basic auth user", required=False)
parser.add_argument("--pass",  help="Prometheus basic auth password", required=False)
parser.add_argument("--url",   help="Prometheus server url", required=True)
parser.add_argument("--timeout",  help="Prometheus HTTP request timeout", required=False)
parser.add_argument("--file_path",  help="File path to store csv output", required=True)
parser.add_argument("--file_name",  help="File name using workload/job name", required=True)
args = parser.parse_args()

# Main
if __name__ == '__main__':
    # Get api url, http query params and auth credentials if exist
    url, params, basic_auth = createEndpoint(vars(args))

    # Send HTTP request and pull metrics from prometheus server
    metrics = getMetrics(url, params, basic_auth.get('user'), basic_auth.get('pass'))

    # Write metrics as csv data
    writeToCsvFile(vars(args), metrics)