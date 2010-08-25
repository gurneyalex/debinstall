import sys
import os, os.path as osp
import shutil
import logging

from logilab.common.testlib import TestCase, unittest_main
from logilab.common.shellutils import Execute

from debinstall import ldi

TESTDIR = osp.abspath(osp.dirname(__file__))
REPODIR = osp.join(TESTDIR, 'data', 'my_repo')
DEBUG = False

def setup_module(args):
    data_dir = osp.join(TESTDIR, 'data')
    if not osp.isdir(data_dir):
        os.mkdir(data_dir)

def run_command(cmd, *commandargs):
    return ldi.LDI.run_command(cmd, list(commandargs))

def _tearDown(self):
    if osp.exists(REPODIR):
        shutil.rmtree(REPODIR)



class LdiLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        logging.Handler.__init__(self, *args, **kwargs)
        self.msgs = {}
    def emit(self, record):
        self.msgs.setdefault(record.levelname, []).append(record.getMessage())

ldi.LDI.init_log(handler=LdiLogHandler())
ldi.rcfile = None


class LdiCreateTC(TestCase):
    tearDown = _tearDown

    def test_normal_creation(self):
        command = ['ldi', 'create', '-d', 'testing,stable', REPODIR]
        status = run_command('create', '-d', 'testing,stable', REPODIR)
        self.assertEquals(status, 0)
        self.failUnless(osp.isdir(REPODIR), 'repo dir %s not created' % REPODIR)
        for sub in ('dists', 'incoming'):
            dists = osp.join(REPODIR, sub)
            self.failUnless(osp.isdir(dists), '%s dir not created' % sub)
            for dist in ['testing', 'stable']:
                directory = osp.join(dists, dist)
                self.failUnless(osp.isdir(directory),
                                '%s/%s dir not created' % (sub, dist))
        #aptconf = osp.join(repodir, 'apt.conf')
        #self.failUnless(osp.isfile(aptconf), '%s file not created' % aptconf)


class LdiUploadTC(TestCase):
    def setUp(self):
        run_command('create', '-d', 'unstable', REPODIR)
    tearDown = _tearDown

    def test_upload_normal_changes(self):
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        status = run_command('upload', REPODIR, changesfile)
        self.assertEqual(status, 0)
        incoming = osp.join(REPODIR, 'incoming', 'unstable')
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
        status = run_command('upload', REPODIR, changesfile)
        self.assertEqual(status, 2)


class LdiPublishTC(TestCase):
    def setUp(self):
        run_command('create', '-d', 'unstable', REPODIR)
        changesfile = osp.join(TESTDIR, 'packages', 'signed_package', 'package1_1.0-1_i386.changes')
        run_command('upload', REPODIR, changesfile)
    tearDown = _tearDown

    def test_publish_normal(self):
        status = run_command('publish', REPODIR)
        self.assertEqual(status, 0)
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
        self.failUnless(expected_generated.issubset(generated))
        self.assertSetEqual(generated, expected_published | expected_generated)
        output = Execute('apt-config dump -c %s' % osp.join(REPODIR, 'apt.conf'))
        self.assertEqual(output.status, 0, output.err)


if __name__ == '__main__':
    unittest_main()
