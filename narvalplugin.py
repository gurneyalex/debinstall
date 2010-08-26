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
    options = inputs['options']
    options['changes-file'] = inputs['changes-file']
    checker, status = test.run_checker(checker, options)
    return status


@input('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True)
@input('options', 'isinstance(elmt, Options)', '"debian.repository" in elmt')
@output('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        optional=True)
@utils.apycotaction('ldi.upload')
def act_ldi_upload(inputs):
    status = _ldi_checker('ldi.upload', inputs)
    if status == utils.SUCCESS:
        path = osp.join(inputs['options'].repository, 'incoming',
                        inputs['changes-file'].distribution,
                        osp.basename(inputs['changes-file']))
        return {'changes-file': FilePath(path=path, type='debian.changes.uploaded')}
    return {}


@input('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True)
@input('options', 'isinstance(elmt, Options)', '"debian.repository" in elmt')
@output('changes-file', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        optional=True)
@utils.apycotaction('ldi.publish')
def act_ldi_publish(inputs):
    status = _ldi_checker('ldi.publish', inputs)
    if status == utils.SUCCESS:
        path = osp.join(inputs['options'].repository, 'dists',
                        inputs['changes-file'].distribution,
                        osp.basename(inputs['changes-file']))
        return {'changes-file': FilePath(path=path, type='debian.changes.published')}
    return {}


# apycot checkers ##############################################################

class LdiLogHandler(logging.Handler):
    def __init__(self, writer, path):
        logging.Handler.__init__(self)
        self.writer = writer
        self.path = path
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
        repository = self.get_option('repository')
        debinstallrc = self.get_option('rc-file', LDI.rcfile)
        changesfile = self.get_option('changes-file').path
        LDI.logger = logger = LdiLogHandler(self.writer, changesfile)
        LDI.run_command(self.command, [repository, changesfile], debinstallrc)
        return logger.status

register('checker', LdiUploadChecker)


class LdiPublishChecker(LdiUploadChecker):
    """publish debian packages using ldi"""

    id = 'ldi.publish'
    command = 'publish'

register('checker', LdiPublishChecker)
