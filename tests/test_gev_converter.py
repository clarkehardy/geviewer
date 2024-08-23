import unittest
from unittest import mock
import os
import tempfile
from geviewer import converter, viewer
from pathlib import Path

class TestGevConverter(unittest.TestCase):

    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_gev_converter_wrl(self, mock_parse_args):
        """Tests the gev-converter command-line utility with a VRML file.
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = 'tests/sample.wrl'
            output_file = os.path.join(temp_dir, 'sample.gev')
            
            mock_args = mock.Mock()
            mock_args.file = Path(input_file)
            mock_args.destination = Path(output_file)
            mock_parse_args.return_value = mock_args

            converter.main()
            
            gev = viewer.GeViewer()
            gev.load_file(output_file, off_screen=True)
            self.assertEqual(len(gev.components[0]['children']), 3)


    @mock.patch('argparse.ArgumentParser.parse_args')
    def test_gev_converter_heprep(self, mock_parse_args):
        """Tests the gev-converter command-line utility with a HepRep file.
        """
        
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = 'tests/sample.heprep'
            output_file = os.path.join(temp_dir, 'sample.gev')

            mock_args = mock.Mock()
            mock_args.file = Path(input_file)
            mock_args.destination = Path(output_file)
            mock_parse_args.return_value = mock_args

            converter.main()
            
            gev = viewer.GeViewer()
            gev.load_file(output_file, off_screen=True)
            self.assertEqual(len(gev.components[0]['children']), 2)


if __name__ == '__main__':
    unittest.main()