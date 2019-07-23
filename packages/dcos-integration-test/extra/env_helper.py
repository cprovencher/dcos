import os
import sys

import requests

HELP_MESSAGE = """
ENVIRONMENT VARIABLES TO SET

  Required variables

    {begin_color}PUBLIC_SLAVE_HOSTS{end_color}
    comma-separated list of public agent private IPs

    {begin_color}SLAVE_HOSTS{end_color}
    comma-separated list of private agent private IPs

    {begin_color}MASTER_HOSTS{end_color}
    comma-separated list of master private IPs

    {begin_color}SSH_USER{end_color}
    ssh user for your Cluster

    {begin_color}MASTER_PUBLIC_IPS{end_color}
    comma-separated list of masters' public IPs


  EE-only variables

    {begin_color}DCOS_LOGIN_UNAME{end_color}
    dcos username for logging into your cluster

    {begin_color}DCOS_LOGIN_PW{end_color}
    dcos password for logging into your cluster


  Open-only variables

    {begin_color}DCOS_ACS_TOKEN{end_color}
    Obtain this token by logging into your cluster from your web browser.
    If you run integration tests before setting this variable, you will
    no longer be able to log into your cluster.


  Optional variables

    {begin_color}SSH_KEY_PATH{end_color}
    full path to the private key for your cluster
    If not set, you must add the key to your ssh agent.
""".format(begin_color='\u001b[38;5;42m', end_color='\u001b[0m')


def print_red(text):
    start = '\033[91m'
    end = '\033[0m'
    print(start + text + end)


def print_yellow(text):
    start = '\033[93m'
    end = '\033[0m'
    print(start + text + end)


def set_required_env_var(dcos_env_vars, env_var_name):
    env_var = os.getenv(env_var_name)
    if env_var is None:
        print_red("ERROR: required environment variable '{}' is not set!".format(env_var_name))
        print_red("Run 'pytest --env-help' to see all environment variables to set.")
        sys.exit(1)
    dcos_env_vars[env_var_name] = env_var


def load_env_vars():
    dcos_env_vars = {}
    required_env_vars = ['PUBLIC_SLAVE_HOSTS', 'SLAVE_HOSTS', 'MASTER_HOSTS', 'SSH_USER', 'MASTER_PUBLIC_IPS']
    non_required_env_vars = ['DCOS_LOGIN_UNAME', 'DCOS_LOGIN_PW', 'DCOS_ACS_TOKEN', 'SSH_KEY_PATH']

    for e in required_env_vars:
        set_required_env_var(dcos_env_vars, e)

    for e in non_required_env_vars:
        v = os.getenv(e)
        if v:
            dcos_env_vars[e] = v

    return dcos_env_vars


def get_leader_ip(masters):
    masters = masters.split(',')
    master = masters[0]
    r = requests.get('http://{}/exhibitor/exhibitor/v1/cluster/status'.format(master))
    assert r.status_code == 200
    assert len(r.json()) == len(masters)

    for master_info in r.json():
        if master_info['isLeader']:
            return master_info['hostname']

    raise Exception('leader not found')


def get_env_vars():
    env_vars = load_env_vars()
    if 'SSH_KEY_PATH' not in env_vars:
        print_yellow("Environment variable 'SSH_KEY_PATH' is not set. Make sure you add the ssh key for your cluster "
                     "to your ssh agent!")

    leader_ip = get_leader_ip(env_vars['MASTER_PUBLIC_IPS'])
    return env_vars['SSH_USER'], leader_ip, env_vars
