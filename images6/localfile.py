"""Helper classes for dealing with local file operations."""


import os
import errno
import logging
import shutil


class FileCopy(object):
    def __init__(
            self,
            source=None,
            destination=None,
            link=False,
            remove_source=False):

        self.source = source
        self.destination = destination
        self.link = link
        self.remove_source = remove_source

    def run(self):
        destination_folder = os.path.dirname(self.destination)
        os.makedirs(destination_folder, exist_ok=True)

        while True:
            try:
                if self.link:
                    logging.debug("Linking %s -> %s", self.source, self.destination)
                    os.link(self.source, self.destination)
                else:
                    logging.debug("Copying %s -> %s", self.source, self.destination)
                    shutil.copyfile(self.source, self.destination)
                break
            except OSError as e:
                if e.errno == errno.EXDEV:
                    logging.warning("Cross-device link %s -> %s", self.source, self.destination)
                    self.link = False
                else:
                    logging.warning("OSError %i %s -> %s (%s)", e.errno, self.source, self.destination, str(e))
                    raise e

        if self.remove_source:
            logging.debug("Removing source %s", self.source)
            os.remove(self.source)


class FolderScanner(object):
    def __init__(self, basepath, extensions=None):
        self.basepath = basepath
        if extensions is None:
            self.extensions = None
        else:
            self.extensions = [e.lower() for e in extensions]
            self.extensions = [e if e.startswith('.') else ('.' + e) for e in self.extensions]
            self.extensions.extend([e.upper() for e in self.extensions])
        logging.debug('Scanning for file-extensions %s', str(self.extensions))

    def scan(self):
        for relative_path, directories, files in os.walk(self.basepath, followlinks=True):
            logging.debug('Scanning %s', relative_path)
            for f in files:
                if self.extensions is None or any(map(lambda e: f.endswith(e), self.extensions)):
                    path = os.path.relpath(os.path.join(relative_path, f), self.basepath)
                    if not path.startswith('.'):
                        yield path


