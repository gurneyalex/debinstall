import subprocess as sp
import os
import sys
import os.path as osp
import shutil

from logilab.common.testlib import TestCase

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

[create]
destination=%(destination)s
configurations=%(configurations)s
default_distribution=sid

[upload]
check_signature=%(check_signature)s
checkers=%(run_lintian)s %(run_linda)s

[publish]
sign_repo=%(signrepo)s
keyid=%(keyid)s
check_signature=%(check_signature)s
checkers=%(run_lintian)s %(run_linda)s

[archive]
archivedir=%(archivedir)s
'''

def write_config(filename, **substitutions):
    defaults={'destination': osp.join(TESTDIR, 'data', 'acceptance', 'repositories'),
              'configurations': osp.join(TESTDIR, 'data', 'acceptance', 'configurations'),
              'run_lintian': '',
              'run_linda': '',
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
        self.run_command(command)
        
    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')


    def test_publish_normal(self):
        command = ['ldi', 'publish', '-c', self.config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEqual(status, 0, error)
        

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
        incoming = osp.join(repodir, 'incoming')
        uploaded = os.listdir(incoming)
        expected = ['package1_1.0-1_all.deb',
                    'package1_1.0-1.diff.gz',
                    'package1_1.0-1.dsc',
                    'package1_1.0-1_i386.changes',
                    'package1_1.0.orig.tar.gz',
                    ]
        self.assertSetEqual(uploaded, expected)

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
        incoming = osp.join(repodir, 'incoming')
        uploaded = os.listdir(incoming)
        expected = ['package1_1.0-1_all.deb',
                    'package1_1.0-1.diff.gz',
                    'package1_1.0-1.dsc',
                    'package1_1.0-1_i386.changes',
                    'package1_1.0.orig.tar.gz',
                    ]
        self.assertSetEqual(uploaded, expected)

    def test_upload_wrong_md5(self):
        self.skip('unwritten test')

    def test_upload_lintian_error(self):
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
        status, output, error = self.run_command(command)
        self.assertEquals(status, 0, error)
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')

        repodir = osp.join(base_dir, 'repositories', 'my_repo')
        debian = osp.join(repodir, 'debian')
        sid = osp.join(debian, 'sid')
        incoming = osp.join(repodir, 'incoming')
        self.failUnless(osp.isdir(repodir), 'repo dir not created')
        self.failUnless(osp.isdir(debian), 'debian dir not created')
        self.failUnless(osp.isdir(sid), 'debian/sid dir not created')
        self.failUnless(osp.isdir(incoming), 'incoming dir not created')
        aptconf = osp.join(base_dir, 'configurations', 'my_repo-apt.conf')
        self.failUnless(osp.isfile(aptconf), 'apt.conf file not created')
        ldiconf = osp.join(base_dir, 'configurations', 'my_repo-ldi.conf')
        self.failUnless(osp.isfile(ldiconf), 'ldi.conf file not created')
        f = open(ldiconf)
        config = f.read()
        f.close()
        expected = '''\
[DEFAULT]
distribution=sid

[subrepository]
sources=
packages=
'''
        self.assertEquals(config, expected, 'incorrect ldi.conf written')

        
    def test_no_double_creation(self):
        command = ['ldi', 'create', '-c', self.config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEquals(status, 0, error)
        status, output, error = self.run_command(command)
        self.failIfEqual(status, 0)


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
[DEFAULT]
distribution=sid

[subrepository]
sources=repo1, repo2
packages=package1, package2
'''
        self.assertEquals(config, expected, 'incorrect ldi.conf written')


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
        
