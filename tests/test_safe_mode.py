import unittest
from unittest import mock
import tempfile
import numpy as np
from os.path import isfile
from geviewer import geviewer


class TestGeViewerSafe(unittest.TestCase):

    def setUp(self):
        '''
        Create a GeViewer object with safe mode enabled.
        '''
        self.gev = geviewer.GeViewer(['tests/sample.wrl'],safe_mode=True,off_screen=True)


    def test_key_inputs(self):
        '''
        Test the key inputs for the GeViewer object.
        '''
        for i in range(2):
            with self.subTest():
                self.gev.toggle_tracks()
            with self.subTest():
                self.gev.toggle_step_markers()
            with self.subTest():
                colors = ['lightskyblue','white']
                bkg_status = self.gev.bkg_on
                self.gev.toggle_background()
                self.assertEqual(self.gev.plotter.background_color,colors[bkg_status])


    @mock.patch('geviewer.utils.prompt_for_file_path')
    def test_save_screenshot(self,mocked_input):
        '''
        Test the save_graphic method with mocked file name inputs.
        '''
        file_names = [tempfile.mkstemp(suffix='.png')[1],\
                      tempfile.mkstemp(suffix='.svg')[1],\
                      tempfile.mkstemp(suffix='.eps')[1],\
                      tempfile.mkstemp(suffix='.ps')[1],\
                      tempfile.mkstemp(suffix='.pdf')[1],\
                      tempfile.mkstemp(suffix='.tex')[1]]
        mocked_input.side_effect = file_names
        self.gev.save_screenshot()
        for i in mocked_input.side_effect:
            with self.subTest():
                self.assertTrue(isfile(i))


    @mock.patch('geviewer.utils.prompt_for_window_size',return_value=[800,600])
    def test_set_window_size(self,mocked_input):
        '''
        Test the set_window_size method with a mocked window size input.
        '''
        self.gev.set_window_size()
        self.assertEqual(self.gev.plotter.window_size,[800,600])


    @mock.patch('geviewer.utils.prompt_for_camera_view')
    def test_set_camera_view(self,mocked_input):
        '''
        Test the set_camera_view method with a mocked camera viewpoint input.
        '''
        pos = (1,2,3)
        up_input = (4,5,6)
        focus = (7,8,9)
        up_output = tuple(np.array(up_input)/np.linalg.norm(up_input))
        mocked_input.return_value = [pos,up_input,focus]                                   
        with self.subTest():
            self.gev.set_camera_view()
            self.assertEqual(self.gev.plotter.camera.position,pos)
            self.assertEqual(self.gev.plotter.camera.up,up_output)
            self.assertEqual(self.gev.plotter.camera.focal_point,focus)
    

if __name__ == '__main__':
    unittest.main()