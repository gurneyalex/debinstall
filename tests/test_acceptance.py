import sys
import os, os.path as osp
import shutil
import logging
from glob import glob
import subprocess

from logilab.common.testlib import TestCase, unittest_main

from debinstall.ldi import LDI

TESTDIR = osp.abspath(osp.dirname(__file__))
REPODIR = osp.join(TESTDIR, 'data', 'my_repo')
DEBUG = False

class LdiLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self.msgs = {}
    def emit(self, record):
        self.msgs.setdefault(record.levelname, []).append(record.getMessage())
HANDLER = LdiLogHandler()

def setUpModule(*args):
    os.environ['GNUPGHOME'] = osp.join(TESTDIR, 'gnupg')
    data_dir = osp.join(TESTDIR, 'data')
    if not osp.isdir(data_dir):
        os.mkdir(data_dir)
    status = run_command('create', '-d', 'testing,stable,unstable', REPODIR)[-1]
    assert status == 0, HANDLER.msgs

def tearDownModule(*args):
    if osp.exists(REPODIR):
        shutil.rmtree(REPODIR)

def run_command(cmd, *commandargs):
    cmd = LDI.get_command(cmd, logger=LDI.create_logger(HANDLER))
    return cmd, cmd.main_run(list(commandargs), rcfile=None)

def _tearDown(self):
    for f in glob(osp.join(REPODIR, '*', '*', '*')):
        os.unlink(f)


class LdiCreateTC(TestCase):
    tearDown = _tearDown

    def assertDirectoryExists(self, dir):
        self.assertTrue(osp.isdir(dir), '%s not created' % dir)

    def test_normal_creation(self):
        self.assertDirectoryExists(REPODIR)
        for sub in ('dists', 'incoming', 'archive'):
            dists = osp.join(REPODIR, sub)
            self.assertDirectoryExists(dists)
            for dist in ['testing', 'stable', 'unstable']:
                self.assertDirectoryExists(osp.join(dists, dist))


class LdiUploadTC(TestCase):
    tearDown = _tearDown

    def test_upload_normal_changes(self):
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        cmd, status = run_command('upload', REPODIR, changesfile)
        self.assertEqual(status, 0, HANDLER.msgs)
        incoming = osp.join(REPODIR, 'incoming', 'unstable')
        uploaded = os.listdir(incoming)
        expected = ['package1_1.0-1_all.deb',
                    'package1_1.0-1.diff.gz',
                    'package1_1.0-1.dsc',
                    'package1_1.0-1_i386.changes',
                    'package1_1.0.orig.tar.gz',
                    ]
        self.assertCountEqual(uploaded, expected)
        self.assertEqual(cmd.debian_changes,
                          {'unstable': [osp.join(REPODIR, 'incoming/unstable/package1_1.0-1_i386.changes')]})

    def test_upload_unsigned_changes(self):
        changesfile = osp.join(TESTDIR, 'packages', 'unsigned_package', 'package1_1.0-1_i386.changes')
        cmd, status = run_command('upload', REPODIR, changesfile)
        self.assertEqual(status, 2, HANDLER.msgs)
        self.assertEqual(cmd.debian_changes, {})


class LdiPublishTC(TestCase):
    def setUp(self):
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        cmd, status = run_command('upload', REPODIR, changesfile)
        assert status == 0, HANDLER.msgs
    tearDown = _tearDown

    def test_publish_normal(self):
        cmd, status = run_command('publish', '--no-confirm', REPODIR)
        self.assertEqual(status, 0, HANDLER.msgs)
        self.assertEqual(cmd.debian_changes,
                          {'unstable': [osp.join(REPODIR, 'dists/unstable/package1_1.0-1_i386.changes')]})
        expected_generated = set(['Release', 'Packages', 'Packages.gz', 'Packages.bz2',
                              'Sources', 'Sources.gz', 'Sources.bz2',
                              'Contents', 'Contents.gz', 'Contents.bz2', ])
        expected_published = set(['package1_1.0-1_all.deb',
                                  'package1_1.0-1.diff.gz',
                                  'package1_1.0-1.dsc',
                                  'package1_1.0-1_i386.changes',
                                  'package1_1.0.orig.tar.gz',
                                  ])
        unstable = osp.join(REPODIR, 'dists', 'unstable')
        generated = set(os.listdir(unstable))
        self.assertTrue(expected_generated.issubset(generated))
        self.assertSetEqual(generated, expected_published | expected_generated)
        with open(os.devnull, 'w') as null:
            cmd = subprocess.Popen(['apt-config', 'dump', '-c', osp.join(REPODIR, 'apt.conf')],
                                   stdout=null, stderr=subprocess.PIPE)
        _, err = cmd.communicate()
        self.assertEqual(cmd.returncode, 0, err)


if __name__ == '__main__':
    unittest_main()
