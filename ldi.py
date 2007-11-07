import sys
from logilab.common import optparser

def run(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = optparser.OptionParser()
    for cmd in (Create, Upload, Publish, Archive):
        instance = cmd()
        instance.register(parser)
    run, options, args = parser.parse_command(args)
    run(options, args)

class Command:
    name="PROVIDE A NAME"
    help="PROVIDE SOME HELP"
    opt_specs = []
    def __init__(self):
        self.options = None
        self.args = None
        self.repo_name = None

    def register(self, option_parser):
        option_parser.add_command(self.name, (self.run, self.add_options), self.help)

    def server(self):
        if self.server_proxy is None:
            from Pyro import core, naming
            core.init_client(banner=0)
            nameserver =  naming.NameServerLocator().getNS()
            self.server_proxy = nameserver.resolve(':debinstall2.debinstalld').getProxy()
        return self.server_proxy
        
    def run(self, options, args):
        self.options = options
        self.args = args
        try:
            self.pre_checks()
            self.process()
            self.post_checks()
        except Exception, exc:
            print >>sys.stderr, "%s: %s" % (exc.__class__.__name__, exc)
            sys.exit(1)
            
    def add_options(self, option_parser):
        for short, long, kwargs in self.opt_specs:
            option_parser.add_option(short, long, **kwargs)
    
    def pre_checks(self):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")

class Create(Command):
    name="create"
    help="create a new repository."
    opt_specs = [('-a', '--apt-config',
                {'dest': "aptconffile",
                 'help': 'apt-ftparchive configuration file for the new repository'}
                ),
               ('-s', '--source-repo',
                {'action':'append',
                 'default': [],
                 'help': "the original repository from which a sub-repository should be created"}
                ),
               ('-p', '--package',
                {'action':'append', 'default': [],
                 'help': "a package to extract from a repository into a sub-repository"}
                ),
               ]

    
    def pre_checks(self):
        assert len(self.args) == 1, "A single repository name must be provided"
        self.repo_name = self.args[0]
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")

class Upload(Command):
    name="upload"
    help="upload a new package to the incoming queue of a repository"
    
    def pre_checks(self):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")
    
class Publish(Command):
    name="publish"
    help="process the incoming queue of a repository"
    
    def pre_checks(self):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")
    
class Archive(Command):
    name="archive"
    help="cleanup a repository by moving old unused packages to an archive directory"

    def pre_checks(self):
        pass

    def post_checks(self):
        pass

    def process(self):
        raise NotImplementedError("This command is not yet available")
    


class ArgumentError(Exception):
    """missing or wrong argument"""
