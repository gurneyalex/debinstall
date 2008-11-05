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
import os
import re
import os.path as osp
import glob

from logilab.common import optparser

from debinstall.debfiles import Changes
from debinstall.command import LdiCommand, CommandError
from debinstall import shelltools as sht
from debinstall import apt_ftparchive
from debinstall.__pkginfo__ import version

def run(args=None):
    if sys.argv[0] == "-c": # launched by binary script using python -c
        sys.argv[0] = "ldi"
        debug = False
    else:
        debug = True
    os.umask(0002)
    if args is None:
        args = sys.argv[1:]
    usage = """usage: ldi <command> <options> [arguments]"""
    parser = optparser.OptionParser(usage=usage,
                                    version='debinstall %s' % version)
    for cmd in (Create,
                Upload,
                Publish,
                List,
                #Archive,
                #Destroy,
                Configure,
                ):
        instance = cmd(debug=debug)
        instance.register(parser)
    runfunc, options, args = parser.parse_command(args)
    runfunc(options, args, parser)


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
        ('-d', '--distribution',
         {'dest': 'distribution',
          'help': 'the name of the distribution in the repository',
          'action': 'append',
          }
         ),
        ]

    def process(self):
        origin = self.get_config_value("origin")
        dest_base_dir = self.get_config_value("destination")
        conf_base_dir = self.get_config_value('configurations')
        distnames = self.options.distribution or \
                   [self.get_config_value('default_distribution')]
        if len(distnames) == 1:
            distnames = re.split(r'[^\w]+', distames[0])
        repo_name = self.args[0]
        dest_dir = osp.join(dest_base_dir, repo_name)
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repo_name)
        ldiconf = osp.join(conf_base_dir, '%s-ldi.conf' % repo_name)

        directories = [dest_dir]
        for distname in distnames:
            directories.append(osp.join(dest_dir, 'incoming', distname))
            directories.append(osp.join(dest_dir, 'dists', distname))

        for directory in directories:
            self.logger.info('creation of %s', directory)
            try:
                sht.mkdir(directory, self.group, 02775) # set gid on directories 
            except OSError, exc:
                self.logger.debug(exc)

        if osp.isfile(aptconf) or osp.isfile(ldiconf):
            self.logger.error("The repository '%s' already exists" % repo_name)
            self.logger.info("You can edit the aptfile %s to add new sections"
                             % aptconf)
        else:
            if self.options.source_repositories:
                if not self.options.packages:
                    message = 'No packages to extract from the source repositories'
                    raise CommandError(message)
            if self.options.packages:
                if not self.options.source_repositories:
                    message = 'No source repositories for package extraction'
                    raise CommandError(message)

            from debinstall import ldiconffile
            self.logger.info('writing ldiconf to %s', ldiconf)
            ldiconffile.writeconf(ldiconf, self.group, 0664,
                                  distnames,
                                  self.options.source_repositories,
                                  self.options.packages)

            if self.options.aptconffile is not None:
                self.logger.info('copying %s to %s',
                                 self.options.aptconffile, aptconf)
                sht.copy(self.options.aptconffile, aptconf, self.group, 0755)
            else:
                from debinstall import aptconffile
                self.logger.info('writing default aptconf to %s', aptconf)
                aptconffile.writeconf(aptconf, self.group, 0664, distnames[0], origin)
                for distname in distnames:
                    aptconffile.writeconf(aptconf, self.group, 0664, distname, origin, 1)
                self.logger.info('An aptconf file %s has been created.' % aptconf)

class Upload(LdiCommand):
    """upload a new package to the incoming queue of a repository"""
    name = "upload"
    min_args = 2
    max_args = sys.maxint
    arguments = "repository package.changes [...]"
    opt_specs = [ ('-r', '--remove',
                   {'dest': 'remove',
                    'action': "store_true",
                    'default': False,
                    'help': 'remove debian changes file when uploading',
                   }),
                ]

    def _get_all_package_files(self, changes_file):
        file_list = []
        self.logger.info('preparing upload of %s', changes_file)
        all_files = Changes(changes_file).get_all_files()
        for candidate in all_files:
            try:
                fdesc = open(candidate)
                fdesc.close()
            except IOError, exc:
                raise CommandError('Cannot read %s from %s: %s' % \
                                   (candidate, changes_file, exc))
        file_list += all_files
        return file_list

    def _check_signature(self, changes_file):
        """return True if the changes files and appropriate dsc files
        are correctly signed.

        raise CommandError otherwise.
        """
        if self.get_config_value('check_signature').lower() in ('no', 'false'):
            self.logger.info("Signature checks skipped")
            return True

        failed = []
        try:
            Changes(changes_file).check_sig(failed)
        except (Exception,), exc:
            raise CommandError('%s is not a changes file [%s]' % (filename, exc))

        if failed:
            raise CommandError('The following files are not signed:\n' + \
                               '\n'.join(failed))
        return True

    def process(self):
        repository = self.args[0]
        for filename in self.args[1:]:
            distrib = Changes(filename).changes['Distribution']
            destdir = osp.join(self.get_config_value('destination'),
                               repository, 'incoming', distrib)
            self.logger.info('uploading packages to %s for distribution %s',
                             destdir, distrib)
            if not osp.isdir(destdir):
                raise CommandError("The repository '%s' is not fully created. \n"
                                   "Use `ldi list` to get the list of "
                                   "available repositories." % destdir)
            self._check_signature(filename)
            all_files = self._get_all_package_files(filename)
            if self.options.remove:
                shellutil = sht.move
            else:
                shellutil = sht.copy
            for filename in all_files:
                shellutil(filename, destdir, self.group, 0775)

class Publish(Upload):
    """process the incoming queue of a repository"""
    name = "publish"
    min_args = 1
    max_args = sys.maxint
    arguments = "repository [package.changes...]"
    opt_specs = []

    def _get_incoming_changes(self):
        repository = self.args[0]
        changes = []
        for changes_file in self.args[1:]:
            for filename in glob.glob(osp.join('incoming', '**', changes_file)):
                distrib = Changes(filename).changes['Distribution']
                incoming = osp.join(self.get_config_value('destination'),
                                    self.args[0], 'incoming', distrib)
                if not osp.isdir(incoming):
                    raise CommandError("The repository '%s' is not fully created. \n"
                                       "Use `ldi list` to get the list of "
                                       "available repositories." % incoming)
                if osp.isabs(filename):
                    raise CommandError('%s is not a relative path' % filename)
                elif not osp.isfile(filename):
                    msg = "%s is not available in %s %s's incoming queue" % \
                          (filename, distrib, self.args[0])
                    raise CommandError(msg)
                elif not filename.endswith('.changes'):
                    raise CommandError('%s is not a changes file' % filename)
                else:
                    changes.append(osp.join(incoming, distrib, filename))
        else:
            changes = glob.glob(osp.join('incoming', '**', '*.changes'))
        return changes

    def _run_checkers(self, changes_file):
        checkers = self.get_config_value('checkers').split()
        failed = []
        try:
            Changes(changes_file).run_checkers(checkers, failed)
        except (Exception,), exc:
            raise CommandError('%s is not a changes file [%s]'
                               % (changes_file, exc))
        if failed:
            raise CommandError('The following packaging errors were found:\n' +\
                               '\n'.join(failed))

    def process(self):
        repository = self.args[0]
        workdir = osp.join(self.get_config_value('destination'),
                           repository)
        cwd = os.getcwd()
        os.chdir(workdir)

        try:
            changes_files = self._get_incoming_changes()
            for filename in changes_files:
                distrib = Changes(filename).changes['Distribution']
                destdir = osp.join(self.get_config_value('destination'),
                                   repository, 'dists', distrib)
                self.logger.info('publishing packages to %s', destdir)
                self._check_signature(filename)
                self._run_checkers(filename)

                all_files = self._get_all_package_files(filename)
                for one_file in all_files:
                    sht.move(one_file, destdir, self.group, 0664)

                conf_base_dir = self.get_config_value('configurations')
                aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repository)
                apt_ftparchive.clean(destdir)
                # FIXME ajouter la section 'distrib'
                self.logger.info('Running apt-ftparchive generate')
                apt_ftparchive.generate(destdir, aptconf, self.group)
                self.logger.info('Running apt-ftparchive release')
                apt_ftparchive.release(destdir, aptconf, self.group)
                self._sign_repo(destdir)

        finally:
            os.chdir(cwd)

    def _sign_repo(self, repository):
        if self.get_config_value("sign_repo").lower() in ('no', 'false'):
            return
        self.logger.info('Signing release')
        apt_ftparchive.sign(repository,
                            self.get_config_value('keyid'),
                            self.group)


class Configure(LdiCommand):
    """install the program by creating the correct directories with
    the associated permissions"""
    name = "configure"
    min_args = 0
    max_args = 0
    arguments = ""

    def process(self):
        directories = [self.get_config_value(confkey)
                       for confkey in ('destination',
                                       'configurations',
                                       'archivedir')]
        try:
            for dirname in directories:
                sht.mkdir(dirname, self.group, 0775)
        except OSError:
            raise CommandError('Unable to create the directories %s with the '
                               'correct permissions.\n'
                               'Please fix this or edit %s'  % (directories,
                                                       self.options.configfile))
        self.logger.info('Configuration successful')


class List(LdiCommand):
    """list all repositories and their distributions"""
    name = "list"
    min_args = 0
    max_args = sys.maxint
    arguments = "[repository...]"

    def process(self):
        if self.args:
            repositories = self.args[:]
        else:
            repositories = self.get_repo_list()
        for repository in repositories:
            print repository, ':', os.listdir(osp.join(repository, "incoming"))

    def get_repo_list(self):
        dest_dir, conf_dir = [self.get_config_value(confkey)
                              for confkey in ('destination', 'configurations',)]
        repositories = []
        for dirname in os.listdir(dest_dir):
            config = osp.join(conf_dir, '%s-%s.conf')
            for conf in ('apt', 'ldi'):
                conf_file = config % (dirname, conf)
                if not osp.isfile(conf_file):
                    self.logger.debug('cound not find %s', conf_file)
                    break
            else:
                repositories.append(dirname)
        return repositories


## class Archive(LdiCommand):
##     """cleanup a repository by moving old unused packages to an
##     archive directory"""
##     name = "archive"

    

## class Destroy(LdiCommand):
##     """completely remove a repository, its packages and the
##     configuration files"""
##     name = 'destroy'

if __name__ == '__main__':
    run()
