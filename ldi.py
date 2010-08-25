# Copyright (c) 2007-2010 LOGILAB S.A. (Paris, FRANCE).
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
"""The ldi command provides access to various subcommands to manipulate debian
packages and repositories
"""

import sys
import os
import os.path as osp
from glob import glob
# from itertools import chain

from logilab.common import clcommands as cli, shellutils as sht

from debinstall.__pkginfo__ import version
from debinstall import debrepo
from debinstall.debfiles import BadSignature, Changes

RCFILE = '/home/syt/etc/debinstallrc'

LDI = cli.CommandLine('ldi', doc='Logilab debian installer', version=version,
                      rcfile=RCFILE)

OPTIONS = [
    ('distributions', # XXX to share with lgp
     {'type': 'csv', 'short': 'd', 'group': 'main',
      'help': 'comma separated list of distributions supported by the repository',
      'default': ['lenny', 'squeeze', 'sid'],
      }),
    ('checkers',
     {'type': 'csv', 'short': 'C', 'group': 'main',
      'help': 'comma separated list of checkers to run before package upload/publish',
      'default': ['lintian'],
      }),
    ('repositories-directory',
     {'type': 'string', 'short': 'R', 'group': 'main',
      'help': 'directory where repositories are stored',
      }),
    ('group',
     {'type': 'string', 'short': 'G', 'group': 'main',
      'help': 'Unix group to which ldi handled files/directories should belong',
      'default': None, #'debinstall',
      }),
    ]


def run():
    os.umask(0002)
    LDI.run(sys.argv[1:])

def _repo_path(config, directory):
    if not osp.isabs(directory):
        if not config.repositories_directory:
            raise cli.CommandError(
                'Give either an absolute path to a directory that should '
                'hold the repository or a repository name and specify its'
                'directory using --repositories-directory')
        directory = osp.join(config.repositories_directory, directory)
    return directory


class Create(cli.Command):
    """create a new repository"""
    name = "create"
    arguments = "<repository path or name>"
    min_args = max_args = 1
    options = OPTIONS

    def run(self, args):
        repodir = _repo_path(self.config, args.pop(0))
        # creation of the repository
        for distname in self.config.distributions:
            for subdir in ('incoming', 'dists', 'archive'):
                distribdir = osp.join(repodir, subdir, distname)
                if not osp.isdir(distribdir):
                    os.makedirs(distribdir)
                    if self.config.group:
                        sht.chown(distribdir, group=self.config.group)
                    os.chmod(distribdir, 02775)
                    self.logger.info('created %s', distribdir)
                else:
                    self.logger.info('%s directory already exists', distribdir)

LDI.register(Create)


class Upload(cli.Command):
    """upload a new package to the incoming queue of a repository"""
    name = "upload"
    min_args = 2
    arguments = "[options] <repository> <package.changes>..."
    options = OPTIONS[1:] + [
        ('remove',
         {'short': 'r', 'action': 'store_true',
          'help': 'remove debian changes file',
          'default': False,
          }),
        ('distribution',
         {'help': 'force a specific target distribution',
          }),
        ]

    def run(self, args):
        repodir = _repo_path(self.config, args.pop(0))
        sectiondir = self._check_repository(repodir, 'incoming')
        for filename in args:
            changes = self._check_changes_file(filename)
            if self.config.distribution:
                distrib = self.config.distribution
            else:
                distrib = changes['Distribution']
            try:
                distribdir = self._check_distrib(sectiondir, distrib)
            except cli.CommandError, ex:
                self.logger.error(ex)
                # drop the current changes file
                continue
            self._check_signature(changes)
            self._run_checkers(changes)
            if self.config.remove:
                move = sht.mv
            else:
                move = sht.cp
            self.perform_changes_file(changes, distribdir, move)

    def _check_repository(self, repodir, section):
        subdir = osp.join(repodir, section)
        if not osp.isdir(osp.join(repodir, 'incoming')):
            raise cli.CommandError(
                "Repository %s doesn't exist or isn't properly initialized (no "
                "'%s' directory)" % (repodir, section))
        return subdir

    def _check_distrib(self, sectiondir, distrib):
        distribdir = osp.join(sectiondir, distrib)
        if not osp.isdir(distribdir):
            raise cli.CommandError(
                "Distribution %s not found in %s" % (distrib, sectiondir))
        # Print a warning in case of using symbolic distribution names
        distribdir = osp.realpath(distribdir)
        dereferenced = osp.basename(distribdir)
        if dereferenced != distrib:
            self.logger.warn("deferences symlinked distribution '%s' to '%s'",
                             distrib, dereferenced)
        return distribdir

    def _check_changes_file(self, changes_file):
        """basic tests to determine debian changes file"""
        if changes_file.endswith('.changes') and osp.isfile(changes_file):
            try:
                return Changes(changes_file)
            except Exception, ex:
                raise cli.CommandError(
                    '%s is not a debian changes file: %s' % (changes_file, ex))
        raise cli.CommandError(
            '%s is not a Debian changes file (bad extension)' % changes_file)

    def _check_signature(self, changes):
        """raise error if the changes files and appropriate dsc files are not
        correctly signed
        """
        try:
            changes.check_sig()
        except BadSignature, ex:
            raise cli.CommandError(
                "%s. Check if the PGP block exists and if the key is in your "
                "keyring" % ex)

    def _run_checkers(self, changes):
        checkers = self.config.checkers
        try:
            changes.run_checkers(checkers)
        except Exception, ex:
            raise cli.CommandError(str(ex))

    def _files_to_keep(self, changes):
        # In case of multi-arch in same directory, we need to check if parts
        # of changes files are not required by another changes files We're
        # excluding the current parsed changes file
        mask = "%s*.changes" % changes.filename.rsplit('_', 1)[0]
        ochanges = glob(osp.join(changes.dirname, mask))
        ochanges.remove(changes.path)
        # Find intersection of files shared by several 'changes'
        allfiles = changes.get_all_files()
        result = allfiles & set([f for c in ochanges
                                 for f in Changes(c).get_all_files()])
        if result:
            self.logger.warn("keep intact changes file's parts "
                             "required by another architecture(s)")
            return result
        pristine = changes.get_pristine()
        if pristine:
            # Another search to preserve pristine tarball in case of multiple
            # revision of the same upstream release
            # We're excluding the current parsed changes file
            mask = "%s*.changes" % changes.filename.rsplit('-', 1)[0]
            ochanges = glob(osp.join(changes.dirname, mask))
            ochanges.remove(changes.path)
            # Check if the detected changes files really needs the tarball
            result = set([r for r in ochanges
                          if Changes(r).get_pristine() == pristine])
            if result:
                self.logger.warn("keep intact original pristine tarball "
                                 "required by another Debian revision(s)")
            return result
        return set()

    def perform_changes_file(self, changes, distribdir, move=sht.cp):
        allfiles = changes.get_all_files()
        # Logilab uses trivial Debian repository and put all generated files in
        # the same place. Badly, it occurs some problems in case of several
        # supported architectures and multiple Debian revision (in this order)
        if move is sht.mv:
            tokeep = self._files_to_keep(changes)
        else:
            tokeep = None
        for filename in allfiles:
            if tokeep and filename in tokeep:
                move_ = sht.cp
            else:
                move_ = move
            destfile = osp.join(distribdir, osp.basename(filename))
            self.logger.debug("%s %s %s", move_.__name__, filename, destfile)
            move_(filename, distribdir)
            if self.config.group:
                sht.chown(destfile, group=self.config.group)
            os.chmod(destfile, 0664)
        if tokeep:
            for filename in tokeep:
                self.logger.debug("rm %s %s", filename)
                sht.rm(filename)

LDI.register(Upload)


class Publish(Upload):
    """process the incoming queue of a repository"""
    name = "publish"
    min_args = 1
    arguments = "<repository> [<package.changes>...]"
    options = OPTIONS[1:] + [
        ('gpg-keyid',
         {'type': 'string', 'group': 'main',
          'help': 'GPG identifier of the key to use to sign the repository',
          }),
        ('refresh',
         {'action': "store_true",
          'help': 'refresh the whole repository index files',
          'default': False,
          }),
        ]

    def run(self, args):
        repodir = _repo_path(self.config, args.pop(0))
        incdir = self._check_repository(repodir, 'incoming')
        distsdir = self._check_repository(repodir, 'dists')
        distribs = set()
        # we have to launch the publication sequentially
        lockfile = osp.join(repodir, 'ldi.lock')
        sht.acquire_lock(lockfile, max_try=3, delay=5)
        try:
            changes_files = self._find_changes_files(incdir, args)
            if not changes_files and not self.config.refresh:
                self.logger.error("no changes file to publish in %s", incdir)
            for filename in changes_files:
                # distribution name is the same as the incoming directory name
                # it lets override a valid suite by a more private one (for
                # example: contrib, volatile, experimental, ...)
                distrib = osp.basename(osp.dirname(filename))
                destdir = self._check_distrib(distsdir, distrib)
                changes = self._check_changes_file(filename)
                self._check_signature(changes)
                self._run_checkers(changes)
                self.perform_changes_file(changes, destdir, sht.mv)
                # mark distribution to be refreshed at the end
                distribs.add(distrib)
            aptconffile = debrepo.generate_aptconf(repodir)
            if self.config.refresh:
                distribs = ('*',)
            for distrib in distribs:
                self._apt_refresh(distsdir, aptconffile, distrib)
        finally:
            sht.release_lock(lockfile)

    def _apt_refresh(self, distsdir, aptconffile, distrib="*"):
        for distdir in glob(osp.join(distsdir, distrib)):
            if osp.isdir(distdir) and not osp.islink(distdir):
                debrepo.clean(distdir)
                debrepo.generate(distdir, aptconffile)
                debrepo.release(distdir, aptconffile)
                if self.config.gpg_keyid:
                    self.logger.info('signing release')
                    debrepo.sign(distdir, self.config.gpg_keyid)
                self.logger.info('%s: index files generated', distdir)

    def _find_changes_files(self, path, args, distrib=None):
        changes = []
        if distrib:
            distrib = osp.basename(osp.realpath(osp.join(path, distrib)))
        for root, dirs, files in os.walk(path):
            for d in dirs[:]:
                if osp.islink(osp.join(root, d)):
                    dirs.remove(d)
                elif distrib and d != distrib:
                    dirs.remove(d)
            for f in files:
                if f.endswith('.changes') and (not args or f in args):
                    changes.append(osp.join(root, f))
        return sorted(changes)

LDI.register(Publish)


# class List(Upload):
#     """list all repositories and their distributions"""
#     name = "list"
#     min_args = 0
#     max_args = sys.maxint
#     arguments = "[repository [-d | --distribution] [package.changes ...]]"
#     opt_specs = [
#                  ('-d', '--distribution',
#                    {'dest': 'distribution',
#                     'help': 'list a specific target distribution',
#                    }),
#                  ('-s', '--section',
#                    {'dest': 'section',
#                     'help': "directory that contains the dist nodes ('incoming' or 'dists')",
#                     'default': 'incoming'
#                    }),
#                  ('-o', '--orphaned',
#                    {'dest': 'orphaned',
#                     'action': "store_true",
#                     'default': False,
#                     'help': 'report orphaned packages or files (can be slow)'
#                    }),
#                 ]

#     def process(self):
#         if not self.args:
#             destdir = self.get_config_value('destination')
#             repositories = self.get_repo_list()
#             self.logger.info("%s available repositories in '%s'"
#                              % (len(repositories), destdir))
#             repositories = sorted([repository for repository in repositories])
#             print(os.linesep.join(repositories))
#             return

#         repository = self.args[0]
#         path = self._check_repository(repository, self.options.section)
#         if len(self.args)==1 and not self.options.distribution:
#             lines = []
#             for root, dirs, files in os.walk(path):
#                 orphaned = list()
#                 if dirs:
#                     for d in dirs:
#                         line = "%s/%s" % (repository, d)
#                         if osp.islink(osp.join(root, d)):
#                             line += ' is symlinked to %s' % os.readlink(osp.join(root, d))
#                         else:
#                             nb = len(glob(osp.join(root, d, "*.changes")))
#                             if nb:
#                                 line += " contains %d changes files" % nb
#                             else:
#                                 line += " is empty"
#                             if self.options.orphaned:
#                                 orphaned = self.get_orphaned_files(path, d)
#                                 if orphaned:
#                                     line += " and %d orphaned files" % len(orphaned)
#                         lines.append(line)
#             self.logger.info("%s: %s available distribution(s) in '%s' section"
#                              % (repository, len(lines), self.options.section))
#             for line in lines: print line
#         else:
#             self._print_changes_files(repository, self.options.section,
#                                       self.options.distribution)
#             if self.options.orphaned:
#                 orphaned = self.get_orphaned_files(path, self.options.distribution)
#                 if orphaned:
#                     self.logger.warn("%s: has %s orphaned file(s)"
#                                      % (repository, len(orphaned)))
#                     print '\n'.join(orphaned)

#         if self.options.section == 'incoming':
#             self.logger.info("use option 'ldi list -s dists %s' to list published content" % repository)

#     def _print_changes_files(self, repository, section, distribution):
#         """print information about a repository and inside changes files"""
#         filenames = self._find_changes_files(repository, section, distribution)

#         if not filenames:
#             self.logger.warn("%s/%s: no changes file found" % (repository,
#                                                                distribution))
#         else:
#             self.logger.info("%s/%s: %s available changes files"
#                              % (repository, distribution, len(filenames)))
#             filenames = [filename.rsplit('/', 4)[1:] for filename in filenames]
#             for f in filenames:
#                 print("%s/%s: %s" % (f[0], f[2], f[-1]))

#     def get_repo_list(self):
#         """return list of repository and do some checks"""
#         destdir = self.get_config_value('destination')
#         confdir = self.get_config_value('configurations')

#         repositories = []
#         for dirname in os.listdir(destdir):
#             # Some administrators like to keep configuration files
#             # in the same directory that the whole repositories
#             if os.path.realpath(os.path.join(destdir, dirname)) == os.path.realpath(confdir):
#                 self.logger.debug('skipping debinstall configuration directory %s', confdir)
#                 continue
#             config = osp.join(confdir, '%s-%s.conf')
#             for conf in ('apt', 'ldi'):
#                 conf_file = config % (dirname, conf)
#                 if not osp.isfile(conf_file):
#                     self.logger.error('could not find %s', conf_file)
#                     break
#             else:
#                 repositories.append(dirname)
#         return repositories

#     def get_orphaned_files(self, repository, distrib):
#         import fnmatch
#         changes_files = (glob(os.path.join(repository, distrib,
#                                                 '*.changes')))
#         tracked_files = (Changes(f).get_all_files(check_if_exists=False)
#                          for f in changes_files if f)
#         tracked_files = set(tuple(chain(*tracked_files)))

#         untracked_files = set([f for f in glob(os.path.join(repository, distrib, '*'))])
#         orphaned_files = untracked_files - tracked_files
#         orphaned_files -= set(fnmatch.filter(orphaned_files, "*/Packages*"))
#         orphaned_files -= set(fnmatch.filter(orphaned_files, "*/Sources*"))
#         orphaned_files -= set(fnmatch.filter(orphaned_files, "*/Contents*"))
#         orphaned_files -= set(fnmatch.filter(orphaned_files, "*/Release*"))
#         return orphaned_files


if __name__ == '__main__':
    run()
