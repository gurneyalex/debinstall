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

"""The ldi command provides access to various subcommands to
manipulate debian packages and repositories"""
import sys
import os.path as osp
import glob

from logilab.common import optparser

from debinstall.debfiles import Changes
from debinstall.command import LdiCommand, CommandError
from debinstall import shelltools as sht
from debinstall import apt_ftparchive
from debinstall.__pkginfo__ import version

def run(args=None):
    if args is None:
        args = sys.argv[1:]
    usage = """usage: ldi <command> <options> [arguments]"""
    parser = optparser.OptionParser(usage=usage, version='debinstall %s' % version)
    for cmd in (Create, Upload, Publish, Archive):
        instance = cmd(debug=True)
        instance.register(parser)
    run, options, args = parser.parse_command(args)
    run(options, args, parser)


class Create(LdiCommand):
    """create a new repository"""
    name = "create"
    arguments = "repository_name"
    opt_specs = [
        ('-a', '--apt-config',
         {'dest': "aptconffile",
          'help': 'apt-ftparchive configuration file for the new repository'}
         ),
        ('-s', '--source-repo',
         {'action':'append',
          'default': [],
          'dest': 'source_repositories',
          'help': "the original repository from which a sub-repository "
                  "should be created"}
         ),
        ('-p', '--package',
         {'action':'append',
          'default': [],
          'dest': 'packages',
          'help': "a package to extract from a repository into a "
                  "sub-repository"}
         ),
        ] 


    def pre_checks(self, option_parser):
        LdiCommand.pre_checks(self, option_parser)
        self.repo_name = self.args[0]
        directories = [self.get_config_value(confkey)
                       for confkey in ('destination', 'configurations')]
        sht.ensure_directories(directories)
        sht.ensure_permissions(directories, self.group, 0775, 0664)
                
    def post_checks(self):
        directories = [self.get_config_value(confkey)
                       for confkey in ('destination', 'configurations')]
        sht.ensure_permissions(directories, self.group, 0775, 0664)
    
    def process(self):
        dest_base_dir = self.get_config_value("destination")
        conf_base_dir = self.get_config_value('configurations')
        repo_name = self.args[0]
        dest_dir = osp.join(dest_base_dir, repo_name)
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repo_name)
        ldiconf = osp.join(conf_base_dir, '%s-ldi.conf' % repo_name)
        if osp.isdir(dest_dir) or osp.isfile(aptconf) or osp.isfile(ldiconf):
            raise CommandError('A repository with that name already exists.')

        if self.options.source_repositories:
            if not self.options.packages:
                message = 'No packages to extract from the source repositories'
                raise CommandError(message)
        if self.options.packages:
            if not self.options.source_repositories:
                message = 'No source repositories for package extraction'
                raise CommandError(message)

        for directory in [dest_dir,
                          osp.join(dest_dir, 'incoming'),
                          osp.join(dest_dir, 'debian'),
                          ]:
            self.logger.info('creation of %s', directory)
            sht.mkdir(directory, self.group, 0775)

        if self.options.aptconffile is not None:
            self.logger.info('copying %s to %s', self.options.aptconffile, aptconf)
            sht.copy(self.options.aptconffile, aptconf)
        else:
            import aptconffile
            self.logger.info('writing default aptconf to %s', aptconf)
            aptconffile.writeconf(aptconf, self.group, 0664)
        import ldiconffile
        self.logger.info('writing ldiconf to %s', ldiconf)
        ldiconffile.writeconf(ldiconf, self.group, 0664,
                              self.options.source_repositories,
                              self.options.packages)

class Upload(LdiCommand):
    """upload a new package to the incoming queue of a repository"""
    name = "upload"
    min_args = 2
    max_args = sys.maxint
    arguments = "repository package.changes [...]"


    def _get_all_package_files(self, changes_files):
        file_list = []
        for filename in changes_files:
            dirname = osp.dirname(filename)
            self.logger.info('preparing upload of %s', filename)
            all_files = Changes(filename).get_all_files()
            for candidate in all_files:
                try:
                    fdesc = open(candidate)
                except IOError, exc:
                    raise CommandError('Cannot read %s from %s: %s' % (candidate, filename, exc))
            file_list += all_files
        return file_list

    def _check_signatures(self, changes_files):
        """return True if the changes files and appropriate dsc files
        are correctly signed.
        
        raise CommandError otherwise.
        """
        if self.get_config_value('check_signature').lower() in ('no', 'false'):
            self.logger.info("Signature checks skipped")
            return True
        failed = []
        for filename in changes_files:
            Changes(filename).check_sig(failed)
            
        if failed:
            raise CommandError('The following files are not signed:\n' + \
                               '\n'.join(failed))
        return True

    def _run_checkers(self, changes_files):
        checkers = self.get_config_value('checkers').split()
        failed = []
        for filename in changes_files:
            Changes(filename).run_checkers(checkers, failed)
        if failed:
            raise CommandError('The following packaging errors were found:\n' + \
                               '\n'.join(failed))
    
        
    def process(self):
        repository = self.args[0]
        changes_files = self.args[1:]
        self._check_signatures(changes_files)
        all_files = self._get_all_package_files(changes_files)
        destdir = osp.join(self.get_config_value('destination'),
                           repository,
                           'incoming')
        self.logger.info('uploading packages to %s', destdir)
        for filename in all_files:
            sht.copy(filename, destdir, self.group, 0775)

class Publish(Upload):
    """process the incoming queue of a repository"""
    name = "publish"
    min_args = 1
    max_args = sys.maxint
    argument = "repository [package.changes...]"


    def _get_incoming_changes(self):
        incoming = osp.join(self.get_config_value('destination'),
                            self.args[0],
                            'incoming')
        changes_files = self.args[1:]
        if changes_files:
            for change in changes_files:
                if osp.isabs(change):
                    raise CommandError('%s is not a relative path' % change)
            return [osp.join(incoming, change) for change in changes_files]
        else:
            return glob.glob(osp.join(incoming, '*.changes'))
        
        
    def process(self):
        repository = self.args[0]
        destdir = osp.join(self.get_config_value('destination'),
                           repository,
                           'debian')
        
        changes_files = self._get_incoming_changes()
        
        self._check_signatures(changes_files)
        self._run_checkers(changes_files)
        all_files = self._get_all_package_files(changes_files)
        self.logger.info('uploading packages to %s', destdir)
        for filename in all_files:
            sht.move(filename, destdir, self.group, 0664)

        conf_base_dir = self.get_config_value('configurations')
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repository)
        apt_ftparchive.clean(destdir)
        self.logger.info('Running apt-ftparchive generate')
        apt_ftparchive.generate(destdir, aptconf, self.group)
        self.logger.info('Running apt-ftparchive release')
        apt_ftparchive.release(destdir, aptconf, self.group)
        self._sign_repo(destdir)

    def _sign_repo(self, repository):
        if self.get_config_value("sign_repo").lower() in ('no', 'false'):
            return
        self.logger.info('Signing release')
        apt_ftparchive.sign(repository,
                            self.get_config_value('keyid'),
                            self.group)
        
class Archive(LdiCommand):
    """cleanup a repository by moving old unused packages to an
    archive directory"""
    name = "archive"

    

class Destroy(LdiCommand):
    """completely remove a repository, its packages and the
    configuration files"""
    name = 'destroy'

