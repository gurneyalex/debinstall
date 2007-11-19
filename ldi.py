
import sys
import os
import grp
from ConfigParser import ConfigParser
from logilab.common import optparser

def run(args=None):
    if args is None:
        args = sys.argv[1:]
    usage = """usage: ldi <command> <options> [arguments]"""
    parser = optparser.OptionParser(usage=usage)
    for cmd in (Create, Upload, Publish, Archive):
        instance = cmd()
        instance.register(parser)
    run, options, args = parser.parse_command(args)
    run(options, args, parser)

class Command:
    """HELP for --help"""
    name="PROVIDE A NAME"
    opt_specs = []
    global_options = []
    min_args = 1
    max_args = 1
    arguments = "arg1"
    def __init__(self):
        self.options = None
        self.args = None
        self.repo_name = None

    def register(self, option_parser):
        option_parser.add_command(self.name, (self.run, self.add_options), self.__doc__ )

    def run(self, options, args, option_parser):
        self.options = options
        self.args = args
        try:
            self.pre_checks(option_parser)
            self.process()
            self.post_checks()
        except Exception, exc:
            print >>sys.stderr, "%s: %s" % (exc.__class__.__name__, exc)
            raise
            sys.exit(1)
            
    def add_options(self, option_parser):
        for short, long, kwargs in self.opt_specs + self.global_options:
            option_parser.add_option(short, long, **kwargs)
        option_parser.min_args = self.min_args
        option_parser.max_args = self.max_args
        option_parser.prog  = "%s %s" % (os.path.basename(sys.argv[0]), self.name)
        option_parser.usage = "%%prog <options> %s" % (self.arguments)

    def pre_checks(self, option_parser):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")

class LdiCommand(Command):
    global_options =  [('-c', '--config',
                   {'dest': 'configfile',
                    'default':'/etc/debinstall/debinstallrc',
                    'help': 'configuration file (default: /etc/debinstall/debinstallrc)'}
                   ),                  
                  ]
    def pre_checks(self, option_parser):
        #os.umask(self.get_config_value('umask'))
        pass

    def get_config_value(self, option):
        if self.options is None:
            raise RuntimeError("No configuration file available yet")
        if not hasattr(self, '_parser'):
            self._parser = ConfigParser()
            self._parser.read([self.options.configfile])
        
        sections = ['debinstall', self.name]
        for section in sections:
            if self._parser.has_section(section):
                if self._parser.has_option(section, option):
                    return self._parser.get(section, option)
        raise ValueError("No option %s in sections %s of %s" % (option, sections, self.options.configfile))

class Create(LdiCommand):
    """create a new repository"""
    name="create"
    arguments = "repository_name"
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

    def _ensure_directories(self, directories):
        for dirname in directories:
            if not os.path.isdir(dirname):
                os.makedirs(dirname)

    def _set_permissions(self, path, uid, gid, mod):
        try:
            os.chown(path, uid, gid)
            os.chmod(path, mod)
        except OSError, exc:
            raise RuntimeError('Failed to set permissions on %s: %s' % (path, exc))

    def _ensure_permissions(self, directories):
        gid= grp.getgrnam(self.get_config_value('group')).gr_gid
        uid = os.getuid()
        for dirname in directories:
            self._set_permissions(dirname, uid, gid, 00775)
            for dirpath, dirnames, filenames in os.walk(dirname):
                for subdir in dirnames:
                    subdir = os.path.join(dirpath, subdir)
                    self._set_permissions(subdir, uid, gid, 00775)
                for filename in filenames:
                    filename = os.path.join(dirpath, file)
                    self._set_permissions(filename, uid, gid, 00775)

    def pre_checks(self, option_parser):
        if self.options.aptconffile is None:
            option_parser.error('You must provide an apt.conf file')
        LdiCommand.pre_checks(self, option_parser)
        if self.options.aptconffile is None:
            raise 
        self.repo_name = self.args[0]
        directories = [self.get_config_value(confkey) for confkey in ('destination', 'configurations', 'archivedir')]
        self._ensure_directories(directories)
        self._ensure_permissions(directories)
        
    def post_checks(self):
        self._ensure_permissions(directories)
    
    def process(self):
        dest_base_dir = self.get_config_value("destination")
        conf_base_dir = self.get_config_value('configurations')
        repo_name = self.args[0]
        dest_dir = os.path.join(dest_base_dir, repo_name)
        conf_dest_dir = os.path.join(conf_base_dir, repo_name)
        if os.path.isdir(dest_dir) or os.path.isdir(conf_dest_dir):
            raise ValueError('A repository with that name already exists.')

        os.mkdir(conf_dest_dir)
        os.mkdir(dest_dir)

        
        self._ensure_permissions([conf_dest_dir, dest_dir])
        
class Upload(LdiCommand):
    """upload a new package to the incoming queue of a repository"""
    name="upload"
    max_args = sys.maxint
    arguments = "package.changes [...]"
    def pre_checks(self, option_parser):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")
    
class Publish(LdiCommand):
    """process the incoming queue of a repository"""
    name="publish"
    min_args = 0
    max_args = sys.maxint
    argument = "[source_package...]"
    def pre_checks(self, option_parser):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")
    
class Archive(LdiCommand):
    """cleanup a repository by moving old unused packages to an archive directory"""
    name="archive"

    def pre_checks(self, option_parser):
        pass

    def post_checks(self):
        pass

    def process(self):
        raise NotImplementedError("This command is not yet available")
    

class Destroy(LdiCommand):
    """completely remove a repository, its packages and the configuration files"""
    name = 'destroy'

    def process(self):
        raise NotImplementedError("This command is not yet available")
