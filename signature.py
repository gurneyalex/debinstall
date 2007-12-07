"""helper module to handle GnuPG signatures"""

from subprocess import Popen, PIPE

def check_sig(filename):
    """return True if the file is correctly signed"""
    pipe = Popen(["gpg", "--verify",  filename], stderr=PIPE)
    pipe.stderr.read()
    status = pipe.wait()
    return status == 0
