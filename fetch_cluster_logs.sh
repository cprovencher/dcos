#!/bin/bash

set +e
set -x

DCOS_ACS_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik9UQkVOakZFTWtWQ09VRTRPRVpGTlRNMFJrWXlRa015Tnprd1JrSkVRemRCTWpBM1FqYzVOZyJ9.eyJlbWFpbCI6ImFsYmVydEBiZWtzdGlsLm5ldCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczovL2Rjb3MuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA5OTY0NDk5MDExMTA4OTA1MDUwIiwiYXVkIjoiM3lGNVRPU3pkbEk0NVExeHNweHplb0dCZTlmTnhtOW0iLCJleHAiOjIwOTA4ODQ5NzQsImlhdCI6MTQ2MDE2NDk3NH0.OxcoJJp06L1z2_41_p65FriEGkPzwFB_0pA9ULCvwvzJ8pJXw9hLbmsx-23aY2f-ydwJ7LSibL9i5NbQSR2riJWTcW4N7tLLCCMeFXKEK4hErN2hyxz71Fl765EjQSO5KD1A-HsOPr3ZZPoGTBjE0-EFtmXkSlHb1T2zd0Z8T5Z2-q96WkFoT6PiEdbrDA-e47LKtRmqsddnPZnp0xmMQdTr2MjpVgvqG7TlRvxDcYc-62rkwQXDNSWsW61FcKfQ-TRIZSf2GS9F9esDF4b5tRtrXcBNaorYa9ql0XAWH5W_ct4ylRNl3vwkYKWa4cmPvOqT5Wlj9Tf0af4lNO40PQ
DCOS_USERNAME=bootstrap
DCOS_PASSWORD=deleteme

# We don't want to try collecting the logs if the machines didn't create successfully
if [ ! -f cluster_ip.json ]; then
  exit 0
fi

# Setting up the dcos cli
master_ip=$(cat cluster_ip.json | jq -r .masters[0].public_ip)
metadata=$(curl -s ${master_ip}/dcos-metadata/dcos-version.json)
dcos_version=$(echo "$metadata" | jq -r .version)
[[ $(echo "$metadata" | jq -r '.["dcos-variant"]') = "enterprise" ]]
enterprise_edition_test=$?

if [[ $dcos_version = "1.9"* ]]; then
  wget https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.9/dcos --output-document=dcos-cli
  chmod +x dcos-cli
  ./dcos-cli config set core.dcos_url $master_ip
  ./dcos-cli config set core.ssl_verify False

  if [[ $enterprise_edition_test = 0 ]]; then
    ./dcos-cli auth login --username $DCOS_USERNAME --$DCOS_PASSWORD # for enterprise
  else
    ./dcos-cli config set core.dcos_acs_token $DCOS_ACS_TOKEN # for open
  fi
else
  wget https://downloads.dcos.io/binaries/cli/linux/x86-64/dcos-1.12/dcos --output-document=dcos-cli
  chmod +x dcos-cli
  if [[ $enterprise_edition_test = 0 ]]; then
    ./dcos-cli cluster setup $master_ip --username $DCOS_USERNAME --password $DCOS_PASSWORD --insecure
  else
    ./dcos-cli cluster setup $master_ip --insecure <<< $DCOS_ACS_TOKEN
  fi
fi

# get diagnostics
bundle_name=$(./dcos-cli node diagnostics create all | grep -o bundle-.*)
echo "bundle name: ${bundle_name}"

status_output="$(./dcos-cli node diagnostics --status)"
while [[ $status_output =~ "is_running: True" ]]; do
    echo "Diagnostics job still running, retrying in 5 seconds."
    sleep 5
    status_output="$(./dcos-cli node diagnostics --status)"
done

./dcos-cli node diagnostics download $bundle_name

nodes_info_json=$(./dcos-cli node --json)

for node_info in $(echo "$nodes_info_json" | jq -r '.[] | @base64'); do
  _jq() {
   echo "$node_info" | base64 --decode | jq -r ${1}
  }

  id=$(_jq '.id')
  pid=$(_jq '.pid')

  # get journald logs
  ./dcos-cli node ssh journalctl --mesos-id=$id > ${pid}_journald.log

  # get mesos sandbox logs
  ./dcos-cli node log --mesos-id=$id > ${pid}_sandbox.log
done
