"""Take care of Image imports, exports and proxy generation"""

import logging
import os
from PIL import Image
import exifread
from datetime import datetime

from ..system import current_system
from ..importer import GenericImportModule, register_import_module
from ..localfile import FileCopy
from ..entry import Entry, Variant, create_entry, update_entry_by_id, delete_entry_by_id, State, Access, Purpose
from ..exif import exif_position, exif_orientation, exif_string, exif_int, exif_ratio
from ..types import PropertySet, Property
from ..metadata import register_metadata_schema



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

        angle, mirror = metadata.Angle, metadata.Mirror
        self.create_variant('thumb', Purpose.thumb, self.system.thumb_size, angle, mirror)
        self.create_variant('proxy', Purpose.proxy, self.system.proxy_size, angle, mirror)
        self.create_check(angle, mirror)
        logging.debug('Created proxy files.')

        self.entry.metadata = metadata

        self.entry.state = State.pending
        self.entry = update_entry_by_id(self.entry.id, self.entry)
        logging.debug('Updated entry.\n%s', self.entry.to_json())

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

    def create_variant(self, store, purpose, longest_edge, angle, mirror):
        variant = Variant(
            store=store,
            mime_type='image/jpeg',
            purpose=purpose,
        )
        full_path = os.path.join(
            self.system.media_root,
            variant.get_filename(self.entry.id),
        )
        variant.width, variant.height = _convert(
            self.full_original_file_path,
            full_path,
            longest_edge=longest_edge,
            angle=angle,
            mirror=mirror,
        )
        s = os.stat(full_path)
        variant.size=s.st_size
        self.entry.variants.append(variant)

    def create_check(self, angle, mirror):
        variant = Variant(
            store='check',
            mime_type='image/jpeg',
            purpose=Purpose.check,
        )
        full_path = os.path.join(
            self.system.media_root,
            variant.get_filename(self.entry.id),
        )
        variant.width, variant.height = _create_check(
            self.full_original_file_path,
            full_path,
            angle=angle,
            mirror=mirror,
            size=self.system.check_size,
        )
        s = os.stat(full_path)
        variant.size=s.st_size
        self.entry.variants.append(variant)

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


register_metadata_schema(JPEGMetadata)


def _create_check(path_in, path_out, size=200, angle=None, mirror=None):
    os.makedirs(os.path.dirname(path_out), exist_ok=True)

    with open(path_out, 'w') as out:
        img = Image.open(path_in)
        width, height = img.size

        left = int((width - size) / 2)
        top = int((height - size) / 2)
        right = int((width + size) / 2)
        bottom = int((height + size) / 2)

        logging.debug('Cropping %i %i %i %i', left, top, right, bottom)
        cropped = img.crop((left, top, right, bottom))
        img.close()

        if mirror == 'H':
            cropped = cropped.transpose(Image.FLIP_RIGHT_LEFT)
        elif mirror == 'V':
            cropped = cropped.transpose(Image.FLIP_TOP_BOTTOM)
        if angle:
            logging.debug('Rotating by %i degrees', angle)
            cropped = cropped.rotate(angle)

        cropped.save(out, "JPEG", quality=98)
        cropped.close()
        logging.debug("Created check %s", path_out)
        return size, size


def _convert(path_in, path_out, longest_edge=1280, angle=None, mirror=None):
    os.makedirs(os.path.dirname(path_out), exist_ok=True)

    with open(path_out, 'w') as out:
        img = Image.open(path_in)
        width, height = img.size
        if width > height:
            scale = float(longest_edge) / float(width)
        else:
            scale = float(longest_edge) / float(height)
        w = int(width * scale)
        h = int(height * scale)
        logging.debug('_resize %i %i %i', h, w, angle)
        _resize(img, (w, h), out, angle, mirror)
        logging.info("Created image %s", path_out)
        return w, h


def _resize(img, box, out, angle, mirror):
    '''Downsample the image.
    @param img: Image -  an Image-object
    @param box: tuple(x, y) - the bounding box of the result image
    @param out: file-like-object - save the image into the output stream
    @param angle: int - rotate with this angle
    @param mirror: str - mirror in this direction, None, "H" or "V"
    '''
    # Preresize image with factor 2, 4, 8 and fast algorithm
    factor = 1
    bw, bh = box
    iw, ih = img.size
    while (iw * 2 / factor > 2 * bw) and (ih * 2 / factor > 2 * bh):
        factor *= 2
    factor /= 2
    if factor > 1:
        logging.debug('factor = %d: Scale down to %ix%i', factor, int(iw / factor), int(ih / factor))
        img.thumbnail((iw / factor, ih / factor), Image.NEAREST)

    # Resize the image with best quality algorithm ANTI-ALIAS
    logging.debug('Final scale down to %ix%i', box[0], box[1])
    img.thumbnail(box, Image.ANTIALIAS)
    if mirror == 'H':
        img = img.transpose(Image.FLIP_RIGHT_LEFT)
    elif mirror == 'V':
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if angle:
        logging.debug('Rotating by %i degrees', angle)
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)

    # Save it into a file-like object
    img.save(out, "JPEG", quality=90)
