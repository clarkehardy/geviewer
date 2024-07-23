import unittest
from unittest import mock
import tempfile
from geviewer import geviewer


class TestGeViewerSafe(unittest.TestCase):

    def setUp(self):
        '''
        Create a GeViewer object with safe mode enabled.
        '''
        self.gev = geviewer.GeViewer('tests/sample.wrl',safe_mode=True,off_screen=True)


    def test_key_inputs(self):
        '''
        Test the key inputs for the GeViewer object.
        '''
        self.assertEqual(self.gev.toggle_tracks(),None)
        self.assertEqual(self.gev.toggle_hits(),None)
        self.assertEqual(self.gev.toggle_background(),None)


    @mock.patch.object(geviewer.GeViewer,'prompt_for_file_path')
    def test_save_screenshot(self,mocked_input):
        '''
        Test the save_screenshot method with a mocked file name input.
        '''
        mocked_input.side_effect = [tempfile.mkstemp(suffix='.png')[1]]
        self.assertEqual(self.gev.save_screenshot(),None)


    @mock.patch.object(geviewer.GeViewer,'prompt_for_file_path')
    def test_save_graphic(self,mocked_input):
        '''
        Test the save_graphic method with mocked file name inputs.
        '''
        mocked_input.side_effect = [None,tempfile.mkstemp(suffix='.svg')[1],\
                                    None,tempfile.mkstemp(suffix='.eps')[1],\
                                    None,tempfile.mkstemp(suffix='.ps')[1],\
                                    None,tempfile.mkstemp(suffix='.pdf')[1],\
                                    None,tempfile.mkstemp(suffix='.tex')[1]]
        for i in mocked_input.side_effect:
            self.assertEqual(self.gev.save_graphic(),None)
    

if __name__ == '__main__':
    unittest.main()