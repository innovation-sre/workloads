#!/usr/bin/env python3

import sys
import os
import json
from time import time
from datetime import datetime, timedelta
import urllib3
import argparse
import csv
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# supress InsecureRequestWarning message
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import dependency
try:
    import requests
    from requests.auth import HTTPBasicAuth


    class BearerAuth(requests.auth.AuthBase):
        def __init__(self, token):
            self.token = token

        def __call__(self, r):
            r.headers["authorization"] = "Bearer " + self.token
            return r

except Exception as e:
    exit()


# get metrics dictionary key returned by prometheus
def getMetricKeys(metricKeys):
    # scalar values
    metric_name = "n/a"
    try:
        # if resultset is grouped by instance
        if metricKeys.get('instance') is not None:
            metric_name = metricKeys.get('instance')
        # if resultset is grouped by instance but has node name
        if metricKeys.get('node') is not None:
            metric_name = metricKeys.get('node')
        # if resultset is grouped by others
        if metric_name == 'n/a' and len(metricKeys) > 0:
            keys = list(metricKeys.keys())
            metric_name = metricKeys.get(keys[0])
    except:
        metric_name = "n/a"

    return metric_name


# parseMetrics
def parseMetrics(metrics_dictionary, result_type):
    metrics = []
    counter = 0
    for row in (metrics_dictionary['data']['result']):
        print("Metrics length: {}".format(len(metrics_dictionary['data']['result'])))
        try:
            metric_name = getMetricKeys(row['metric'])
        except IndexError:
            metric_name = "n/a"
        if result_type == 'vector':
            counter = counter + 1
            metric = round(float(row['value'][1]), 1)
            metrics.append(str(counter) + ',' + str(row['value'][0]) + ',' + str(metric) + "," + metric_name)
        elif result_type == 'matrix':
            print("Metrics matrix length: {}".format(len(row['values'])))
            for value in row['values']:
                counter = counter + 1
                metric = round(float(value[1]), 1)
                metrics.append(str(counter) + ',' + str(value[0]) + ',' + str(metric) + ',' + metric_name)
    return metrics


# create endpoint query
def createEndpoint(query_params_dict):
    secondary_urls = query_params_dict.get('secondary_urls').split(',')
    query_params = {}
    auth_credentials = {}
    if query_params_dict.get('prometheus_server_type') != 'default':
        index = query_params_dict.get('prometheus_server_index')
        if index + 1 >= len(secondary_urls):
            target_url = secondary_urls[index]
            query_params['prometheus_server_type'] = 'secondary'
        else:
            raise Exception('Provided index is out of range')
    else:
        target_url = query_params_dict.get('url')
        query_params['prometheus_server_type'] = 'default'

    # Range vector query
    if query_params_dict.get('end') is not None:
        query_params['query'] = query_params_dict.get('promql')
        query_params['start'] = query_params_dict.get('start')
        query_params['end'] = query_params_dict.get('end')
        if query_params_dict.get('step') is not None:
            query_params['step'] = query_params_dict.get('step')
        endpoint = target_url + '/api/v1/query_range'
    # Instant vector query
    else:
        query_params['query'] = query_params_dict.get('promql')
        query_params['time'] = query_params_dict.get('start')
        endpoint = target_url + '/api/v1/query'

    # Basic auth params
    if query_params_dict.get('user') is not None and query_params_dict.get('pass') is not None:
        auth_credentials['user'] = query_params_dict.get('user')
        auth_credentials['pass'] = query_params_dict.get('pass')
    if query_params_dict.get('token') is not None:
        auth_credentials['token'] = query_params_dict.get('token')

    # Request timeout param 
    if query_params_dict.get('timeout') is not None:
        query_params['timeout'] = query_params_dict.get('timeout')
    # return url , api query params and basic auth credentials
    print(query_params)
    return endpoint, query_params, auth_credentials


# Send promql request
def getMetrics(url, **request_parameters):
    query_params = request_parameters.get('query_params')
    auth = request_parameters.get('auth')
    server_type = query_params.get('prometheus_server_type', 'default')
    del query_params['prometheus_server_type']
    try:
        if server_type == 'default' \
                          and auth.get('user') is not None and auth.get('pass') is not None:
            user = auth.get('user')
            password = auth.get('pass')
            print('Using Basic auth with server_type: %s' % server_type)
            response = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False, params=query_params)
        elif server_type != 'default' and auth.get('token') is not None:
            token = auth.get('token')
            print('Using Token based auth with server_type: %s' % server_type)
            response = requests.get(url, auth=BearerAuth(token), verify=False, params=query_params)
        else:
            print('Using no authentication server_type: %s' % server_type)
            response = requests.get(url, verify=False, params=query_params)
        print("HTTP status code: {}, message: {}, URL: {}".format(response.status_code, response.reason,
                                                                  response.request.url))
        if response.status_code == 200:
            data = json.loads(response.text)
            if data['status'] != 'success':  # check success or failure
                exit()
            if len(data['data']['result']) < 0:  # check if resultset is empty
                exit()
            metrics = parseMetrics(data, data['data']['resultType'])
            return metrics
        else:
            print("Something went wrong, HTTP status code: {} - Message: {}/{}".format(response.status_code,
                                                                                       response.reason, response.text))
    except requests.exceptions.RequestException as re:
        print(re)

# convert timestamp to H:M:S
def convertTimestamp(timestamp):
    ts = datetime.datetime.fromtimestamp(int(timestamp)).isoformat()
    ts = str(ts).split('T')[1]
    return ts

# get each time or point for x axis
def getXAxisTime(start, end):
    ts = []
    while start < end:
        ts.append(convertTimestamp(start))
        start=start+60
    return ts

# Set value for undefined data point timestamp
def mergeMetrics(list1, list2, start, end):
    merged = dict(zip(list1, list2))
    ts = getXAxisTime(int(start), int(end))
    mergedMetrics = {}
    for i in ts:
        if merged.get(i) is not None:
            mergedMetrics[i] = merged.get(i)
        else:
            mergedMetrics[i] = 0.0

    return mergedMetrics


# Plot metrics graph from csv
def plotGraph(csv_file, plot_title, x_label, y_label, image_file, start_time=0, end_time=0):
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

    # Draw/plot chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    x_label = "Time <from: " + timestamp[0] + " to " + timestamp[-1] + ">"

    for k, v in data_set.items():
        print(k, v)
        merged_data = mergeMetrics(timestamp, v, start_time, end_time)
        fig.add_trace(
            go.Scatter(x=list(merged_data.keys()), y=list(merged_data.values()), name=k, mode="lines+markers", line_shape='spline', connectgaps=True),
            secondary_y=True,
        )

    for k, v in data_set.items():
        fig.update_yaxes(title_text=y_label, secondary_y=True, tickformat = 'g')

    # label angle
    fig.update_xaxes(tickangle=45)
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
                csvWriter.writerow(
                    {fieldNames[0]: row[0], fieldNames[1]: row[1], fieldNames[2]: row[2], fieldNames[3]: row[3]})
        return file_name
    else:
        print("Path is not a directory and/or does not exist: {}".format(file_path))
        return ""


# Process command line args
parser = argparse.ArgumentParser(description='Run Prometheus queries (promql) using promethues HTTP API.',
                                 epilog="Happy querying! :)")

# Args. Checkout ansible's argparse
parser.add_argument("--start", help="Start timestamp, Defaults to time for instant vector time-series samples",
                    required=True)
parser.add_argument("--end", help="End timestamp", required=False)
parser.add_argument("--step", help="Query resolution step width in duration format or float number of seconds",
                    required=True)
parser.add_argument("--interval", help="Prometheus range vector interval", required=False)
parser.add_argument("--promql", help="Prometheus expression query string", required=True)
parser.add_argument("--user", help="Prometheus basic auth user", required=False)
parser.add_argument("--pass", help="Prometheus basic auth password", required=False)
parser.add_argument("--token", help="Prometheus bearer token auth", required=False)
parser.add_argument("--url", help="Prometheus server url", required=True)
parser.add_argument("--secondary_urls", help="Prometheus server urls for additional DB endpoints", required=False)
parser.add_argument("--prometheus_server_type", help="Indicates whether to use default Prometheus DB or secondary URLs",
                    default='default', required=False)
parser.add_argument("--prometheus_server_index", help="Indicates which secondary Prometheus DB to use", required=False,
                    type=int, default=0)
parser.add_argument("--timeout", help="Prometheus HTTP request timeout", required=False)
parser.add_argument("--file_path", help="File path to store csv output", required=True)
parser.add_argument("--file_name", help="File name using workload/job name", required=True)
parser.add_argument("--print", help="Print", required=False)
parser.add_argument("--x_axis", help="x axis/label of graph", required=False)
parser.add_argument("--y_axis", help="y axis/lable of graph", required=False)
parser.add_argument("--title", help="Graph title", required=False)
parser.add_argument("--description", help="Graph description/info", required=False)
args = parser.parse_args()

# Main
if __name__ == '__main__':
    # Get api url, http query params and auth credentials if exist
    url, query_params, auth = createEndpoint(vars(args))
    print('URL: %s\nParams: %s\nAuth: %s' % (url, query_params, auth))

    # Send HTTP request and pull metrics from prometheus server
    metrics = getMetrics(url, query_params=query_params, auth=auth)
    # Write metrics as csv data
    metrics_csv_file = writeToCsvFile(vars(args), metrics)

    # Generate images
    if os.path.isfile(metrics_csv_file) and len(metrics) > 0:
        print("CSV File: {}".format(metrics_csv_file))
        cmd_params = vars(args)
        title = cmd_params.get('title')
        x_label = cmd_params.get('x_axis')
        y_label = cmd_params.get('y_axis')
        start = cmd_params.get('start')
        end = cmd_params.get('end')
        description = cmd_params.get('description')
        file_path = cmd_params.get('file_path')
        file_name = cmd_params.get('file_name').split('.', 1)[0] + '-graph.png'
        image_file = os.path.join(file_path, file_name)
        print("Image File: {}".format(image_file))
        plotGraph(metrics_csv_file, title, x_label, y_label, image_file, start_time=start, end_time=end)
