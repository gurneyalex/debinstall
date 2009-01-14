# Copyright (c) 2007-2008 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""Base classes for ldi commands"""

import sys
import os
import os.path as osp
from ConfigParser import ConfigParser
import logging

from debinstall.logging_handlers import CONSOLE, isatty


class Command(object):
    """HELP for --help"""
    name = "PROVIDE A NAME"
    opt_specs = []
    global_options = []
    min_args = 1
    max_args = 1
    arguments = "arg1"
    def __init__(self, debug=False):
        self.options = None
        self.args = None
        self.repo_name = None
        self.logger = logging.getLogger('debinstall.%s' % self.name)
        if debug:
            self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(CONSOLE)

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
            self.logger.critical(exc)
            sys.exit(1)
            
    def add_options(self, option_parser):
        for shortname, longname, kwargs in self.opt_specs + self.global_options:
            option_parser.add_option(shortname, longname, **kwargs)
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
        # just for having the option in the help documentation
        # see logging_handlers.py for details
        ('', '--no-color',
         {'dest': 'no_color',
          'default': not isatty,
          'action': 'store_true',
          'help': "print log messages without color"}
         ),
        ]

    def __init__(self, debug=False):
        Command.__init__(self, debug)
        self._parser = None
        self._repo_parser = None

    def pre_checks(self, option_parser):
        #os.umask(self.get_config_value('umask'))
        pass

    def _get_ldi_conf_path(self, reponame):
        configdir = self.get_config_value("configurations")
        return  osp.join(configdir, '%s-ldi.conf' % reponame)

    def get_repo_config_value(self, reponame, option):
        if self.options is None:
            raise RuntimeError("No configuration file available yet")
        if self._repo_parser is None:
            self._repo_parser = ConfigParser()
            configfile = self._get_ldi_conf_path(reponame)
            self._repo_parser.read([configfile])

        sections = ['subrepository']
        for section in sections:
            if self._repo_parser.has_section(section):
                if self._repo_parser.has_option(section, option):
                    value = self._repo_parser.get(section, option)
                    self.logger.debug('value for %s: %s', option, value)
                    return value

        message = "No option %s in sections %s of %s" % (option, sections,
                                        self._get_ldi_conf_path(reponame))
        raise CommandError(message)

    def get_config_value(self, option):
        if self.options is None:
            raise RuntimeError("No configuration file available yet")
        if self._parser is None:
            self._parser = ConfigParser()
            self._parser.read([self.options.configfile])

        sections = ['debinstall',
                    self.name,
                    'create', 'upload', 'publish', 'archive']
        for section in sections:
            if self._parser.has_section(section):
                if self._parser.has_option(section, option):
                    value = self._parser.get(section, option)
                    self.logger.debug('value for %s: %s', option, value)
                    return value
        message = "No option %s in sections %s of %s" % (option, sections,
                                                        self.options.configfile)
        raise CommandError(message)

    @property
    def group(self):
        return self.get_config_value('group')


class CommandError(Exception):
    """raised to exit the program without a traceback"""
