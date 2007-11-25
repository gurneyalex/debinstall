import subprocess as sp
import os
import sys
import os.path as osp
import shutil

from logilab.common.testlib import TestCase

TESTDIR = osp.abspath(osp.dirname(__file__))

DEBUG = True

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

[upload]
check_signature=%(check_signature)s
run_lintian=%(run_lintian)s
run_linda=%(run_linda)s

[publish]
signrepo=%(signrepo)s
keyid=%(keyid)s
check_signature=%(check_signature)s
run_lintian=%(run_lintian)s
run_linda=%(run_linda)s

[archive]
archivedir=%(archivedir)s
'''

def write_config(filename, **substitutions):
    defaults={'destination': osp.join(TESTDIR, 'data', 'acceptance', 'repositories'),
              'configurations': osp.join(TESTDIR, 'data', 'acceptance', 'configurations'),
              'run_lintian': 'no',
              'run_linda': 'no',
              'signrepo': 'no',
              'keyid': 'FFFFFFFF',
              'check_signature': 'no',
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
    

class LdiCreate_TC(TestCase, CommandLineTester):
    def setUp(self):
        self.tearDown()
        
    def tearDown(self):
        dirname = osp.join(TESTDIR, 'data', 'acceptance')
        if osp.exists(dirname):
            shutil.rmtree(dirname)
        cleanup_config('debinstallrc_acceptance')
            
    def test_normal_creation(self):
        config = write_config('debinstallrc_acceptance')
        command = ['ldi', 'create', '-c', config, 'my_repo']
        status, output, error = self.run_command(command)
        self.assertEquals(status, 0, error)
        base_dir = osp.join(TESTDIR, 'data', 'acceptance')
        self.failUnless(osp.isdir(osp.join(base_dir, 'repositories', 'my_repo')))



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
        
