#!/usr/bin/env bash
set -x

# Check cluster's health
if [[ ${CERBERUS_URL} ]]; then
  response=$(curl ${CERBERUS_URL})
  if [ "$response" != "True" ]; then
    echo "Cerberus status is False, Cluster is unhealthy"
    exit 1
  fi
fi

date
oc get clusterversion
if [ $? -ne 0 ]; then
  echo "Workload Failed for $HTTP_TEST_SUFFIX , Unable to connect to the cluster"
  exit 1
fi

if [[ ${COMPARE} == "true" ]]; then
  echo $BASELINE_CLOUD_NAME,$HTTP_TEST_SUFFIX > uuid.txt
else
  echo $HTTP_TEST_SUFFIX > uuid.txt
fi

echo "Starting test for: $HTTP_TEST_SUFFIX"
echo "[orchestration]" > inventory; echo "${ORCHESTRATION_HOST:-localhost}" >> inventory
time ansible-playbook -vv -i inventory workloads/http.yml
for (( i=1; i<=5; i++ ))
do
  pod_name=$(oc get pods -n scale-ci-tooling | grep scale-ci-http | awk '{print $1}')
  pod_status=$(oc get pods -n scale-ci-tooling | grep scale-ci-http | awk '{print $3}')
  echo "$pod_name -> $pod_status"
  sleep 10
  if [ $pod_status == "Running" ]; then
    oc logs -f $pod_name -n scale-ci-tooling
  else
    break
  fi
done

router_state=$(oc get job -n scale-ci-tooling scale-ci-http -o jsonpath='{.status.succeeded}')
if [ "$router_state" == "1" ] ; then
  echo "Workload Succeeded"
else
  echo "Workload Failed"
  exit 1
fi

compare_router_uuid=$(oc logs -n scale-ci-tooling $(oc get pods -n scale-ci-tooling | grep "scale-ci-http" |awk '{print $1}') | grep UUID | awk '{print $3}')
baseline_router_uuid=${BASELINE_ROUTER_UUID}

if [[ ${COMPARE} == "true" ]]; then
  echo ${baseline_router_uuid},${compare_router_uuid} >> uuid.txt
else
  echo ${compare_router_uuid} >> uuid.txt
fi

#../run_compare.sh ${baseline_router_uuid} ${compare_router_uuid} mb
#
#python3 workloads/router-perf/csv_gen.py --files compare.yaml
