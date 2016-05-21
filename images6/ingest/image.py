"""Take care of Image imports, exports and proxy generation"""

import logging
import os
from PIL import Image
import exifread
from datetime import datetime

from ..system import current_system
from ..importer import GenericImportModule, register_import_module
from ..localfile import FileCopy
from ..entry import Entry, Variant, create_entry, update_entry_by_id, State, Access, Purpose
from ..exif import exif_position, exif_orientation, exif_string, exif_int, exif_ratio
from ..types import PropertySet, Property
from ..metadata import register_metadata_schema



class JPEGImportModule(GenericImportModule):
    def run(self):
        self.full_source_file_path = self.folder.get_full_path(self.file_path)
        self.system = current_system()

        self.entry = create_entry(Entry(
            original_filename=os.path.basename(self.file_path),
            state=State.new,
        ))

        self.create_original()

        metadata = JPEGMetadata(**(self.analyse()))
        self.fix_taken_ts(metadata)

        angle, mirror = metadata.Angle, metadata.Mirror
        self.create_variant('thumb', Purpose.thumb, self.system.thumb_size, angle, mirror)
        self.create_variant('proxy', Purpose.proxy, self.system.proxy_size, angle, mirror)
        self.create_check(angle, mirror)

        self.entry.metadata = metadata

        update_entry_by_id(self.entry.id, self.entry)

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
            remove_source=folder.auto_remove,
        )
        filecopy.run()
        self.full_original_file_path = filecopy.destination_full_path
        original.file_size = os.path.getsize(filecopy.destination_full_path)
        self.entry.variants.append(original)

    def fix_taken_ts(self, metadata):
        real_date = metadata.DateTimeOriginal
        if not real_date:
            return

        self.entry.taken_ts = (datetime.strptime(
                real_date, '%Y:%m:%d %H:%M:%S').replace(microsecond=0)
                .strftime('%Y-%m-%d %H:%M:%S')
        )

    def create_variant(self, store, purpose, size, angle, mirror):
        variant = Variant(
            store=store,
            mime_type='image/jpeg',
            purpose=purpose,
        )
        full_path = os.path.join(
            self.system.media_root,
            variant.get_filename(self.entry.id),
        ),
        variant.width, variant.height = _convert(
            self.full_original_file_path,
            full_path,
            angle=angle,
            mirror=mirror,
            size=size,
        )
        s = os.stat(full_path)
        variant.size=s.st_size,
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
        ),
        variant.width, variant.height = _create_check(
            self.full_original_file_path,
            full_path,
            angle=angle,
            mirror=mirror,
            size=self.system.check_size,
        )
        s = os.stat(full_path)
        variant.size=s.st_size,
        self.entry.variants.append(variant)

    def analyse(self):
        infile = self.image_path

        exif = None
        with open(infile, 'rb') as f:
            exif = exifread.process_file(f)

        orientation, mirror, angle = exif_orientation(exif)
        lon, lat = exif_position(exif)
        logging.debug(exif)

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
            "Longitude": lon
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
        width, height = im.size

        bx = width / 2 - size / 2
        by = height / 2 - size / 2

        img = img.crop((x, y, size, size))

        if mirror == 'H':
            img = img.transpose(Image.FLIP_RIGHT_LEFT)
        elif mirror == 'V':
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        if angle:
            img = img.rotate(angle)

        img.save(out, "JPEG", quality=98)
        img.close()
        logging.info("Created check %s", path_out)
        return size, size


def _convert(path_in, path_out, longest_edge=1280, angle=None, mirror=None):
    os.makedirs(os.path.dirname(path_out), exist_ok=True)

    with open(path_out, 'w') as out:
        im = Image.open(path_in)
        width, height = im.size
        if width > height:
            scale = float(longest_edge) / float(width)
        else:
            scale = float(longest_edge) / float(height)
        w = int(width * scale)
        h = int(height * scale)
        _resize(im, (w, h), False, out, angle, mirror)
        im.close()
        logging.info("Created image %s", path_out)
        return w, h


def _crop(img, pos, box, out, angel, mirror):
    '''Crop the image
    @param img: Image - an Image-object
    @param pos: (x, y) position to read from
    @param box: (w, h) box size to read from
    @param out: file-like object
    @param angle: int - rotate with this angle
    @param mirror: str - mirror in this direction, None, "H" or "V"
    '''

def _resize(img, box, fit, out, angle, mirror):
    '''Downsample the image.
    @param img: Image -  an Image-object
    @param box: tuple(x, y) - the bounding box of the result image
    @param fit: boolean - crop the image to fill the box
    @param out: file-like-object - save the image into the output stream
    @param angle: int - rotate with this angle
    @param mirror: str - mirror in this direction, None, "H" or "V"
    '''
    # Preresize image with factor 2, 4, 8 and fast algorithm
    factor = 1
    bw, bh = box
    iw, ih = img.size
    while (iw*2/factor > 2*bw) and (ih*2/factor > 2*bh):
        factor *= 2
    factor /= 2
    if factor > 1:
        img.thumbnail((iw/factor, ih/factor), Image.NEAREST)

    # Calculate the cropping box and get the cropped part
    if fit:
        x1 = y1 = 0
        x2, y2 = img.size
        wRatio = 1.0 * x2/box[0]
        hRatio = 1.0 * y2/box[1]
        if hRatio > wRatio:
            y1 = int(y2/2-box[1]*wRatio/2)
            y2 = int(y2/2+box[1]*wRatio/2)
        else:
            x1 = int(x2/2-box[0]*hRatio/2)
            x2 = int(x2/2+box[0]*hRatio/2)
        img = img.crop((x1, y1, x2, y2))

    # Resize the image with best quality algorithm ANTI-ALIAS
    img.thumbnail(box, Image.ANTIALIAS)
    if mirror == 'H':
        img = img.transpose(Image.FLIP_RIGHT_LEFT)
    elif mirror == 'V':
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if angle:
        img = img.rotate(angle)

    # Save it into a file-like object
    img.save(out, "JPEG", quality=85)
