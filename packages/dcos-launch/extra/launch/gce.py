from test_util.gce import CloudDeploymentManager

log = logging.getLogger(__name__)


class CloudDeploymentManagerLauncher(launch.util.AbstractLauncher):
    def __init__(self, config: dict):
        self.GCE_client = CloudDeploymentManager(config)
        self.config = config
        log.debug('Using Cloud Deployment Manager Launcher')

    def create(self):
        #self.key_helper()
        return self.GCE_client.create()

    def wait(self):
        pass

    def describe(self):
        pass


    def delete(self):
        pass
        self.resource_group.delete()

    def key_helper(self):
        """ Adds private key to the config and injects the public key into
        the template parameters
        """
        pass

    @property
    def resource_group(self):
        pass

    def test(self, args: list, env: dict):
        pass


class BareClusterLauncher(CloudDeploymentManagerLauncher):
    """ Launches a homogeneous cluster of plain AMIs intended for onprem DC/OS
    """
    def create(self):
        pass
        """ Amend the config to add a template_body and the appropriate parameters
        """
        self.config.update({})
        return super().create()

    def get_hosts(self):
        pass

    def describe(self):
        pass

    def test(self, args, env):
        raise NotImplementedError('Bare clusters cannot be tested!')
