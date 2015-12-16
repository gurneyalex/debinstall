# Copyright (c) 2007-2011 LOGILAB S.A. (Paris, FRANCE).
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
"""wrapper functions to run the apt-ftparchive command"""

import os
import os.path as osp
import subprocess
import shutil
from glob import glob

from logilab.common.clcommands import CommandError
from logilab.common.changelog import Version as BaseVersion

from debinstall.debfiles import Changes

def changesfile(package, version, archi, upstreamversion=False):
    if upstreamversion:
        return '%s_%s-*_%s.changes' % (package, version, archi)
    return '%s_%s_%s.changes' % (package, version, archi)

_SEPARATOR = object()

class Version(BaseVersion):
    def __new__(cls, versionstr):
        if isinstance(versionstr, basestring):
            try:
                versionstr, debversion = versionstr.split('-', 1)
            except ValueError:
                debversion = None
            else:
                try:
                    debversion = int(debversion)
                except ValueError:
                    pass
            parsed = cls.parse(versionstr)
            if debversion is not None:
                parsed.append(_SEPARATOR)
                parsed.append(debversion)
        else:
            parsed = versionstr
        return tuple.__new__(cls, parsed)

    @classmethod # remove once lgc > 0.54 is out
    def parse(cls, versionstr):
        versionstr = versionstr.strip(' :')
        try:
            return [int(i) for i in versionstr.split('.')]
        except ValueError, ex:
            raise ValueError("invalid literal for version '%s' (%s)"%(versionstr, ex))

    def __str__(self):
        version = '.'.join(str(num) for num in self.upstream_version)
        debianversion = self.debian_version
        if debianversion is not None:
            return '%s-%s' % (version, debianversion)
        return version

    @property
    def upstream_version(self):
        version = []
        for num in self:
            if num is _SEPARATOR:
                break
            version.append(num)
        return tuple(version)

    @property
    def debian_version(self):
        separator_found = False
        for num in self:
            if separator_found is True:
                return num
            if num is _SEPARATOR:
                separator_found = True
        return None

APTDEFAULT_APTCONF = '''// This header is used to generate the apt.conf file
// you may modify it to configure your repository, eg. you can add headers in
// APT::FTPArchive::Release, etc.
// MODIFY BELOW THIS LINE

APT {
  FTPArchive {
    Release {
        Origin "%(origin)s";
        Label  "%(origin)s debian packages repository";
        Description "created by the ldi utility";
    };
  };
};

Default {
        Packages::Compress ". gzip bzip2";
        Sources::Compress ". gzip bzip2";
        Contents::Compress ". gzip bzip2";
        FileMode 0664;
};

Dir {
        ArchiveDir "%(archivedir)s";
};
'''

BINDIRECTORY_APTCONF = '''\

BinDirectory "%(distribution)s" {
    Packages "%(distribution)s/Packages";
    Sources "%(distribution)s/Sources";
    Contents "%(distribution)s/Contents"
};
'''

class DebianRepository(object):
    def __init__(self, logger, directory):
        self.logger = logger
        self.directory = directory
        self.ldiname = osp.basename(directory.rstrip(os.sep))

    @property
    def aptconf_file(self):
        return osp.join(self.directory, 'apt.conf')

    @property
    def incoming_directory(self):
        return osp.join(self.directory, 'incoming')
    @property
    def dists_directory(self):
        return osp.join(self.directory, 'dists')
    @property
    def archive_directory(self):
        return osp.join(self.directory, 'archive')

    def check_distrib(self, section, distrib):
        distribdir = osp.join(self.directory, section, distrib)
        if not osp.isdir(distribdir):
            os.mkdir(distribdir)
            self.logger.info("created %s", distribdir)
        # Print a warning in case of using symbolic distribution names
        distribdir = osp.realpath(distribdir)
        dereferenced = osp.basename(distribdir)
        if dereferenced != distrib:
            self.logger.warn("deferences symlinked distribution '%s' to '%s'",
                             distrib, dereferenced)
        return distribdir

    def generate_aptconf(self, origin='Logilab'):
        """write a configuration file for use by apt-ftparchive"""
        header_file = self.aptconf_file+".in"
        if not osp.isfile(header_file):
            with open(header_file, "w") as stream:
                stream.write(APTDEFAULT_APTCONF % { 'origin': origin,
                                                    'archivedir': self.dists_directory,
                                                    })
        stream = open(self.aptconf_file, "w")
        stream.write('// Generated by ldi; DO NOT EDIT\n')
        stream.write('// You may edit the apt.conf.in file to customize it\n')
        header = [line.rstrip() for line in open(header_file)]
        marker = "// MODIFY BELOW THIS LINE"
        if marker in header:
            header = header[header.index(marker) + 1:]
        stream.write('\n'.join(header))
        for distrib in glob(osp.join(self.dists_directory, '*')):
            if osp.isdir(distrib) and not osp.islink(distrib):
                distrib = osp.basename(distrib)
                stream.write(BINDIRECTORY_APTCONF % {'distribution': distrib})
        stream.close()

    def dist_publish(self, dist, gpgkeyid=None):
        self.dist_clean(dist)
        self.ftparchive_generate(dist)
        self.ftparchive_release(dist)
        if gpgkeyid:
            self.sign(dist, gpgkeyid)

    def dist_clean(self, dist):
        for mask in ['Packages*', 'Source*', 'Content*', 'Release*']:
            for path in glob(osp.join(self.dists_directory, dist, mask)):
                self.logger.debug('rm %s', path)
                os.remove(path)

    def ftparchive_generate(self, dist):
        command = ['apt-ftparchive', '-q=2', 'generate',
                   self.aptconf_file, dist]
        self.logger.debug(' '.join(command))
        pipe = subprocess.Popen(command)
        status = pipe.wait()
        if status != 0:
            raise CommandError('apt-ftparchive exited with error status %d' % status)

    def ftparchive_release(self, dist):
        distdir = osp.join(self.dists_directory, dist)
        command = ['apt-ftparchive', '-c', self.aptconf_file, 'release',
                   distdir,
                   '-o', 'APT::FTPArchive::Release::Codename=%s' % dist]
        self.logger.debug('running command: %s', ' '.join(command))
        release_file = osp.join(distdir, 'Release')
        release = open(release_file, 'w')
        pipe = subprocess.Popen(command, stdout=release)
        pipe.communicate()
        release.close()
        if pipe.returncode != 0:
            raise CommandError('apt-ftparchive exited with error status %d'
                               % pipe.returncode)

    def sign(self, dist, gpgkeyid):
        releasepath = osp.join(self.dists_directory, dist, 'Release')
        signed_releasepath = releasepath + '.gpg'
        command = ['gpg', '-b', '-a', '--yes', '--default-key', gpgkeyid,
                   '-o', signed_releasepath, releasepath]
        self.logger.debug('running command: %s' % ' '.join(command))
        pipe = subprocess.Popen(command)
        pipe.communicate()
        status = pipe.wait()
        if status != 0:
            raise CommandError('gpg exited with status %d' % status)

    def incoming_changes_files(self, args, distrib=None):
        return self._changes_files(self.incoming_directory, args, distrib)

    def dists_changes_files(self, args, distrib=None):
        return self._changes_files(self.dists_directory, args, distrib)

    def _changes_files(self, path, args, distrib=None):
        changes = []
        if distrib:
            distrib = osp.basename(osp.realpath(osp.join(path, distrib)))
        if args:
            file_match = lambda f: f in args or osp.join(root, f) in args
        else:
            file_match = lambda f: f.endswith('.changes')
        for root, dirs, files in os.walk(path):
            for d in dirs[:]:
                if osp.islink(osp.join(root, d)):
                    dirs.remove(d)
                elif distrib and d != distrib:
                    dirs.remove(d)
            changes += [osp.join(root, f) for f in files if file_match(f)]
        return sorted(changes)

    def iter_changes_files(self, package=None, dists=None):
        if package is None:
            matchstring = '*.changes'
        else:
            matchstring = '%s_*.changes' % package
        for dist in os.listdir(self.dists_directory):
            if dists and not dist in dists:
                self.logger.debug('skip distrib %s', dist)
                continue
            for changes in glob(osp.join(self.dists_directory, dist, matchstring)):
                yield changes

    def iter_packages(self, package=None, dists=None):
        for changesfile in self.iter_changes_files(package, dists):
            package, version, archi = changesfile.split('_')
            dist = osp.basename(osp.dirname(changesfile))
            try:
                yield (dist, archi.replace('.changes', ''),
                       osp.basename(package), Version(version))
            except ValueError:
                self.logger.warning('skip misnamed package %s', changesfile)

    def packages_index(self, package=None, dists=None):
        repo1 = {}
        for dist, archi, package, version in self.iter_packages(package, dists):
            repo1.setdefault(package, {}).setdefault(dist, {}).setdefault(archi, set()).add(version)
        return repo1

    def archive_package(self, dist, package, version, archi):
        self.logger.info('archive %s %s %s %s', dist, package, version, archi)
        distdir = osp.join(self.dists_directory, dist)
        archivedir = osp.join(self.archive_directory, dist)
        changes = osp.join(distdir, changesfile(package, version, archi))
        for bpackage in Changes(changes).get_packages():
            for fpath in glob(osp.join(distdir, '%s_%s_%s*' % (bpackage, version, archi))):
                self.logger.debug('move %s', fpath)
                shutil.move(fpath, osp.join(archivedir, osp.basename(fpath)))
            for fpath in glob(osp.join(distdir, '%s_%s_all*' % (bpackage, version))):
                self.logger.debug('move %s', fpath)
                shutil.move(fpath, osp.join(archivedir, osp.basename(fpath)))
        if glob(osp.join(distdir, changesfile(package, version, '*'))):
            # .dsc, .diff.gz, .orig.tar.gz should be kept for some other
            # architecture
            move = shutil.copy
        else:
            move = shutil.move
        for fpath in (osp.join(distdir, '%s_%s.dsc' % (package, version)),
                      osp.join(distdir, '%s_%s.diff.gz' % (package, version))):
            if osp.exists(fpath):
                self.logger.debug('%s %s', move.__name__, fpath)
                move(fpath, osp.join(archivedir, osp.basename(fpath)))
        upstreamversion = Version(version.upstream_version)
        if glob(osp.join(distdir, changesfile(package, upstreamversion, '*',
                                              upstreamversion=True))):
            # don't remove .orig.tar.gz if there still exists packages for that
            # upstream version
            move = shutil.copy
        fpath  = osp.join(distdir, '%s_%s.orig.tar.gz' % (package, upstreamversion))
        if osp.exists(fpath):
            self.logger.debug('%s %s', move.__name__, fpath)
            move(fpath, osp.join(archivedir, osp.basename(fpath)))

    def reduce_package(self, dist, package, versions, archi):
        versions = sorted(versions)
        lastversion = versions.pop()[:2]
        for version in reversed(versions):
            majorversion = version[:2]
            if lastversion == majorversion:
                self.archive_package(dist, package, version, archi)
            else:
                lastversion = majorversion
