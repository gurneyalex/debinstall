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

from logilab.common import optparser, shellutils as sht

from debinstall.debfiles import Changes
from debinstall.command import LdiCommand, CommandError
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
        # comma separated distribs are accepted here
        distribs = self.options.distribution or \
                   [self.get_config_value('default_distribution')]
        distribs, = [re.split(r'[^\w]+', r) for r in distribs]

        # creation of the repository
        directories = [repodir]
        for distname in distribs:
            directories.append(osp.join(repodir, 'incoming', distname))
            directories.append(osp.join(repodir, 'dists', distname))
            self.logger.info("new section '%s' will be added in repository '%s'"
                             % (distname, repository))

        for directory in directories:
            try:
                os.makedirs(directory)
                sht.chown(directory, group=self.group)
                os.chmod(destdir, 02775)
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
        if changes_file.endswith('.changes') and osp.isfile(changes_file):
            return True
        raise CommandError('%s is not a Debian changes file' % changes_file)

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
        repository = self.args[0]
        for filename in self.args[1:]:
            self._check_changes_file(filename)
            if self.options.distribution:
                distrib = self.options.distribution
            else:
                distrib = Changes(filename).changes['Distribution']
            destdir = self._check_repository(repository, "incoming", distrib)
            self._check_signature(filename)
            self._run_checkers(filename)

            if self.options.remove:
                shellutil = sht.mv
            else:
                shellutil = sht.cp
            self.perform_changes_file(filename, destdir, shellutil)

    def perform_changes_file(self, changes_file, destdir, shellutil=sht.cp):
        self.logger.info("%sing of '%s'..." % (self.__class__.__name__, changes_file))
        arguments = Changes(changes_file).get_all_files()
        pristine_included = [f for f in arguments if f.endswith('.orig.tar.gz')]
        distrib = osp.basename(destdir)
        section = osp.basename(osp.dirname(destdir))
        repository = osp.basename(osp.dirname(osp.dirname(destdir)))

        # Logilab uses trivial Debian repository and put all generated files in
        # the same place. Badly, it occurs some problems in case of several 
        # supported architectures and multiple Debian revision (in this order)
        if shellutil != sht.cp:
            # In case of multi-arch in same directory, we need to check if parts og
            # changes files are not required by another changes files
            mask = "%s*.changes" % changes_file.rsplit('_',1)[0]
            result = glob.glob(osp.join(destdir, mask))
            # if another file is matched by mask, we must not erase the parts
            if result:
                self.logger.warn('changes file parts are blocked by mask: %s' % mask)
                import pprint
                self.logger.debug(pprint.pformat(all_files))
                return

        for filename in all_files:
            self.logger.debug("[%s] '%s' (%s)" % (shellutil.__name__,
                                                  filename,
                                                  osp.basename(destdir)))
            if osp.exists(destdir):
                shellutil(filename, destdir)
                filename = osp.join(destdir, osp.basename(filename))
                sht.chown(filename, group=self.group)
                os.chmod(filename, 0664)
            else: # sht.rm
                shellutil(filename)
        self.logger.info("%sed in '%s' section of the '%s' distribution."
                         % (self.__class__.__name__, section, distrib))

    def _find_changes_files(self, repository, section, distrib=None):
        changes = []
        path = self._check_repository(repository, section)
        for root, dirs, files in os.walk(path):
            if distrib:
                distrib = osp.basename(osp.realpath(osp.join(root, distrib)))
            for d in dirs[:]:
                if osp.islink(osp.join(root, d)):
                    dirs.remove(d)
                elif distrib and d != distrib:
                    dirs.remove(d)
            for f in files:
                if f.endswith('.changes') and self._filter_by_arguments(f):
                    changes.append(osp.join(root, f))
        return sorted(changes)

    def _filter_by_arguments(self, changes):
        '''if changes files are given in command line, only keep them'''
        if self.args[1:]:
            for f in self.args[1:]:
                return osp.basename(changes) in [osp.basename(f) for f
                                                 in self.args[1:]]
        return True


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

    def process(self):
        distribs = set()
        repository = self.args[0]

        confdir = self.get_config_value('configurations')
        distdir = self.get_config_value("destination")
        repodir = osp.join(distdir, repository)
        aptconf = osp.join(confdir, '%s-apt.conf' % repository)
        ldiconf = osp.join(confdir, '%s-ldi.conf' % repository)

        os.chdir(repodir)

        # we have to launch the publication sequentially
        sht.acquire_lock(LOCK_FILE, max_try=3, delay=5)
        try:
            changes_files = self._find_changes_files(repository, "incoming")

            if not changes_files:
                self.logger.info("no changes file to publish in repository '%s'" % repository)

            for filename in changes_files:
                # distribution name is the same as the incoming directory name
                # it lets permit to override a valid suite by a more private
                # one (for example: contrib, volatile, experimental, ...)
                distrib = osp.basename(osp.dirname(filename))
                destdir = self._check_repository(repository, "dists", distrib)
                self._check_signature(filename)
                self._run_checkers(filename)

                self.perform_changes_file(filename, destdir, sht.mv)

                # mark distribution to be refreshed at the end
                distribs.add(distrib)

            if self.options.refresh:
                self.logger.info('force refreshing whole repository %s...' % repository)
                self._apt_refresh(repodir, aptconf)
            elif distribs:
                for distrib in distribs:
                    self.logger.info('refreshing distribution %s in repository %s...'
                                     % (distrib, repository))
                    self._apt_refresh(repodir, aptconf, distrib)

        finally:
            sht.release_lock(LOCK_FILE)

    def _sign_repo(self, repository):
        if self.get_config_value("sign_repo").lower() in ('no', 'false'):
            return
        self.logger.info('signing release')
        apt_ftparchive.sign(repository,
                            self.get_config_value('keyid'),
                            self.group)

    def _apt_refresh(self, repodir, aptconf, distrib="*"):
        for destdir in glob.glob(osp.join(repodir, 'dists', distrib)):
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
        for dirname in directories:
            try:
                os.mkdir(dirname)
            except OSError:
                self.logger.warn("directory '%s' already exists" % dirname)
            try:
                os.chmod(dirname, 0775)
            except OSError:
                self.logger.critical('unable to change permissions on %s' % dirname)
                raise CommandError('please fix this or edit %s'
                                   % self.options.configfile)
        self.logger.info('configuration successful')

class List(Upload):
    """list all repositories and their distributions"""
    name = "list"
    min_args = 0
    max_args = sys.maxint
    arguments = "[repository [-d | --distribution] [package.changes ...]]"
    opt_specs = [
                 ('-d', '--distribution',
                   {'dest': 'distribution',
                    'help': 'list a specific target distribution',
                   }),
                 ('-s', '--section',
                   {'dest': 'section',
                    'help': "directory that contains the dist nodes ('incoming' or 'dists')",
                    'default': 'incoming'
                   }),
                ]

    def process(self):
        if not self.args:
            destdir = self.get_config_value('destination')
            repositories = self.get_repo_list()
            self.logger.info("%s available repositories in %s"
                             % (len(repositories), destdir))
            print [repository for repository in repositories]
        elif len(self.args)==1 and not self.options.distribution:
            repository = self.args[0]
            path = self._check_repository(repository, self.options.section)
            lines = []
            for root, dirs, files in os.walk(path):
                if dirs:
                    for d in dirs:
                        line = str(root.split('/')[5:7] + [d,])
                        if osp.islink(osp.join(root, d)):
                            line += ' (symlinked to %s)' % os.readlink(osp.join(root, d))
                        else:
                            nb = len(glob.glob(osp.join(root, d, "*.changes")))
                            if nb:
                                line += " contains %d changes files" % nb
                            else:
                                line += " is empty"
                        lines.append(line)
            self.logger.info("%s available %s section(s) in %s"
                             % (len(lines), self.options.section, root))
            for line in lines: print line
        else:
            repository = self.args[0]
            self._print_changes_files(repository, self.options.section,
                                      self.options.distribution)

    def _print_changes_files(self, repository, section, distribution=None):
        """print information about a repository and inside changes files"""
        filenames = self._find_changes_files(repository, section, distribution)
        filenames = [filename.rsplit('/', 4)[1:] for filename in filenames]

        if not filenames:
            self.logger.warn("no changes file was found in repository '%s'" % repository)

        for f in filenames:
            print f

    def get_repo_list(self):
        """return list of repository and do some checks"""
        destdir = self.get_config_value('destination')
        confdir = self.get_config_value('configurations')

        repositories = []
        for dirname in os.listdir(destdir):
            # Some administrators like to keep configuration files
            # in the same directory that the whole repositories
            if os.path.realpath(os.path.join(destdir, dirname)) == os.path.realpath(confdir):
                self.logger.debug('skipping debinstall configuration directory %s', confdir)
                continue
            config = osp.join(confdir, '%s-%s.conf')
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
    arguments = "repository [-d | --distribution] [package.changes ...]"
    opt_specs = [
                 ('-s', '--section',
                   {'dest': 'section',
                    'help': "directory that contains the dist nodes ('incoming' or 'dists')",
                    'default': 'incoming'
                   }),
                 ('-d', '--distribution',
                   {'dest': 'distribution',
                    'help': 'force a specific target distribution',
                   }),
                ]

    def process(self):
        repository = self.args[0]
        self._check_repository(repository)

        confdir = self.get_config_value('configurations')
        distdir = self.get_config_value("destination")
        repodir = osp.join(distdir, repository)
        aptconf = osp.join(confdir, '%s-apt.conf' % repository)
        ldiconf = osp.join(confdir, '%s-ldi.conf' % repository)

        os.chdir(repodir)

        # Manage deletion of changes files given by command line
        if self.args[1:]:
            filenames = self._find_changes_files(repository, self.options.section,
                                                 self.options.distribution)
            if not filenames:
                self.logger.warn("no changes file was deleted in repository '%s'" % repository)

            for filename in filenames:
                self.perform_changes_file(filename, "", sht.rm)
        else:
            try:
                self.logger.warn("you're asking for a large deletion of data...")
                import time
                time.sleep(1)
                confirm = raw_input("Do you want to continue (type: Yes, I do) ? ")
            except KeyboardInterrupt:
                sys.exit(1)

            if confirm != 'Yes, I do':
                self.logger.info('Aborting.')
                sys.exit()

            for section in ['incoming', 'dists']:
                destdir = self._check_repository(repository, section, self.options.distribution)
                sht.rm(destdir)

            # Erase all repository config by default
            confdir = self.get_config_value('configurations')
            destdir = self.get_config_value('destination')
            repodir = osp.join(destdir, repository)
            aptconf = osp.join(confdir, '%s-apt.conf' % repository)
            ldiconf = osp.join(confdir, '%s-ldi.conf' % repository)

            if self.options.distribution is None:
                sht.rm([aptconf, ldiconf, repodir])
                self.logger.info("repository '%s' was deleted" % repository)
            else:
                info = {}
                info['origin'] = self.get_config_value("origin") or '(Unknown)'

                # only one distribution was deleted because _check_repository()
                # returned an unique distribution path
                self.logger.info("distribution '%s' was removed in repository '%s'"
                                 % (self.options.distribution, repository))
                # write configuration
                aptconffile.writeconf(confdir, destdir, repository, self.group, 0664, info)
                self.logger.info("aptfile '%s' was modified" % aptconf)


## class Archive(LdiCommand):
##     """cleanup a repository by moving old unused packages to an
##     archive directory"""
##     name = "archive"


if __name__ == '__main__':
    run()
