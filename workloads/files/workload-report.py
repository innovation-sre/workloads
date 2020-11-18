#!/usr/bin/env python3

import sys
import os
import json
from time import time
from datetime import datetime, timedelta
import urllib3
import argparse
import csv
import pandas as pd
import plotly.express as px
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    counter=0
    for row in (metrics_dictionary['data']['result']):
        print("Metrics lenght: {}".format(len(metrics_dictionary['data']['result'])))
        keys = list(row.get('metric').keys())
        try:
            metric_name = row['metric'].get(keys[0])
        except IndexError:
            metric_name = "n/a"
        if result_type == 'vector':
            counter = counter + 1
            metric = round(float(row['value'][1]), 1)
            metrics.append(str(counter) + ',' + str(row['value'][0]) + ',' + str(metric) + "," + metric_name)
        elif result_type == 'matrix':
            print("Metrics matrix lenght: {}".format(len(row['values'])))
            for value in row['values']:
                counter = counter + 1
                metric = round(float(value[1]), 1)
                metrics.append(str(counter) + ',' + str(value[0]) + ',' + str(metric) + ',' + metric_name)
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
    print(query_params)
    return endpoint, query_params, auth_credentials

# Send promql request
def getMetrics(url, params, user, password):
    try:
        if user is not None and password is not None:
            response = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False, params=params)
        else:
            response = requests.get(url, verify=False, params=params)
        print("HTTP status code: {}, message: {}, URL: {}".format(response.status_code, response.reason, response.request.url))
        if response.status_code == 200:
            data = json.loads(response.text)
            if data['status'] != 'success': # check success or failure
                exit()
            if len(data['data']['result']) < 0: # check if resultset is empty
                exit()
            metrics = parseMetrics(data, data['data']['resultType'])
            return metrics   
        else:
           print("Something went wrong, HTTP status code: {} - Message: {}/{}".format(response.status_code, response.reason, response.text))
    except requests.exceptions.RequestException as re:
        print(re)

# Plot metrics graph from csv

def plotGraph(csv_file, plot_title, x_label, y_label, image_file):
    x_axis = []
    y_axis = []
    timestamp = []
    data_set = {}

    with open(csv_file, newline='') as csvfile:
        data = csv.reader(csvfile, delimiter=',')
        for row in data:
            if row[0] == 'SN':
                continue
            # timestamps
            if row[1] not in x_axis:
                x_axis.append(row[1])
            # metrics name/group rows
            if row[3] not in y_axis:
                y_axis.append(row[3])

    for i in x_axis:
        ts = datetime.datetime.fromtimestamp(int(i)).isoformat()
        timestamp.append(str(ts).split('T')[1])

    # Group metrics by dimension i
    for i in y_axis:
        data_set[i] = []

    with open(csv_file, newline='') as csvfile:
        data = csv.reader(csvfile, delimiter=',')
        for row in data:
            for y_axis_value in y_axis:
                if y_axis_value == row[3]:
                    tmp = data_set.get(y_axis_value)
                    if row[2] != None and row[2] != 'nan' and row[2] != "" and row[2] != 'NaN':
                        tmp.append(row[2]) 
                    else:
                        tmp.append(0.0)
                    data_set[y_axis_value] = tmp

    # Draw/plat chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x_label = "Time <from: " + timestamp[0] + " to " + timestamp[-1] + ">"
    
    for k,v in data_set.items():
        print(k, v)
        fig.add_trace(
            go.Scatter(x=timestamp, y=v, name=k, mode="lines+markers", line_shape='spline', connectgaps=True),
            secondary_y=True,
        )

    for k,v in data_set.items():
        fig.update_yaxes(title_text=y_label, secondary_y=True)


    # label angle
    fig.update_xaxes(tickangle = 45)
    # update plat labels with titles
    fig.update_layout(
        title=plot_title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        legend_title="Legend"
    )
    # Write image to file
    fig.write_image(image_file, width=900, height=600)

# File path to store csv output
def writeToCsvFile(cmd_args, metrics):
    file_path = cmd_args.get('file_path')
    if os.path.exists(file_path) and os.path.isdir(file_path):
        file_name = os.path.join(file_path, cmd_args.get('file_name'))
        # write metrics to file
        print("Writing metrics to csv file: {}".format(file_name))
        with open(file_name, 'w') as csv_file:
            fieldNames = ['SN', 'TIMESTAMP', 'METRIC', 'GROUP']
            csvWriter = csv.DictWriter(csv_file, fieldnames=fieldNames)
            csvWriter.writeheader()
            print("{},{},{},{}".format(fieldNames[0], fieldNames[1], fieldNames[2], fieldNames[3]))
            for i in metrics:
                row = i.split(',')
                csvWriter.writerow({fieldNames[0]: row[0], fieldNames[1]: row[1], fieldNames[2]: row[2], fieldNames[3]: row[3]})
        return file_name
    else:
        print("Path is not a directory and/or does not exist: {}".format(file_path))
        return ""

# Process command line args
parser = argparse.ArgumentParser(description='Run Prometheus queries (promql) using promethues HTTP API.', epilog="Happy quering! :)")

# Args. Checkout ansible's argparse
parser.add_argument("--start",      help="Start timestamp, Defaults to time for instant vector time-series samples", required=True)
parser.add_argument("--end",        help="End timestamp", required=False)
parser.add_argument("--step",       help="Query resolution step width in duration format or float number of seconds", required=True)
parser.add_argument("--interval",   help="Prometheus range vector interval", required=False)
parser.add_argument("--promql",     help="Prometheus expression query string", required=True)
parser.add_argument("--user",  help="Prometheus basic auth user", required=False)
parser.add_argument("--pass",  help="Prometheus basic auth password", required=False)
parser.add_argument("--url",   help="Prometheus server url", required=True)
parser.add_argument("--timeout",  help="Prometheus HTTP request timeout", required=False)
parser.add_argument("--file_path",  help="File path to store csv output", required=True)
parser.add_argument("--file_name",  help="File name using workload/job name", required=True)
parser.add_argument("--print",  help="Print", required=False)
parser.add_argument("--x_axis",  help="x axis/label of graph", required=False)
parser.add_argument("--y_axis",  help="y axis/lable of graph", required=False)
parser.add_argument("--title",  help="Graph title", required=False)
parser.add_argument("--description",  help="Graph description/info", required=False)
args = parser.parse_args()

# Main
if __name__ == '__main__':
    # Get api url, http query params and auth credentials if exist
    url, params, basic_auth = createEndpoint(vars(args))

    # Send HTTP request and pull metrics from prometheus server
    metrics = getMetrics(url, params, basic_auth.get('user'), basic_auth.get('pass'))

    # Write metrics as csv data
    metrics_csv_file = writeToCsvFile(vars(args), metrics)

    #Generate images
    if os.path.isfile(metrics_csv_file) and len(metrics) > 0:
        print("CSV File: {}".format(metrics_csv_file))
        cmd_params = vars(args)
        title = cmd_params.get('title')
        x_label = cmd_params.get('x_axis')
        y_label = cmd_params.get('y_axis')
        description = cmd_params.get('description')
        file_path = cmd_params.get('file_path')
        file_name = cmd_params.get('file_name').split('.', 1)[0] + '-graph.png'
        image_file = os.path.join(file_path, file_name)
        print("Image File: {}".format(image_file))
        plotGraph(metrics_csv_file, title, x_label, y_label, image_file)