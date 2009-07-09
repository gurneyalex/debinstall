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
import os.path as osp
import glob
import subprocess

from logilab.common import optparser
from logilab.common.shellutils import acquire_lock, release_lock

from debinstall.debfiles import Changes
from debinstall.command import LdiCommand, CommandError
from debinstall import shelltools as sht
from debinstall import apt_ftparchive
from debinstall import aptconffile
from debinstall.__pkginfo__ import version

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
        ('-d', '--distribution',
         {'dest': 'distribution',
          'help': 'the name of the distribution in the repository',
          'action': 'append',
          'default': [],
          }
         ),
        ]

    def process(self):
        repository = self.args[0]

        confdir = self.get_config_value('configurations')
        destdir = self.get_config_value("destination")
        repodir = osp.join(destdir, repository)
        aptconf = osp.join(confdir, '%s-apt.conf' % repository)
        ldiconf = osp.join(confdir, '%s-ldi.conf' % repository)
        distribs = self.options.distribution or \
                    [self.get_config_value("default_distribution"),]

        # creation of the repository
        directories = [repodir]
        for distname in distribs:
            directories.append(osp.join(repodir, 'incoming', distname))
            directories.append(osp.join(repodir, 'dists', distname))
            self.logger.info("new section '%s' will be added in repository '%s'"
                             % (distname, repository))

        for directory in directories:
            try:
                sht.mkdir(directory, self.group, 02775) # set gid on directories
            except OSError, exc:
                self.logger.debug(exc)

        # write configuration files
        info = {}
        info['origin'] = self.get_config_value("origin") or '(Unknown)'
        from debinstall import ldiconffile
        ldiconffile.writeconf(ldiconf, self.group, 0664, distribs)
        self.logger.info("a new ldifile '%s' was created" % ldiconf)
        aptconffile.writeconf(confdir, destdir, repository, self.group, 0664, info)
        self.logger.info("a new aptfile '%s' was created" % aptconf)


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
                self.logger.error('the changes file is not properly signed: %s' % changes_file)
                self.logger.error(failed)
                subprocess.Popen(['gpg', '--verify', changes_file]).communicate()
                raise CommandError("check if the PGP block exists and if the key is in your keyring")

    def _check_repository(self, repository, section="incoming", distrib=None):
        '''check repository and returns its real path or raise CommandError'''
        destdir = osp.join(self.get_config_value('destination'), repository, section)
        if distrib:
            destdir = osp.join(destdir, distrib)
        destdir = osp.realpath(destdir)

        if not osp.isdir(destdir):
            if distrib:
                raise CommandError("distribution '%s' not found. Use ldi list to "\
                                   "check" % distrib)
            raise CommandError("section '%s' in repository '%s' not found. Use ldi list to check"
                               % (section, repository))

        # Print a warning in case of using symbolic distribution names
        dereferenced = osp.basename(destdir)
        if distrib and  dereferenced != distrib:
            self.logger.warn("deferences symlinked distribution '%s' to '%s' "
                             % (distrib, dereferenced))
        return destdir

    def _check_changes_file(self, changes_file):
        """basic tests to determine debian changes file"""
        if not (osp.isfile(changes_file) and changes_file.endswith('.changes')):
            raise CommandError('%s is not a Debian changes file' % changes_file)

    def _print_changes_files(self, repository, section, distribution=None):
        """print information about a repository and inside changes files"""
        path = self._check_repository(repository, section, distribution)
        for root, dirs, files in os.walk(path):
            if distribution:
                line = StringIO.StringIO()
                # Only consider pointed distribution (not symbolic)
                if osp.basename(root) == osp.basename(path):
                    line.write("%s changes files in %s:\n" % (section.title(), root))
                    for f in sorted(files):
                        if f.endswith(".changes"):
                            line.write(str(root.split('/')[4:7]) + " %s\n" % f)
                    if len(files) == 0:
                        line.write(str(root.split('/')[4:7]) + ' (no changes file found)')
                    self.logger.info(line.getvalue())
            # Print section content
            elif dirs and not files:
                line = StringIO.StringIO()
                line.write("Available %s section(s) in %s:\n" % (section.title(), root))
                for d in dirs:
                    line.write(str(root.split('/')[4:7]) + " %s" % d)
                    if osp.islink(osp.join(root, d)):
                        line.write(' (@ --> %s)' % os.readlink(osp.join(root, d)))
                    line.write('\n')
                self.logger.info(line.getvalue())

    def process(self):
        repository = self.args[0]
        for filename in self.args[1:]:
            self._check_changes_file(filename)
            if self.options.distribution:
                distrib = self.options.distribution
            else:
                distrib = Changes(filename).changes['Distribution']
            destdir = self._check_repository(repository, "incoming", distrib)
            self._check_signature(filename)

            if self.options.remove:
                shellutil = sht.move
            else:
                shellutil = sht.copy
            for filename in all_files:
                shellutil(filename, destdir, self.group, 0775)
        self._print_changes_files(repository, 'incoming', distrib)

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

    def _run_checkers(self, changes_file):
        checkers = self.get_config_value('checkers').split()
        failed = []
        try:
            Changes(changes_file).run_checkers(checkers, failed)
        except Exception, exc:
            raise CommandError('%s is not a changes file [%s]'
                               % (changes_file, exc))
        if failed:
            raise CommandError('the following packaging errors were found:\n' +\
                               '\n'.join(failed))

    def process(self):
        distribs = set()
        repository = self.args[0]

        conf_base_dir = self.get_config_value('configurations')
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repository)
        distsdir = osp.join(self.get_config_value('destination'),
                            repository, 'dists')

        # we have to launch the publication sequentially
        acquire_lock(LOCK_FILE, max_try=3, delay=5)
        try:
            changes_files = self._get_incoming_changes(repository)
            if len(changes_files)==0:
                self.logger.info('no package to publish.')
            for filename in changes_files:
                # distribution name is the same as the incoming directory name
                # it lets permit to override a valid suite by a more private
                # one (for example: contrib, volatile, experimental, ...)
                distrib = osp.basename(osp.dirname(filename))
                destdir = self._check_repository(repository, "dists", distrib)
                self._check_signature(filename)
                self._run_checkers(filename)

                all_files = self._get_all_package_files(filename)
                for one_file in all_files:
                    sht.move(one_file, destdir, self.group, 0664)

                # mark distribution to be refreshed at the end
                distribs.add(distrib)

            if self.options.refresh:
                self.logger.info('force refreshing whole repository %s...' % repository)
                self._apt_refresh(repodir, aptconf)
            elif distribs:
                for distrib in distribs:
                    self.logger.info('refreshing distribution %s in repository %s...'
                                     % (distrib, repository))
                    self._apt_refresh(distsdir, aptconf, distrib)

        finally:
            release_lock(LOCK_FILE)

    def _sign_repo(self, repository):
        if self.get_config_value("sign_repo").lower() in ('no', 'false'):
            return
        self.logger.info('signing release')
        apt_ftparchive.sign(repository,
                            self.get_config_value('keyid'),
                            self.group)

    def _apt_refresh(self, distsdir, aptconf, distrib="*"):
        for destdir in glob.glob(osp.join(distsdir, distrib)):
            if osp.isdir(destdir) and not osp.islink(destdir):
                self.logger.info('generate index files in %s' % destdir)
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
            raise CommandError('unable to create the directories %s with the '
                               'correct permissions.\n'
                               'Please fix this or edit %s'  % (directories,
                                                       self.options.configfile))
        self.logger.info('Configuration successful')


class List(Upload):
    """list all repositories and their distributions"""
    name = "list"
    min_args = 0
    max_args = sys.maxint
    arguments = "[repositories...] [-d|--distribution]"
    opt_specs = [
                 ('-d', '--distribution',
                   {'dest': 'distribution',
                    'help': 'list a specific target distribution',
                   }),
                 ('-i', '--incoming',
                   {'dest': 'only_incoming',
                    'action': "store_true",
                    'default': False,
                    'help': 'list only incoming section (not dists)',
                   }),
                ]

    def process(self):
        detectedrepos = self.get_repo_list()
        if not self.args:
            repositories = detectedrepos
        for repository in self.args:
            self._print_changes_files(repository, 'incoming', self.options.distribution)
            if not self.options.only_incoming:
                self._print_changes_files(repository, 'dists', self.options.distribution)

    def get_repo_list(self):
        """return list of repository and do some checks"""
        dest_dir = self.get_config_value('destination')
        conf_dir = self.get_config_value('configurations')

        repositories = []
        for dirname in os.listdir(dest_dir):
            # Some administrators like to keep configuration files
            # in the same directory that the whole repositories
            if os.path.realpath(os.path.join(dest_dir, dirname)) == os.path.realpath(conf_dir):
                self.logger.debug('skipping debinstall configuration directory %s', conf_dir)
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
