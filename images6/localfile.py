"""Helper classes for dealing with local file operations."""


import os
import errno
import logging
import shutil


################################################################################
# Standard File Copyer Class


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
