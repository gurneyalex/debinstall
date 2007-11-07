import sys
import atexit
import os

from Pyro import core, config as pyro_config
from Pyro import naming, errors

DEFAULT_CONFIG = {'repos_dir':'/tmp/debinstall',
                  'configs_dir': '/tmp/debinstall_configs',
                  }

class Debinstaller:
    def __init__(self, config=None):
        if config is None:
            config = DEFAULT_CONFIG
        self.config = config
        self._ensure_directories()
        
    def _ensure_directories(self):
        for confkey in self.config:
            if confkey.endswith('_dir'):
                os.makedirs(self.config[confkey])

    def list_repos(self):
        return os.listdir(self.config['configs_dir'])

class Daemon:
    def __init__(self):
        self.nsgroup = ':debinstall2'
        self.appid = 'debinstalld'
        self.delegate = Debinstaller()
        daemon = self.pyro_register()
        daemon.requestLoop()
        
    def pyro_register(self, host=None):
        """register the repository as a pyro object"""
        pyro_config.PYRO_NS_DEFAULTGROUP = self.nsgroup
        core.initServer(banner=0)
        daemon = core.Daemon()
        daemon.useNameServer(self.pyro_nameserver(host, self.nsgroup))
        # use Delegation approach
        impl = core.ObjBase()
        impl.delegateTo(self.delegate)
        daemon.connect(impl, self.appid)
        msg = 'debinstalld registered as a pyro object using group %s and id %s'
        print msg % (self.nsgroup, self.appid)
        atexit.register(pyro_unregister, self.nsgroup, self.appid)
        return daemon
    
    
    def pyro_nameserver(self, host=None, group=None):
        """locate and bind the the name server to the daemon"""
        # locate the name server
        nameserver = naming.NameServerLocator().getNS(host)
        if group is not None:
            # make sure our namespace group exists
            try:
                nameserver.createGroup(group)
            except errors.NamingError:
                pass
        return nameserver

def pyro_unregister(nsgroup, appid):
    """unregister the repository from the pyro name server"""
    nameserver = naming.NameServerLocator().getNS()
    try:
        nameserver.unregister('%s.%s' % (nsgroup, appid))
        print '%s unregistered from pyro name server' % appid
    except errors.NamingError:
        print '%s already unregistered from pyro name server !' % appid
        raise
def run(args=None):
    if args is None:
        args = sys.argv[1:]
    daemon = Daemon()
