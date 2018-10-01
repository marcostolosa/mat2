import zipfile
import datetime
import tempfile
import os
import logging
import shutil
from typing import Dict, Set, Pattern

from . import abstract, UnknownMemberPolicy, parser_factory

# Make pyflakes happy
assert Set
assert Pattern


class ArchiveBasedAbstractParser(abstract.AbstractParser):
    """ Office files (.docx, .odt, …) are zipped files. """
    # Those are the files that have a format that _isn't_
    # supported by MAT2, but that we want to keep anyway.
    files_to_keep = set()  # type: Set[Pattern]

    # Those are the files that we _do not_ want to keep,
    # no matter if they are supported or not.
    files_to_omit = set()  # type: Set[Pattern]

    # what should the parser do if it encounters an unknown file in
    # the archive?
    unknown_member_policy = UnknownMemberPolicy.ABORT  # type: UnknownMemberPolicy

    def __init__(self, filename):
        super().__init__(filename)
        try:  # better fail here than later
            zipfile.ZipFile(self.filename)
        except zipfile.BadZipFile:
            raise ValueError

    def _specific_cleanup(self, full_path: str) -> bool:
        """ This method can be used to apply specific treatment
        to files present in the archive."""
        # pylint: disable=unused-argument,no-self-use
        return True  # pragma: no cover

    @staticmethod
    def _clean_zipinfo(zipinfo: zipfile.ZipInfo) -> zipfile.ZipInfo:
        zipinfo.create_system = 3  # Linux
        zipinfo.comment = b''
        zipinfo.date_time = (1980, 1, 1, 0, 0, 0)  # this is as early as a zipfile can be
        return zipinfo

    @staticmethod
    def _get_zipinfo_meta(zipinfo: zipfile.ZipInfo) -> Dict[str, str]:
        metadata = {}
        if zipinfo.create_system == 3:  # this is Linux
            pass
        elif zipinfo.create_system == 2:
            metadata['create_system'] = 'Windows'
        else:
            metadata['create_system'] = 'Weird'

        if zipinfo.comment:
            metadata['comment'] = zipinfo.comment  # type: ignore

        if zipinfo.date_time != (1980, 1, 1, 0, 0, 0):
            metadata['date_time'] = str(datetime.datetime(*zipinfo.date_time))

        return metadata

    def remove_all(self) -> bool:
        # pylint: disable=too-many-branches

        with zipfile.ZipFile(self.filename) as zin,\
             zipfile.ZipFile(self.output_filename, 'w') as zout:

            temp_folder = tempfile.mkdtemp()
            abort = False

            # Since files order is a fingerprint factor,
            # we're iterating (and thus inserting) them in lexicographic order.
            for item in sorted(zin.infolist(), key=lambda z: z.filename):
                if item.filename[-1] == '/':  # `is_dir` is added in Python3.6
                    continue  # don't keep empty folders

                zin.extract(member=item, path=temp_folder)
                full_path = os.path.join(temp_folder, item.filename)

                if self._specific_cleanup(full_path) is False:
                    logging.warning("Something went wrong during deep cleaning of %s",
                                    item.filename)
                    abort = True
                    continue

                if any(map(lambda r: r.search(item.filename), self.files_to_keep)):
                    # those files aren't supported, but we want to add them anyway
                    pass
                elif any(map(lambda r: r.search(item.filename), self.files_to_omit)):
                    continue
                else:  # supported files that we want to first clean, then add
                    tmp_parser, mtype = parser_factory.get_parser(full_path)  # type: ignore
                    if not tmp_parser:
                        if self.unknown_member_policy == UnknownMemberPolicy.OMIT:
                            logging.warning("In file %s, omitting unknown element %s (format: %s)",
                                            self.filename, item.filename, mtype)
                            continue
                        elif self.unknown_member_policy == UnknownMemberPolicy.KEEP:
                            logging.warning("In file %s, keeping unknown element %s (format: %s)",
                                            self.filename, item.filename, mtype)
                        else:
                            logging.error("In file %s, element %s's format (%s) " +
                                          "isn't supported",
                                          self.filename, item.filename, mtype)
                            abort = True
                            continue
                    if tmp_parser:
                        tmp_parser.remove_all()
                        os.rename(tmp_parser.output_filename, full_path)

                zinfo = zipfile.ZipInfo(item.filename)  # type: ignore
                clean_zinfo = self._clean_zipinfo(zinfo)
                with open(full_path, 'rb') as f:
                    zout.writestr(clean_zinfo, f.read())

        shutil.rmtree(temp_folder)
        if abort:
            os.remove(self.output_filename)
            return False
        return True
