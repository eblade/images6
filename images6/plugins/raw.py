import os
import logging

from ..system import current_system
from ..plugin import GenericPlugin, register_plugin
from ..metadata import register_metadata_schema
from ..types import PropertySet, Property
from ..entry import get_entry_by_id, update_entry_by_id, Purpose, Variant
from ..localfile import FileCopy, FolderScanner


class RawFetchOptions(PropertySet):
    entry_id = Property(int)


register_metadata_schema(RawFetchOptions)


class RawFetcherPlugin(GenericPlugin):
    method = 'rawfetch'

    def run(self, payload):
        logging.info('Starting raw fetching.')
        logging.info('Options\n%s', payload.to_json())

        entry = get_entry_by_id(payload.entry_id)
        logging.info('Original filename is %s', entry.original_filename)

        full_raw_file_path = self.find_raw(entry.original_filename)
        if full_raw_file_path is None:
            logging.info('Could not find a raw file for %s', entry.original_filename)
            return

        _, extension = os.path.splitext(full_raw_file_path)
        raw = Variant(
            store='raw',
            mime_type='image/' + extension.lower().replace('.', ''),
            purpose=Purpose.raw,
        )
        filecopy = FileCopy(
            source=full_raw_file_path,
            destination=os.path.join(
                current_system().media_root,
                raw.get_filename(entry.id)
            ),
            link=True,
            remove_source=False,
        )
        filecopy.run()
        raw.size = os.path.getsize(filecopy.destination)
        entry.variants.append(raw)

        update_entry_by_id(entry.id, entry)
        logging.info('Done with raw fetching.')

    def find_raw(self, original_filename):
        raw_extensions = [e.strip() for e in self.extensions.split() if e.strip()]
        raw_extensions = [e if e.startswith('.') else ('.' + e) for e in raw_extensions]
        raw_locations = [l.strip() for l in self.locations.split('\n') if l.strip()]

        wanted_without_extension, _ = os.path.splitext(original_filename)
        logging.info('Without extension: %s', wanted_without_extension)

        for location in raw_locations:
            logging.info('Scanning for raws in %s', location)
            scanner = FolderScanner(location, extensions=raw_extensions)
            for filepath in scanner.scan():
                filename = os.path.basename(filepath)
                logging.info('Found one raw %s', filename)
                without_extension, _ = os.path.splitext(filename)
                if without_extension == wanted_without_extension:
                    logging.info('Found raw %s', filepath)
                    return os.path.join(location, filepath)



register_plugin(RawFetcherPlugin)
