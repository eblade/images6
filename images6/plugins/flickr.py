import os
import logging
from jsonobject import register_schema, PropertySet, Property

from ..system import current_system
from ..plugin import GenericPlugin, register_plugin
from ..entry import get_entry_by_id, update_entry_by_id, Purpose, Backup


class FlickrOptions(PropertySet):
    entry_id = Property(int)
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

        import flickrapi
        flickr = flickrapi.FlickrAPI(api_key=self.key, secret=self.secret)
        flickr.authenticate_via_browser(perms='write')
        response = flickr.upload(
            filename=os.path.join(current_system().media_root, entry.get_filename(Purpose.original)),
            title=payload.title or '',
            description=payload.description or '',
            is_public=payload.is_public,
            format='etree',
        )
        photo_id = response.find('photoid').text

        backup = Backup(
            method='flickr',
            key=photo_id,
        )
        logging.info('Backup\n%s', backup.to_json())

        entry.backups.append(backup)
        if entry.title is None:
            entry.title = payload.title
        if entry.description is None:
            entry.description = payload.description
        
        update_entry_by_id(entry.id, entry)
        logging.info('Done with flickr export.')


register_plugin(FlickrPlugin)
