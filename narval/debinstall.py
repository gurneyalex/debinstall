import os, os.path as osp
import logging

from narvalbot.prototype import input, output
from narvalbot.elements import FilePath

import apycotlib as apycot
from apycotlib.checkers import BaseChecker

from debinstall.ldi import LDI


# narval actions ###############################################################

def _ldi_checker(checker, inputs):
    test = inputs['apycot']
    options = inputs['options'].copy()
    options['changes-file'] = inputs['changes-file']
    return test.run_checker(checker, options)

def _get_changes_files(checker, repository, type):
    result = []
    for distrib, changesfiles in getattr(checker, 'debian_changes', {}).iteritems():
        for changesfile in changesfiles:
            result.append(FilePath(path=changesfile, type=type))


@input('changes-files', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True, list=True)
@output('changes-files', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        list=True)
@apycot.apycotaction('ldi.upload')
def act_ldi_upload(inputs):
    checker, status = _ldi_checker('ldi.upload', inputs)
    return {'changes-files': _get_changes_files(checker, inputs['options']['debian.repository'],
                                                'debian.changes.uploaded')}


@input('changes-files', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes"',
       use=True, list=True)
@output('changes-files', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.changes.uploaded"',
        list=True)
@output('repository', 'isinstance(elmt, FilePath)', 'elmt.type == "debian.repository"')
@apycot.apycotaction('ldi.publish')
def act_ldi_publish(inputs):
    checker, status = _ldi_checker('ldi.publish', inputs)
    repo = inputs['options']['debian.repository']
    return {'changes-files': _get_changes_files(checker, repo,
                                                'debian.changes.published'),
            'repository': FilePath(
                path=repo, type='debian.repository',
                published_dists=getattr(checker, 'debian_changes', ()))
            }


# apycot checkers ##############################################################

class LdiLogHandler(logging.Handler):
    def __init__(self, writer):
        logging.Handler.__init__(self)
        self.writer = writer
        self.path = None
        self.status = apycot.SUCCESS

    def emit(self, record):
        emitfunc = getattr(self.writer, record.levelname.lower())
        emitfunc(record.getMessage(), path=self.path)
        if record.level >= logging.ERROR:
            self.status = apycot.FAILURE


class LdiUploadChecker(BaseChecker):
    """upload debian packages using ldi"""

    id = 'ldi.upload'
    command = 'upload'
    options_def = {
        'debian.repository': {
            'required': True,
            'help': 'ldi repository name',
            },
        'changes-files': {
            'type': 'csv', 'required': True,
            'help': 'changes file to upload/publish',
            },
        'rc-file': {
            'default': LDI.rcfile,
            'help': 'debinstall configuration file.',
            },
        }

    def version_info(self):
        self.record_version_info('ldi', LDI.version)

    def _get_back_infos(self, cmd):
        self.debian_changes = getattr(cmd, 'debian_changes', {})
        for changes in self.debian_changes.itervalues():
            for change in changes:
                self.writer.raw(change, self.command, type=u'debian.changes')

    def do_check(self, test):
        """run the checker against <path> (usually a directory)

        return true if the test succeeded, else false.
        """
        # FIXME https://www.logilab.net/elo/ticket/7967
        os.system('chmod a+rx -R %s ' % osp.dirname(test.deb_packages_dir))
        repository = self.options.get('debian.repository')
        debinstallrc = self.options.get('rc-file')
        self.processed = {}
        changesfiles = [f.path for f in self.options.get('changes-files')]
        handler = LdiLogHandler(self.writer)
        cmd = LDI.get_command(self.command, logger=LDI.create_logger(handler))
        exit_status = cmd.main_run([repository] + changesfiles, rcfile=debinstallrc)
        self._get_back_infos(cmd)
        if exit_status:
            self.writer.fatal('ldi %s exited with status %s', self.command, exit_status)
            self.set_status(apycot.ERROR)
        return handler.status

apycot.register('checker', LdiUploadChecker)


class LdiPublishChecker(LdiUploadChecker):
    """publish debian packages using ldi"""

    id = 'ldi.publish'
    command = 'publish'

    def _get_back_infos(self, cmd):
        super(LdiPublishChecker, self)._get_back_infos(cmd)
        for dist in self.debian_changes:
            self.writer.raw(dist, 'published', type=u'debian.repository')

apycot.register('checker', LdiPublishChecker)
