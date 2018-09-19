#!/usr/bin/env python3

import unittest
import shutil
import os
import zipfile
import tempfile

from libmat2 import office, parser_factory

class TestZipMetadata(unittest.TestCase):
    def __check_deep_meta(self, p):
        tempdir = tempfile.mkdtemp()
        zipin = zipfile.ZipFile(p.filename)
        zipin.extractall(tempdir)

        for subdir, dirs, files in os.walk(tempdir):
            for f in files:
                complete_path = os.path.join(subdir, f)
                inside_p, _ = parser_factory.get_parser(complete_path)
                if inside_p is None:
                    continue
                self.assertEqual(inside_p.get_meta(), {})
        shutil.rmtree(tempdir)


    def __check_zip_meta(self, p):
        zipin = zipfile.ZipFile(p.filename)
        for item in zipin.infolist():
            self.assertEqual(item.comment, b'')
            self.assertEqual(item.date_time, (1980, 1, 1, 0, 0, 0))
            self.assertEqual(item.create_system, 3)  # 3 is UNIX


    def test_office(self):
        shutil.copy('./tests/data/dirty.docx', './tests/data/clean.docx')
        p = office.MSOfficeParser('./tests/data/clean.docx')

        meta = p.get_meta()
        self.assertIsNotNone(meta)

        ret = p.remove_all()
        self.assertTrue(ret)

        p = office.MSOfficeParser('./tests/data/clean.cleaned.docx')
        self.assertEqual(p.get_meta(), {})

        self.__check_zip_meta(p)
        self.__check_deep_meta(p)

        os.remove('./tests/data/clean.docx')
        os.remove('./tests/data/clean.cleaned.docx')


    def test_libreoffice(self):
        shutil.copy('./tests/data/dirty.odt', './tests/data/clean.odt')
        p = office.LibreOfficeParser('./tests/data/clean.odt')

        meta = p.get_meta()
        self.assertIsNotNone(meta)

        ret = p.remove_all()
        self.assertTrue(ret)

        p = office.LibreOfficeParser('./tests/data/clean.cleaned.odt')
        self.assertEqual(p.get_meta(), {})

        self.__check_zip_meta(p)
        self.__check_deep_meta(p)

        os.remove('./tests/data/clean.odt')
        os.remove('./tests/data/clean.cleaned.odt')