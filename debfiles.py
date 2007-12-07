"""helper classes to manipulate debian packages"""
import os.path as osp

from debian_bundle import deb822

from debinstall2.signature import check_sig

class Changes:
    def __init__(self, filename):
        self.filename = filename
        self.changes = deb822.Changes(open(filename))
        self.dirname = osp.dirname(filename)

    def get_dsc(self):
        """return the full path to the dsc file in the changes file
        or None if there is no source included in the upload"""
        for info in self.changes['Files']:
            if info['name'].endswith('.dsc'):
                return osp.join(self.dirname, info['name'])
        return None

    def get_all_files(self):
        all_files = [self.filename]
        for info in self.changes['Files']:
            all_files.append(osp.join(self.dirname, info['name']))
        return all_files

    def check_sig(self, out_wrong=None):
        """check the gpg signature of the changes file and the dsc file (if it exists)

        return: True if all checked sigs are correct, False otherwise.
        out_wrong can be a list, in which case the full paths to the
        wrong signatures files are appended.
        """
        status = True
        if out_wrong is None:
            out_wrong = []
        if not check_sig(self.filename):
            status = False
            out_wrong.append(self.filename)
        dsc = self.get_dsc()
        if dsc is not None and not check_sig(dsc):
            status = False
            out_wrong.append(dsc)
        return status
