# Stress Workload

The Stress workload playbook is `workloads/stress.yml` and will run stress tool against a certain set of nodes to saturate the CPU, Memory and Disk.





Running from CLI:

```sh
$ cp workloads/inventory.example inventory
$ # Add orchestration host to inventory
$ # Edit vars in workloads/vars/stress.yml or define Environment vars (See below)
$ time ansible-playbook -vv -i inventory workloads/stress.yml
```

## Environment variables

### ES_HOST
Default: ``
Elasticsearch server host address (currently used by snafu), set to index results from cluster loader

### ES_PORT
Default: ``
Elasticsearch server port (currently used by snafu), set to index results from cluster loader

### ES_INDEX_PREFIX
Default: `snafu`
Elasticsearch server index prefix (currently used by snafu)

### SNAFU_USER
Default: `scale-ci`
user running the tests, used for identifying test results.

### SNAFU_CLUSTER_NAME
Default: (defaults to the clustername in the machineset)
clustername on which the tests are running, used for identifying test results.


### PUBLIC_KEY

Default: `~/.ssh/id_rsa.pub`  
Public ssh key file for Ansible.

### PRIVATE_KEY

Default: `~/.ssh/id_rsa`  
Private ssh key file for Ansible.

### ORCHESTRATION_USER

Default: `root`  
User for Ansible to log in as. Must authenticate with PUBLIC_KEY/PRIVATE_KEY.

### WORKLOAD_IMAGE

Default: `quay.io/openshift-scale/scale-ci-workload`  
Container image that runs the workload script.

### WORKLOAD_JOB_NODE_SELECTOR

Default: `false`  
Enables/disables the node selector that places the workload job on the `workload` node.

### WORKLOAD_JOB_TAINT

Default: `false`  
Enables/disables the toleration on the workload job to permit the `workload` taint.

### WORKLOAD_JOB_PRIVILEGED

Default: `false`  
Enables/disables running the workload pod as privileged.

### KUBECONFIG_FILE

Default: `~/.kube/config`  
Location of kubeconfig on orchestration host.

### ENABLE_PBENCH_AGENTS

Default: `false`  
Enables/disables the collection of pbench data on the pbench agent Pods. These Pods are deployed by the tooling playbook
and if this option is enabled then tooling playbook needs to be executed prior to this test.

### ENABLE_PBENCH_COPY

Default: `true`  

Enables/disables the copying of pbench data to a remote results server for further analysis.
As of now, this test requires valid `PBENCH_SERVER` where it will copy results at end of test.

### PBENCH_SSH_PRIVATE_KEY_FILE

Default: `~/.ssh/id_rsa`  
Location of ssh private key to authenticate to the pbench results server.

### PBENCH_SSH_PUBLIC_KEY_FILE

Default: `~/.ssh/id_rsa.pub`  
Location of the ssh public key to authenticate to the pbench results server.

### PBENCH_SERVER

Default: There is no public default.  
DNS address of the pbench results server.

### SCALE_CI_RESULTS_TOKEN

Default: There is no public default.  
Future use for pbench and prometheus scraper to place results into git repo that holds results data.

### JOB_COMPLETION_POLL_ATTEMPTS

Default: `10000`  

Number of retries for Ansible to poll if the workload job has completed.
Poll attempts delay 10s between polls with some additional time taken for each polling action depending on the orchestration host setup.
STRESS test for many pods and big file sizes can run for hours and either we rise `JOB_COMPLETION_POLL_ATTEMPTS` to
higt value, or remove fully checking for `JOB_COMPLETION_POLL_ATTEMPTS` for STRESS test.


### AZURE_AUTH
Default: false
Set it to true when running OCP on Azure.

### AZURE_AUTH_FILE
Default: ''
Path to the Azure auth file - terraform.azure.auto.tfvars.json found in the openshift install dir on the orchestration host i.e scale-ci-deploy/scale-ci-azure/terraform.azure.auto.tfvars.json.

### STRESS_PREFIX

Default: `fiotest`

Prefix to use for FIO I/O test

### STRESS_CLEANUP

Default: `true`
If set to `true` test project will be removed at end of test.

### STRESS_BASENAME

Default: `fiotest`  
Basename used by cluster loader for the project(s) it creates.

### STRESS_MAX_NODES

Default: `1`  
Maximum number of nodes on which we create the STRESS test

### STRESS_POD_IMAGE

Default: `quay.io/openshift-scale/scale-ci-fio:latest`

Container image to use for FIO Pods

### STRESS_STEPSIZE

Default: `1`  
Number of Pods for cluster loader will create before waiting for Pods to become running.

### STRESS_PAUSE

Default: `0`  
Period of time (in seconds) for cluster loader to pause after creating Pods and waiting for them to be "Running" state.
When `STRESS_PAUSE` is zero, cluster loader will create pods in fastest possible manner.


### STRESS_RUNTIME

Default: `60`

Stress test runtime

### STRESS_NODESELECTOR

Default: ""

For cases when it is necessary to have FIO pods to be assigned to already labeled nodes with specific label
`STRESS_NODESELECTOR` allows to specify desired label.
FIO I/O test does not label nodes, it expect that labels are already assigned to nodes.



### Smoke test variables

```
STRESS_PREFIX=stress
STRESS_CLEANUP=true
STRESS_BASENAME=stress
ENABLE_PBENCH_COPY=true
STRESS_NODESELECTOR=workload=true
STRESS_MAX_NODES=1
STRESS_CONTAINER_IMAGE="alexeiled/stress-ng"
STRESS_RUNTIME=60s # timeout after T seconds
STRESS_DAEMONS=5 # start N workers creating multiple daemons
STRESS_CPU=4 # start N workers spinning on sqrt(rand())
STRESS_CPU_LOAD=100  # load CPU by P %, 0=sleep, 100=full load 
STRESS_IO=100 # start N workers spinning on sync()
STRESS_MEM=100 # start N workers spinning on anonymous mmap
STRESS_MEM_BYTES=1G # allocate N bytes per vm worker (default 256MB)
STRESS_ADDITIONAL_ARGS=--metrics-brief
STRESS_STEPSIZE=50
STRESS_PAUSE=60

```
