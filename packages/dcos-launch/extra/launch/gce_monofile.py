from oauth2client.client import GoogleCredentials
from googleapiclient import discovery
from googleapiclient.errors import HttpError
import time, sys, os, yaml
import launch.util
from retrying import retry


class GCE:
    def __init__(self, config, cwd, config_path):
        self.config = config
        self.config_path = config_path
        self.cwd = cwd

        creds_path = self.config['credentials'] if 'credentials' in self.config else os.path.join(cwd, 'credentials', 'gce-creds.json')
        os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', creds_path)
        
        template_path = self.config['template_path'] if 'template_path' in self.config else os.path.join(cwd, 'templates', 'gce-template.yaml')
        with open(template_path, 'r') as t:
            self.template_content = t.read()
        self.template_dict = yaml.load(self.template_content)
        self.cluster_name = self.template_dict['resources'][0]['name']

        credentials = GoogleCredentials.get_application_default()
        self.v1_service = discovery.build('compute', 'v1', credentials=credentials)
        self.v2_service = discovery.build('deploymentmanager', 'v2', credentials=credentials)

    def create(self):
        body = {
            'name': self.config['deployment_name'],
            'target': {
                'config': {
                    'content': self.template_content
                }
            }
        }

        request = self.v2_service.deployments().insert(project=self.config['project_id'], body=body)
        response = request.execute()

        self.key_helper()

        return response

    def check_exception(exception):
        return isinstance(exception, HttpError)

    @retry(wait_fixed=2000, retry_on_exception=check_exception, stop_max_attempt_number=7)
    def get_fingerprint(self):
        request = self.v1_service.instances().get(project=self.config['project_id'], zone=self.config['zone'], instance=self.cluster_name)
        response = request.execute()
        return response['metadata']['fingerprint']

    def key_helper(self):
        """ Adds private key to the self.config and injects the public key into
        the template parameters
        """
        if not self.config.get('key_helper'):
            return

        private_key, public_key = launch.util.generate_rsa_keypair()
        priv_key_path = os.path.join(cwd, 'keys', self.cluster_name)

        with open(priv_key_path, 'w+') as p:
            p.write(private_key.decode())

        body = {
            "kind": "compute#metadata",
            'fingerprint': self.get_fingerprint(),
            'items': [
                {
                    'key': 'ssh-keys',
                    'value': 'dcos:ssh-rsa ' + public_key.decode() + ' dcos'
                }
            ]
        }

        request = self.v1_service.instances().setMetadata(project=self.config['project_id'], zone=self.config['zone'], instance=self.cluster_name, body=body)
        response = request.execute()

        return False

    def check_status(response):
        status = response['operation']['status']
        if status  == 'DONE':
            return False
        elif status == 'RUNNING':
            return True
        else:
            raise Exception('Deployment failed')

    @retry(wait_fixed=2000, retry_on_result=check_status)
    def wait(self):
        request = self.v2_service.deployments().get(project=self.config['project_id'], deployment=self.config['deployment_name'])
        response = request.execute()
        return response

    def delete(self):
        request = self.v2_service.deployments().delete(project=self.config['project_id'], deployment=self.config['deployment_name'])
        response = request.execute()
        return response

    def get_cluster_info(self):
        request = self.v1_service.instances().get(project=self.config['project_id'], zone=self.config['zone'], instance=self.cluster_name)
        response = request.execute()
        return response

if __name__ == '__main__':
    option = sys.argv[1]
    cwd = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(cwd, 'sample_configs', 'gce-config.yaml')
    with open(config_path, 'r') as gc:
        config = yaml.load(gc)
    gce = GCE(config, cwd, config_path)
    response = ''

    try:
        if option == 'create':
            print('creating cluster')
            response = gce.create()
        elif option == 'wait':
            print('waiting for deployment')
            response = gce.wait()
        elif option == 'delete':
            print('deleting deployment')
            response = gce.delete()
        elif option == 'get':
            response = gce.get_cluster_info()
        elif option == 'update_key':
            response = gce.key_helper()
    except HttpError as e:
        if 'HttpError 404' in str(e):
            print("The resource you are trying to access doesn't exist")
        elif 'HttpError 409' in str(e):
            print("The resource you are trying to access is either being created (operation conflict) or already exists") 
        else:
            raise e

    print(response)
