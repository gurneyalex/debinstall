import os, os.path as osp
import logging

from narvalbot.prototype import input, output
from narvalbot.elements import FilePath

from apycotbot import utils, register
from apycotbot.checkers import BaseChecker

from debinstall.ldi import LDI


# narval actions ###############################################################

def _ldi_checker(checker, inputs):
    test = inputs['apycot']
    options = inputs['options'].copy()
    options['changes-file'] = inputs['changes-file']
    return test.run_checker(checker, options)


@input('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True, list=True)
@output('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        list=True)
@utils.apycotaction('ldi.upload')
def act_ldi_upload(inputs):
    checker, status = _ldi_checker('ldi.upload', inputs)
    result = []
    for changesfile in checker.processed.get('changesfiles'):
        path = osp.join(inputs['options'].repository, 'incoming',
                        inputs['changes-file'].distribution,
                        osp.basename(changesfile))
        result.append(FilePath(path=path, type='debian.changes.uploaded'))
    return {'changes-file': result}


@input('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True, list=True)
@output('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        list=True)
@utils.apycotaction('ldi.publish')
def act_ldi_publish(inputs):
    checker, status = _ldi_checker('ldi.publish', inputs)
    result = []
    for changesfile in checker.processed.get('changesfiles', ()):
        path = osp.join(inputs['options'].repository, 'incoming',
                        inputs['changes-file'].distribution,
                        osp.basename(changesfile))
        result.append(FilePath(path=path, type='debian.changes.published'))
    return {'changes-file': result}


# apycot checkers ##############################################################

class LdiLogHandler(logging.Handler):
    def __init__(self, writer):
        logging.Handler.__init__(self)
        self.writer = writer
        self.path = None
        self.status = utils.SUCCESS

    def emit(self, record):
        emitfunc = getattr(self.writer, record.levelname.lower())
        emitfunc(record.getMessage(), path=self.path)
        if record.levelname == 'ERROR':
            self.status = utils.FAILURE


class LdiUploadChecker(BaseChecker):
    """upload debian packages using ldi"""

    id = 'ldi.upload'
    command = 'upload'
    options_def = {
        'repository': {
            'required': True,
            'help': 'ldi repository name',
            },
        'changes-file': {
            'type', 'csv', 'required': True,
            'help': 'changes file to upload/publish',
            },
        'rc-file': {
            'default': LDI.rcfile,
            'help': 'debinstall configuration file.',
            },
        }

    def version_info(self):
        self.record_version_info('ldi', LDI.version)

    def do_check(self, test):
        """run the checker against <path> (usually a directory)

        return true if the test succeeded, else false.
        """
        # FIXME https://www.logilab.net/elo/ticket/7967
        os.system('chmod a+rx -R %s ' % osp.dirname(test.deb_packages_dir))
        repository = self.options.get('repository')
        debinstallrc = self.options.get('rc-file')
        self.processed = {}
        LDI.init_log(handler=LdiLogHandler(self.writer))
        changesfiles = [f.path for f in self.options.get('changes-file')]
        LDI.run_command(self.command, [repository] + changesfiles, debinstallrc)
        if logger.status == utils.SUCCESS:
            self.processed['changesfiles'] = changesfile
        self.processed['repository'] = repository
        return logger.status

register('checker', LdiUploadChecker)


class LdiPublishChecker(LdiUploadChecker):
    """publish debian packages using ldi"""

    id = 'ldi.publish'
    command = 'publish'

register('checker', LdiPublishChecker)
