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
import subprocess

from logilab.common import optparser
from logilab.common.shellutils import acquire_lock, release_lock

from debinstall.debfiles import Changes
from debinstall.command import LdiCommand, CommandError
from debinstall import shelltools as sht
from debinstall import apt_ftparchive
from debinstall.__pkginfo__ import version
from debinstall import aptconffile

LOCK_FILE='/var/lock/debinstall'

def run(args=None):
    if sys.argv[0] == "-c": # launched by binary script using python -c
        sys.argv[0] = "ldi"
        debug = False
    else:
        debug = True
    os.umask(0002)
    if args is None:
        args = sys.argv[1:]
    usage = """usage: %prog <command> <options> [arguments]"""
    usage+= "\n    or %prog <command> --help for more information about a specific command."
    parser = optparser.OptionParser(usage=usage,
                                    version='debinstall %s' % version)
    for cmd in (Create,
                Upload,
                Publish,
                List,
                #Archive,
                Destroy,
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
        try:
            origin = self.get_config_value("origin")
        except CommandError, exc:
            self.logger.warning("%s", exc)
            self.logger.warning("A default value has been written in your debinstallrc")
            origin = "(Unknown)"

        dest_base_dir = self.get_config_value("destination")
        conf_base_dir = self.get_config_value('configurations')
        raw_distnames = self.options.distribution or \
                   [self.get_config_value('default_distribution')]
        distnames = []
        for name in raw_distnames:
            distnames += re.split(r'[^\w]+', name)
        repo_name = self.args[0]
        dest_dir = osp.join(dest_base_dir, repo_name)
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repo_name)
        ldiconf = osp.join(conf_base_dir, '%s-ldi.conf' % repo_name)

        if osp.isfile(aptconf) or osp.isfile(ldiconf):
            self.logger.warning("The repository '%s' already exists" % repo_name)
            aptconffile.writeconf(aptconf, self.group, 0664, distnames, origin)
            self.logger.info("New distribution %s was added in the aptconf file %s"
                             % (','.join(distnames), aptconf))
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
            self.logger.debug('writing ldiconf to %s', ldiconf)
            ldiconffile.writeconf(ldiconf, self.group, 0664,
                                  distnames,
                                  self.options.source_repositories,
                                  self.options.packages)

            if self.options.aptconffile is not None:
                self.logger.debug('copying %s to %s',
                                  self.options.aptconffile, aptconf)
                sht.copy(self.options.aptconffile, aptconf, self.group, 0755)
            else:
                self.logger.debug('writing default aptconf to %s', aptconf)
                aptconffile.writeconf(aptconf, self.group, 0664, distnames, origin)
                self.logger.info('An aptconf file %s has been created.' % aptconf)

        directories = [dest_dir]
        for distname in distnames:
            directories.append(osp.join(dest_dir, 'incoming', distname))
            directories.append(osp.join(dest_dir, 'dists', distname))

        for directory in directories:
            try:
                sht.mkdir(directory, self.group, 02775) # set gid on directories 
            except OSError, exc:
                self.logger.debug(exc)

class Upload(LdiCommand):
    """upload a new package to the incoming queue of a repository"""
    name = "upload"
    min_args = 2
    max_args = sys.maxint
    arguments = "repository [-r | --remove] [-d | --distribution] package.changes [...]"
    opt_specs = [('-r', '--remove',
                   {'dest': 'remove',
                    'action': "store_true",
                    'default': False,
                    'help': 'remove debian changes file',
                   }),
                 ('-d', '--distribution',
                   {'dest': 'distribution',
                    'help': 'force a specific target distribution',
                   }),
                ]

    def _get_all_package_files(self, changes_file):
        file_list = []
        self.logger.debug('%sing of %s...' % (self.__class__.__name__, changes_file))
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
        """raise CommandError if the changes files and appropriate dsc files
        are not correctly signed
        """
        if self.get_config_value('check_signature').lower() in ('yes', 'true'):
            failed = []
            try:
                Changes(changes_file).check_sig(failed)
            except Exception, exc:
                raise CommandError('%s is not a debian changes file [%s]' % (changes_file, exc))

            if failed:
                self.logger.error('The changes file is not properly signed: %s' % changes_file)
                subprocess.Popen(['gpg', '--verify', changes_file]).communicate()
                raise CommandError("Check if the PGP block exists and if the key is in your keyring")

    def _check_repository(self, destdir):
        if not (osp.isdir(destdir) or osp.islink(destdir)):
            raise CommandError("The repository '%s' is not fully created. \n" \
                               "Use `ldi list` to get the list of " \
                               "available repositories." % destdir)

    def _check_changes_file(self, changes_file):
        """basic tests to determine debian changes file"""
        if not (osp.isfile(changes_file) and changes_file.endswith('.changes')):
            raise CommandError('%s is not a Debian changes file' % changes_file)

    def process(self):
        repository = self.args[0]
        for filename in self.args[1:]:
            self._check_changes_file(filename)
            if self.options.distribution:
                distrib = self.options.distribution
            else:
                distrib = Changes(filename).changes['Distribution']
            destdir = osp.join(self.get_config_value('destination'),
                               repository, 'incoming', distrib)
            self.logger.info('%sing "%s" to %s for %s distribution',
                             self.__class__.__name__, osp.basename(filename),
                             destdir, distrib)
            self._check_repository(destdir)
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
    arguments = "repository [-r | --refresh] [package.changes...]"
    opt_specs = [('-r', '--refresh',
                   {'dest': 'refresh',
                    'action': "store_true",
                    'default': False,
                    'help': 'refresh the whole repository index files'
                   }),
                ]

    def _get_incoming_changes(self, workdir):
        changes = []
        incoming = osp.join(workdir, 'incoming')
        for root, dirs, files in os.walk(incoming):
            for d in dirs:
                if os.path.islink(osp.join(root, d)):
                    dirs.remove(d)
            for f in files:
                if f.endswith('.changes'):
                    changes.append(osp.join(root, f))
        self.logger.debug("get incoming changes: %s" % changes)
        changes = self._filter_incoming_changes(changes)
        self.logger.debug("filtered incoming changes: %s" % changes)
        return changes

    def _filter_incoming_changes(self, changes):
        if self.args[1:]:
            changes2 = []
            for f in self.args[1:]:
                self.logger.debug("filter incoming changes: %s" % f)
                f = osp.abspath(f)
                self.logger.debug("filter incoming changes: %s" % f)
                path = osp.dirname(f)
                self.logger.debug("filter incoming changes: %s (%s)" % (f,path))
                if os.path.islink(path):
                    path = osp.join(os.path.dirname(path), os.readlink(path))
                self.logger.debug("filter incoming changes: %s (%s)" % (f,path))
                f = os.path.join(path, osp.basename(f))
                self.logger.debug("filter incoming changes: %s" % f)
                self._check_changes_file(f)
                if f in changes:
                    changes2.append(f)
                    self.logger.debug("queue new changes file: %s" % changes2)
            changes = changes2
        return changes

    def _run_checkers(self, changes_file):
        checkers = self.get_config_value('checkers').split()
        failed = []
        try:
            Changes(changes_file).run_checkers(checkers, failed)
        except Exception, exc:
            raise CommandError('%s is not a changes file [%s]'
                               % (changes_file, exc))
        if failed:
            raise CommandError('The following packaging errors were found:\n' +\
                               '\n'.join(failed))

    def process(self):
        distribs = set()
        repository = self.args[0]
        workdir = osp.join(self.get_config_value('destination'), repository)

        # change to repository directory level to have relative pathnames from
        # here (restore current directory in finally statement)
        cwd = os.getcwd()
        try:
            os.chdir(workdir)
        except Exception:
            self.logger.fatal('no valid repository. Use ldi list to check.')
            sys.exit(1)

        conf_base_dir = self.get_config_value('configurations')
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repository)
        distsdir = osp.join(self.get_config_value('destination'),
                            repository, 'dists')

        # we have to launch the publication sequentially
        acquire_lock(LOCK_FILE, max_try=3, delay=5)
        try:
            changes_files = self._get_incoming_changes(workdir)
            if len(changes_files)==0:
                self.logger.info('No package to publish.')
            for filename in changes_files:
                # distribution name is the same as the incoming directory name
                # it lets permit to override a valid suite by a more private
                # one (for example: contrib, volatile, experimental, ...)
                distrib = osp.basename(osp.dirname(filename))
                destdir = osp.join(distsdir, distrib)
                self._check_repository(destdir)
                self._check_signature(filename)
                self._run_checkers(filename)

                all_files = self._get_all_package_files(filename)
                for one_file in all_files:
                    sht.move(one_file, destdir, self.group, 0664)

                # mark distribution to be refreshed at the end
                distribs.add(distrib)

            if self.options.refresh:
                self.logger.info('Force refreshing whole repository %s...' % repository)
                self._apt_refresh(distsdir, aptconf)
            elif distribs:
                for distrib in distribs:
                    self.logger.info('Refreshing distribution %s in repository %s...'
                                     % (distrib, repository))
                    self._apt_refresh(distsdir, aptconf, distrib)

        finally:
            release_lock(LOCK_FILE)
            os.chdir(cwd)

    def _sign_repo(self, repository):
        if self.get_config_value("sign_repo").lower() in ('no', 'false'):
            return
        self.logger.info('Signing release')
        apt_ftparchive.sign(repository,
                            self.get_config_value('keyid'),
                            self.group)

    def _apt_refresh(self, distsdir, aptconf, distrib="*"):
        for destdir in glob.glob(osp.join(distsdir, distrib)):
            if osp.isdir(destdir) and not osp.islink(destdir):
                apt_ftparchive.clean(destdir)
                apt_ftparchive.generate(destdir, aptconf, self.group)
                apt_ftparchive.release(destdir, aptconf, self.group,
                                       osp.basename(destdir))
                self._sign_repo(destdir)

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

def walkinto(path, distribution):
    """usefull function to print informations about a repository"""
    for root, dirs, files in os.walk(path):
        if distribution:
            if osp.basename(root) == distribution:
                for f in sorted(files):
                    if f.endswith(".changes"):
                        print root.split('/')[4:7], f
                if len(files) == 0:
                    print root.split('/')[4:7], '(empty directory)'
        else:
            for d in dirs:
                print root.split('/')[4:7], d,
                if osp.islink(osp.join(root, d)):
                    print '(@ --> %s)' % os.readlink(osp.join(root, d)),
                print

class List(Upload):
    """list all repositories and their distributions"""
    name = "list"
    min_args = 0
    max_args = sys.maxint
    arguments = "[repository...]"

    def process(self):
        detectedrepos = self.get_repo_list()
        repositories = [x for x in self.args if x in detectedrepos]
        if not self.args:
            repositories = detectedrepos
        for repository in repositories:
            repository = osp.join(self.get_config_value("destination"), repository)
            walkinto(os.path.join(repository, 'incoming'), self.options.distribution)
            walkinto(os.path.join(repository, 'dists'), self.options.distribution)

    def get_repo_list(self):
        """return list of repository and do some checks"""
        dest_dir = self.get_config_value('destination')
        conf_dir = self.get_config_value('configurations')
        
        repositories = []
        for dirname in os.listdir(dest_dir):
            if os.path.realpath(os.path.join(dest_dir, dirname)) == os.path.realpath(conf_dir):
                self.logger.info('skipping config directory %s', conf_dir)
                continue
            config = osp.join(conf_dir, '%s-%s.conf')
            for conf in ('apt', 'ldi'):
                conf_file = config % (dirname, conf)
                if not osp.isfile(conf_file):
                    self.logger.error('could not find %s', conf_file)
                    break
            else:
                repositories.append(dirname)
        return repositories


class Destroy(List):
    """remove a specified repository and the relative configuration files"""
    name = "destroy"
    min_args = 1
    max_args = sys.maxint
    arguments = "[repository...]"

    def process(self):
        detectedrepos = self.get_repo_list()
        for repository in self.args[:]:
            if repository in detectedrepos:
                dest_dir, conf_dir = [self.get_config_value(confkey)
                                      for confkey in ('destination', 'configurations',)]
                sht.rm(osp.join(conf_dir, "%s-apt.conf" % repository))
                sht.rm(osp.join(conf_dir, "%s-ldi.conf" % repository))
                sht.rm(osp.join(dest_dir, repository))
            else:
                self.logger.fatal('repository %s doesn\'t exist', repository)
                sys.exit(1)


## class Archive(LdiCommand):
##     """cleanup a repository by moving old unused packages to an
##     archive directory"""
##     name = "archive"


if __name__ == '__main__':
    run()
