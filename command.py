"""Base classes for ldi commands"""

import sys
import os
from ConfigParser import ConfigParser


class Command(object):
    """HELP for --help"""
    name = "PROVIDE A NAME"
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
        option_parser.add_command(self.name,
                                  (self.run, self.add_options),
                                  self.__doc__ )

    def run(self, options, args, option_parser):
        self.options = options
        self.args = args
        try:
            self.pre_checks(option_parser)
            self.process()
            self.post_checks()
        except CommandError, exc:
            print >> sys.stderr, str(exc)
            sys.exit(1)
            
    def add_options(self, option_parser):
        for short, long, kwargs in self.opt_specs + self.global_options:
            option_parser.add_option(short, long, **kwargs)
        option_parser.min_args = self.min_args
        option_parser.max_args = self.max_args
        option_parser.prog  = "%s %s" % (os.path.basename(sys.argv[0]),
                                         self.name)
        option_parser.usage = "%%prog <options> %s" % (self.arguments)

    def pre_checks(self, option_parser):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")

class LdiCommand(Command):
    """provide command HELP here, on a single line"""
    
    global_options = [
        ('-c', '--config',
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

        sections = ['debinstall',
                    self.name,
                    'create', 'upload', 'publish', 'archive']
        for section in sections:
            if self._parser.has_section(section):
                if self._parser.has_option(section, option):
                    return self._parser.get(section, option)
        message = "No option %s in sections %s of %s" % (option, sections,
                                                        self.options.configfile)
        raise CommandError(message)

    @property
    def group(self):
        return self.get_config_value('group')
    

class CommandError(Exception):
    """raised to exit the program without a traceback"""
