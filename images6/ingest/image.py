import logging
import os
import exifread
from datetime import datetime
from jsonobject import PropertySet, Property, register_schema

from ..system import current_system
from ..importer import GenericImportModule, register_import_module
from ..localfile import FileCopy
from ..entry import (
    Entry,
    Variant,
    State,
    Access,
    Purpose,
    create_entry,
    update_entry_by_id,
    delete_entry_by_id,
)
from ..exif import(
    exif_position,
    exif_orientation,
    exif_string,
    exif_int,
    exif_ratio,
)
from ..plugin import trig_plugin
from ..plugins.imageproxy import ImageProxyOptions


class JPEGImportModule(GenericImportModule):
    def run(self):
        self.full_source_file_path = self.folder.get_full_path(self.file_path)
        logging.debug('Import %s', self.full_source_file_path)
        self.system = current_system()

        logging.debug('Creating entry...')
        self.entry = create_entry(Entry(
            original_filename=os.path.basename(self.file_path),
            state=State.new,
            import_folder=self.folder.name,
            mime_type=self.mime_type,
        ))
        logging.debug('Created entry.\n%s', self.entry.to_json())

        self.create_original()
        logging.debug('Created original.')

        metadata = JPEGMetadata(**(self.analyse()))
        self.fix_taken_ts(metadata)
        logging.debug('Read metadata.')

        self.entry.metadata = metadata

        self.entry.state = State.pending
        self.entry = update_entry_by_id(self.entry.id, self.entry)
        logging.debug('Updated entry.\n%s', self.entry.to_json())

        options = ImageProxyOptions(entry_id=self.entry.id)
        trig_plugin('imageproxy', options)
        logging.debug('Created image proxy task.')

    def clean_up(self):
        logging.debug('Cleaning up...')
        delete_entry_by_id(self.entry.id)
        logging.debug('Cleaned up.')

    def create_original(self):
        original = Variant(
            store='original',
            mime_type=self.mime_type,
            purpose=Purpose.original,
        )
        filecopy = FileCopy(
            source=self.full_source_file_path,
            destination=os.path.join(
                self.system.media_root,
                original.get_filename(self.entry.id)
            ),
            link=True,
            remove_source=self.folder.auto_remove,
        )
        filecopy.run()
        self.full_original_file_path = filecopy.destination
        original.size = os.path.getsize(filecopy.destination)
        self.entry.variants.append(original)

    def fix_taken_ts(self, metadata):
        real_date = metadata.DateTimeOriginal
        if not real_date:
            return

        self.entry.taken_ts = (datetime.strptime(
                real_date, '%Y:%m:%d %H:%M:%S').replace(microsecond=0)
                .strftime('%Y-%m-%d %H:%M:%S')
        )

    def analyse(self):
        infile = self.full_original_file_path

        exif = None
        with open(infile, 'rb') as f:
            exif = exifread.process_file(f)

        # Orientation (rotation)
        orientation, mirror, angle = exif_orientation(exif)

        # GPS Position
        lon, lat = exif_position(exif)

        return {
            "Artist": exif_string(exif, "Image Artist"),
            "ColorSpace": exif_string(exif, "EXIF ColorSpace"),
            "Copyright": exif_string(exif, "Image Copyright"),
            "Geometry": (exif_int(exif, "EXIF ExifImageWidth"), exif_int(exif, "EXIF ExifImageLength")),
            "DateTime": exif_string(exif, "EXIF DateTime"),
            "DateTimeDigitized": exif_string(exif, "EXIF DateTimeDigitized"),
            "DateTimeOriginal": exif_string(exif, "EXIF DateTimeOriginal"),
            "ExposureTime": exif_ratio(exif, "EXIF ExposureTime"),
            "FNumber": exif_ratio(exif, "EXIF FNumber"),
            "Flash": exif_string(exif, "EXIF Flash"),
            "FocalLength": exif_ratio(exif, "EXIF FocalLength"),
            "FocalLengthIn35mmFilm": exif_int(exif, "EXIF FocalLengthIn35mmFilm"),
            "ISOSpeedRatings": exif_int(exif, "EXIF ISOSpeedRatings"),
            "Make": exif_string(exif, "Image Make"),
            "Model": exif_string(exif, "Image Model"),
            "Orientation": orientation,
            "Mirror": mirror,
            "Angle": angle,
            "Saturation": exif_string(exif, "EXIF Saturation"),
            "Software": exif_string(exif, "Software"),
            "SubjectDistanceRange": exif_int(exif, "EXIF SubjectDistanceRange"),
            "WhiteBalance": exif_string(exif, "WhiteBalance"),
            "Latitude": lat,
            "Longitude": lon,
        }

register_import_module('image/jpeg', JPEGImportModule)
register_import_module('image/tiff', JPEGImportModule)


class JPEGMetadata(PropertySet):
    Artist = Property()
    ColorSpace = Property()
    Copyright = Property()
    DateTime = Property()
    DateTimeDigitized = Property()
    DateTimeOriginal = Property()
    ExposureTime = Property(tuple)
    FNumber = Property(tuple)
    Flash = Property()
    FocalLength = Property(tuple)
    FocalLengthIn35mmFilm = Property(int)
    Geometry = Property(tuple)
    ISOSpeedRatings = Property(int)
    Make = Property()
    Model = Property()
    Orientation = Property()
    Mirror = Property()
    Angle = Property(int, default=0)
    Saturation = Property()
    Software = Property()
    SubjectDistanceRange = Property(int)
    WhiteBalance = Property()
    Latitude = Property()
    Longitude = Property()


register_schema(JPEGMetadata)


