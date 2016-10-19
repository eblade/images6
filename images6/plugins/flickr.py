import os
import logging
from jsonobject import register_schema, PropertySet, Property

from ..system import current_system
from ..plugin import GenericPlugin, register_plugin
from ..entry import get_entry_by_id, update_entry_by_id, Purpose, Backup


class FlickrOptions(PropertySet):
    entry_id = Property(int)
    source_purpose = Property(enum=Purpose, default=Purpose.original)
    source_version = Property(int)
    title = Property()
    description = Property()
    tags = Property(list)
    is_public = Property(bool, default=True)


register_schema(FlickrOptions)


class FlickrPlugin(GenericPlugin):
    method = 'flickr'

    def run(self, payload):
        logging.info('Starting flickr export.')
        logging.info('Options\n%s', payload.to_json())

        entry = get_entry_by_id(payload.entry_id)

        flickr_backup = None
        for backup in entry.backups:
            if backup.method == 'flickr':
                flickr_backup = backup

        import flickrapi
        flickr = flickrapi.FlickrAPI(api_key=self.key, secret=self.secret)
        flickr.authenticate_via_browser(perms='write')

        self.source = entry.get_variant(payload.source_purpose, version=payload.source_version)

        if flickr_backup is None:
            logging.debug('Uploading to flickr')
            response = flickr.upload(
                filename=os.path.join(current_system().media_root, self.source.get_filename(entry.id)),
                title=payload.title or entry.title or '',
                description=payload.description or entry.description or '',
                is_public=payload.is_public,
                format='etree',
            )
            photo_id = response.find('photoid').text

            flickr_backup = Backup(
                method='flickr',
                key=photo_id,
                source_purpose=self.source.purpose,
                source_version=self.source.version,
            )
            logging.info('Backup\n%s', flickr_backup.to_json())

            entry.backups.append(flickr_backup)

            if entry.title is None:
                entry.title = payload.title
            if entry.description is None:
                entry.description = payload.description

            update_entry_by_id(entry.id, entry)

        else:
            logging.debug('Replacing image on flickr')
            logging.info('Backup\n%s', flickr_backup.to_json())
            response = flickr.replace(
                filename=os.path.join(current_system().media_root, entry.get_filename(Purpose.original)),
                photo_id=flickr_backup.key,
                format='etree',
            )

            flickr_backup.source_purpose = self.source.purpose
            flickr_backup.source_version = self.source.version

            update_entry_by_id(entry.id, entry)

        logging.info('Done with flickr export.')


register_plugin(FlickrPlugin)
