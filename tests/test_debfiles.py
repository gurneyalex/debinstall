import os.path as osp

from logilab.common.testlib import TestCase, unittest_main

from debinstall.debfiles import *

TESTDIR = osp.abspath(osp.dirname(__file__))

class Changes_TC(TestCase):
    def setUp(self):
        self.packages_dir = osp.join(TESTDIR,
                                     "packages")
        self.signed = Changes(osp.join(self.packages_dir,
                                       "signed_package",
                                       'package1_1.0-1_i386.changes'))
        self.unsigned = Changes(osp.join(self.packages_dir,
                                       "unsigned_package",
                                       'package1_1.0-1_i386.changes'))
        self.no_source = Changes(osp.join(self.packages_dir,
                                          "signed_no_source",
                                          'package1_1.0-1_i386.changes'))

    def test_get_dsc(self):
        dsc = self.signed.get_dsc()
        self.assertEquals(dsc, osp.join(self.signed.dirname,
                                        "package1_1.0-1.dsc"))

    def test_get_dsc_no_source(self):
        dsc = self.no_source.get_dsc()
        self.assertEquals(dsc, None)

    def test_all_files(self):
        dirname = self.signed.dirname
        signed_files = ['package1_1.0-1_i386.changes',
                        'package1_1.0-1.dsc',
                        'package1_1.0.orig.tar.gz',
                        'package1_1.0-1.diff.gz',
                        'package1_1.0-1_all.deb']
        signed_files = [osp.join(dirname, f) for f in signed_files]
        result = self.signed.get_all_files()
        self.assertUnorderedIterableEquals(signed_files, result)

    def test_check_sig(self):
        wrong_sigs = []
        self.failUnless(self.signed.check_sig(wrong_sigs))
        self.assertListEquals(wrong_sigs, [])

        self.failUnless(self.no_source.check_sig(wrong_sigs))
        self.assertListEquals(wrong_sigs, [])

        self.failIf(self.unsigned.check_sig(wrong_sigs))
        self.assertListEquals(wrong_sigs, [self.unsigned.filename,
                                           self.unsigned.get_dsc()])


if __name__ == '__main__':
    unittest_main()
