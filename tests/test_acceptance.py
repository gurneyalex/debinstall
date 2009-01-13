import subprocess as sp
import os
import sys
import os.path as osp
import shutil

from logilab.common.testlib import TestCase, unittest_main

TESTDIR = osp.abspath(osp.dirname(__file__))

DEBUG = False

def setup():
    ldi_dir = osp.normpath(osp.join(TESTDIR, '..', 'bin'))
    os.environ['PATH'] = ldi_dir + os.pathsep + os.environ['PATH']

    data_dir = osp.join(TESTDIR, 'data')
    if not osp.isdir(data_dir):
        os.mkdir(data_dir)

setup()

class CommandLineTester:
    def run_command(self, command):
        pipe = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE)
        status = pipe.wait()
        output = pipe.stdout.read()
        error = pipe.stderr.read()
        if DEBUG:
            sys.stdout.write(output)
            sys.stdout.flush()
            sys.stderr.write(error)
            sys.stderr.flush()
        return status, output, error


CONFIG = '''\
[debinstall]
group=devel
umask=0002
origin=Logilab S.A.

[create]
destination=%(destination)s
configurations=%(configurations)s
default_distribution=unstable

[upload]
check_signature=%(check_signature)s
checkers=%(run_lintian)s

[publish]
sign_repo=%(signrepo)s
keyid=%(keyid)s
check_signature=%(check_signature)s
checkers=%(run_lintian)s

[archive]
archivedir=%(archivedir)s
'''

def _check_countrepo(self, count):
    self.assertEquals(len(os.listdir(osp.join(TESTDIR, 'data', 'acceptance', 'repositories'))),
                      count, "bad number of repository")

def _check_repo(self, command, distnames):
    status, output, error = self.run_command(command)
    self.assertEquals(status, 0, error)
    base_dir = osp.join(TESTDIR, 'data', 'acceptance')
    repo = command[-1]
    repodir = osp.join(base_dir, 'repositories', repo)
    self.failUnless(osp.isdir(repodir), 'repo dir not created')

    dists = osp.join(repodir, 'dists')
    self.failUnless(osp.isdir(dists), 'dists dir not created')
    incoming = osp.join(repodir, 'incoming')
    self.failUnless(osp.isdir(incoming), 'incoming dir not created')
    for name in distnames:
        for base in (dists, incoming):
            directory = osp.join(base, name)
            self.failUnless(osp.isdir(directory), '%s dir not created'%directory)

    aptconf = osp.join(base_dir, 'configurations', '%s-apt.conf' % repo)
    self.failUnless(osp.isfile(aptconf), 'apt.conf file not created')
    ldiconf = osp.join(base_dir, 'configurations', '%s-ldi.conf' % repo)
    self.failUnless(osp.isfile(ldiconf), 'ldi.conf file not created')
    f = open(ldiconf)
    config = f.read()
    f.close()
    expected = '''\
[subrepository]
sources=
packages=
'''
    self.assertEquals(config, expected, 'incorrect ldi.conf written:\n'+config)
    # FIXME : test apt-ftparchive conf file

def _check_norepo(self, command):
    status, output, error = self.run_command(command)
    self.assertEquals(status, 0, error)
    base_dir = osp.join(TESTDIR, 'data', 'acceptance')
    repo = command[-1]
    repodir = osp.join(base_dir, 'repositories', repo)
    self.assertFalse(osp.isdir(repodir), 'repo dir still exists')
    aptconf = osp.join(base_dir, 'configurations', '%s-apt.conf' % repo)
    self.assertFalse(osp.isfile(aptconf), 'apt.conf file not created')
    ldiconf = osp.join(base_dir, 'configurations', '%s-ldi.conf' % repo)
    self.assertFalse(osp.isfile(ldiconf), 'ldi.conf file not created')

def write_config(filename, **substitutions):
    defaults={'destination': osp.join(TESTDIR, 'data', 'acceptance', 'repositories'),
              'configurations': osp.join(TESTDIR, 'data', 'acceptance', 'configurations'),
              'run_lintian': '',
              'signrepo': 'no',
              'keyid': 'FFFFFFFF',
              'check_signature': 'yes',
              'archivedir': osp.join(TESTDIR, 'data', 'acceptance', 'archives'),
              }
    filename = osp.join(TESTDIR, 'data', filename)
    if osp.isfile(filename):
        raise ValueError('config file %r already exists' % filename)
    defaults.update(substitutions)
    f = open(filename, 'w')
    f.write(CONFIG % defaults)
    f.close()
    return filename

def cleanup_config(filename):
    filename = osp.join(TESTDIR, 'data', filename)
    if osp.isfile(filename):
        os.remove(filename)

class LdiPublish_TC(TestCase, CommandLineTester):
    def setUp(self):
        self.tearDown()

        self.config = write_config('debinstallrc_acceptance')
        command = ['ldi', 'configure', '-c', self.config]
        status, output, error = self.run_command(command)
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        self.run_command(command)
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        command = ['ldi', 'upload', '-c', self.config, 'my_repo', changesfile]
        status, output, error = self.run_command(command)

    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')

    def test_aptconfigfile(self):
        aptconfigfile = osp.join(TESTDIR, 'data', 'acceptance', 'configurations',
                           'my_repo-apt.conf')
        command = ['apt-config', 'dump', '-c', aptconfigfile]
        status, output, error = self.run_command(command)
        self.assertEqual(status, 0, error)

    def test_publish_normal(self):
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')
        repodir = osp.join(base_dir, 'repositories', 'my_repo')
        command = ['ldi', 'publish', '-c', self.config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEqual(status, 0, error)
        expected_generated = set(['Release', 'Packages', 'Packages.gz', 'Packages.bz2',
                              'Sources', 'Sources.gz', 'Sources.bz2',
                              'Contents', 'Contents.gz', 'Contents.bz2', ])
        expected_published = set(['package1_1.0-1_all.deb',
                                  'package1_1.0-1.diff.gz',
                                  'package1_1.0-1.dsc',
                                  'package1_1.0-1_i386.changes',
                                  'package1_1.0.orig.tar.gz',
                                  ])
        unstable = osp.join(repodir, 'dists', 'unstable')
        generated = set(os.listdir(unstable))

        self.failUnless(expected_generated.issubset(generated))
        self.assertSetEqual(generated, expected_published | expected_generated)

class LdiUpload_TC(TestCase, CommandLineTester):
    def setUp(self):
        self.tearDown()

        self.config = write_config('debinstallrc_acceptance')
        command = ['ldi', 'configure', '-c', self.config]
        status, output, error = self.run_command(command)
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        self.run_command(command)

    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')


    def test_upload_normal_changes(self):
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        command = ['ldi', 'upload', '-c', self.config, 'my_repo', changesfile]
        status, output, error = self.run_command(command)
        self.assertEqual(status, 0, error)
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')
        repodir = osp.join(base_dir, 'repositories', 'my_repo')
        incoming = osp.join(repodir, 'incoming', 'unstable')
        uploaded = os.listdir(incoming)
        expected = ['package1_1.0-1_all.deb',
                    'package1_1.0-1.diff.gz',
                    'package1_1.0-1.dsc',
                    'package1_1.0-1_i386.changes',
                    'package1_1.0.orig.tar.gz',
                    ]
        self.assertUnorderedIterableEquals(uploaded, expected)

    def test_upload_unsigned_changes(self):
        changesfile = osp.join(TESTDIR, 'packages', 'unsigned_package', 'package1_1.0-1_i386.changes')
        command = ['ldi', 'upload', '-c', self.config, 'my_repo', changesfile]
        status, output, error = self.run_command(command)
        self.assertEqual(status, 1, error)

    def test_upload_unsigned_changes_no_sigcheck(self):
        os.unlink(self.config)
        self.config = write_config('debinstallrc_acceptance', check_signature='no')
        changesfile = osp.join(TESTDIR, 'packages', 'unsigned_package', 'package1_1.0-1_i386.changes')
        command = ['ldi', 'upload', '-c', self.config, 'my_repo', changesfile]
        status, output, error = self.run_command(command)
        self.assertEqual(status, 0, error)
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')
        repodir = osp.join(base_dir, 'repositories', 'my_repo')
        incoming = osp.join(repodir, 'incoming', 'unstable')
        uploaded = os.listdir(incoming)
        expected = ['package1_1.0-1_all.deb',
                    'package1_1.0-1.diff.gz',
                    'package1_1.0-1.dsc',
                    'package1_1.0-1_i386.changes',
                    'package1_1.0.orig.tar.gz',
                    ]
        self.assertUnorderedIterableEquals(uploaded, expected)

    def test_upload_wrong_md5(self):
        self.skip('unwritten test')


class LdiCreate_TC(TestCase, CommandLineTester):
    def setUp(self):
        self.tearDown()
        self.config = write_config('debinstallrc_acceptance')
        command = ['ldi', 'configure', '-c', self.config]
        status, output, error = self.run_command(command)

    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')

    def test_normal_creation(self):
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        _check_repo(self, command, ['unstable'])

    def test_multiple_dash_d_options(self):
        command = ['ldi', 'create', '-c', self.config, '-d', 'unstable', '-d', 'testing', '-d', 'stable', 'my_repo']
        _check_repo(self, command, ['unstable', 'testing', 'stable'])

    def test_comma_separated_dash_d(self):
        command = ['ldi', 'create', '-c', self.config, '-d', 'unstable', '-d', 'testing,stable', 'my_repo']
        _check_repo(self, command, ['unstable', 'testing', 'stable'])


    def test_no_double_creation(self):
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEquals(status, 0, error)

    def test_subrepo_creation(self):
        command = ['ldi', 'create', '-c', self.config, '-s', 'repo1', '-s', 'repo2', '-p', 'package1', '-p', 'package2', 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEquals(status, 0, error)
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')
        ldiconf = osp.join(base_dir, 'configurations', 'my_repo-ldi.conf')
        f = open(ldiconf)
        config = f.read()
        f.close()
        expected = '''\
[subrepository]
sources=repo1, repo2
packages=package1, package2
'''
        self.assertEquals(config, expected, 'incorrect ldi.conf written:\n'+config)


    def test_source_without_package(self):
        command = ['ldi', 'create', '-c', self.config, '-s', 'repo1', 'my_repo']
        status, output, error = self.run_command(command)
        self.failIfEqual(status, 0)
        
    def test_package_without_source(self):
        command = ['ldi', 'create', '-c', self.config, '-p', 'package1', 'my_repo']
        status, output, error = self.run_command(command)
        self.failIfEqual(status, 0)
        
class TestFramework_TC(TestCase, CommandLineTester):
    """tests for the helper functions of this test module."""
    def setUp(self):
        self.configname = 'test_____config___%d' % os.getpid()

    def tearDown(self):
        if osp.exists(self.configname):
            os.remove(self.configname)
        
    def test_path(self):
        firstpath = os.environ['PATH'].split(os.pathsep)[0]
        self.failUnless(osp.isfile(osp.join(firstpath, 'ldi')))

    def test_data(self):
        self.failUnless(osp.isdir(osp.join(TESTDIR, "data")))

    def test_write_config(self):
        write_config(self.configname)
        self.failUnless(osp.isfile(osp.join(TESTDIR, 'data', self.configname)))
        self.assertRaises(ValueError, write_config, self.configname)
        cleanup_config(self.configname)
        self.failIf(osp.isfile(osp.join(TESTDIR, 'data', self.configname)))

    def test_run_command(self):
        status, output, error = self.run_command(['ls', TESTDIR])
        self.assertEquals(status, 0)
        self.failIf(error)
        files = os.listdir(TESTDIR)
        output = output.splitlines(False)
        self.assertSetEqual(set(output), set(files))


class LdiDestroy_TC(TestCase, CommandLineTester):
    def setUp(self):
        self.tearDown()
        self.config = write_config('debinstallrc_acceptance')
        command = ['ldi', 'configure', '-c', self.config]
        status, output, error = self.run_command(command)

    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')

    def test_normal_destruction(self):
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        _check_repo(self, command, ['unstable'])
        _check_countrepo(self, 1)
        command = ['ldi', 'destroy', '-c', self.config, 'my_repo']
        _check_norepo(self, command)
        _check_countrepo(self, 0)

    def test_multiple_destruction(self):
        _check_countrepo(self, 0)
        command = ['ldi', 'create', '-c', self.config, '-d', 'unstable', '-d', 'testing', '-d', 'stable', 'my_repo1']
        _check_repo(self, command, ['unstable', 'testing', 'stable'])
        _check_countrepo(self, 1)
        command = ['ldi', 'create', '-c', self.config, '-d', 'unstable', '-d', 'testing', '-d', 'stable', 'my_repo2']
        _check_repo(self, command, ['unstable', 'stable'])
        _check_countrepo(self, 2)
        command = ['ldi', 'destroy', '-c', self.config, 'my_repo2']
        _check_norepo(self, command)
        _check_countrepo(self, 1)
        command = ['ldi', 'destroy', '-c', self.config, 'my_repo1']
        _check_norepo(self, command)
        _check_countrepo(self, 0)

    def test_no_destruction(self):
        command = ['ldi', 'destroy', '-c', self.config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEquals(status, 1, error)


class TestFramework_TC(TestCase, CommandLineTester):
    """tests for the helper functions of this test module."""
    def setUp(self):
        self.configname = 'test_____config___%d' % os.getpid()

    def tearDown(self):
        if osp.exists(self.configname):
            os.remove(self.configname)
        
    def test_path(self):
        firstpath = os.environ['PATH'].split(os.pathsep)[0]
        self.failUnless(osp.isfile(osp.join(firstpath, 'ldi')))

    def test_data(self):
        self.failUnless(osp.isdir(osp.join(TESTDIR, "data")))

    def test_write_config(self):
        write_config(self.configname)
        self.failUnless(osp.isfile(osp.join(TESTDIR, 'data', self.configname)))
        self.assertRaises(ValueError, write_config, self.configname)
        cleanup_config(self.configname)
        self.failIf(osp.isfile(osp.join(TESTDIR, 'data', self.configname)))

    def test_run_command(self):
        status, output, error = self.run_command(['ls', TESTDIR])
        self.assertEquals(status, 0)
        self.failIf(error)
        files = os.listdir(TESTDIR)
        output = output.splitlines(False)
        self.assertSetEqual(set(output), set(files))


if __name__ == '__main__':
    unittest_main()
