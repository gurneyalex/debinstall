"""common interface to linda and lintian"""

from subprocess import Popen, PIPE

class Checker:
    command = "command"
    options = []
    ok_status = (0, )
    def run(self, changesfile):
        argv = [self.command] + self.options + [changesfile]
        pipe = Popen(argv, stdout=PIPE, stderr=PIPE)
        stdout = pipe.stdout.readlines()
        stderr = pipe.stderr.readlines()
        return pipe.wait in self.ok_status, stdout, stderr

class LintianChecker(Checker):
    command = "lintian"

class LindaChecker(Checker):
    command = "linda"
    error_status = (0, 1,)


ALL_CHECKERS = [LintianChecker(),
                LindaChecker(),
                ]
