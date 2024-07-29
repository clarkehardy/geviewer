import unittest
from unittest import mock
import tempfile
from os.path import isfile
from os import remove
import numpy as np
from geviewer import main, geviewer


class TestGeViewerMain(unittest.TestCase):

    def setUp(self):
        """Create a GeViewer object.
        """
        self.gev = geviewer.GeViewer(['tests/sample.wrl'], off_screen=True)


    def test_print_instructions(self):
        """Test the print_instructions function.
        """
        main.print_instructions()


    def test_key_inputs(self):
        """Test the key inputs for the GeViewer object.
        """
        for i in range(2):
            with self.subTest():
                track_status = self.gev.visible[0]
                self.gev.toggle_tracks()
                track_actors = self.gev.actors[0]
                self.assertTrue(track_actors.visibility!=track_status)
            with self.subTest():
                step_status = self.gev.visible[1]
                self.gev.toggle_step_markers()
                step_actors = self.gev.actors[1]
                self.assertTrue(step_actors.visibility!=step_status)
            with self.subTest():
                colors = ['lightskyblue','white']
                bkg_status = self.gev.bkg_on
                self.gev.toggle_background()
                self.assertEqual(self.gev.plotter.background_color, colors[bkg_status])


    @mock.patch('geviewer.utils.prompt_for_screenshot_path')
    def test_save_screenshot(self, mocked_input):
        """Test the save_graphic method with mocked file name inputs.
        """
        file_names = [tempfile.mkstemp(suffix='.png')[1],\
                      tempfile.mkstemp(suffix='.svg')[1],\
                      tempfile.mkstemp(suffix='.eps')[1],\
                      tempfile.mkstemp(suffix='.ps')[1],\
                      tempfile.mkstemp(suffix='.pdf')[1],\
                      tempfile.mkstemp(suffix='.tex')[1]]
        mocked_input.side_effect = file_names
        for i in file_names:
            self.gev.save_screenshot()
            with self.subTest():
                self.assertTrue(isfile(i))
        for file in file_names:
            remove(file)


    @mock.patch('geviewer.utils.prompt_for_window_size')
    def test_set_window_size(self, mocked_input):
        """Test the set_window_size method with a mocked window size input.
        """
        mocked_input.return_value = [800,600]
        self.gev.set_window_size()
        self.assertEqual(self.gev.plotter.window_size,[800,600])
    

    @mock.patch('geviewer.utils.prompt_for_camera_view')
    def test_set_camera_view(self, mocked_input):
        """Test the set_camera_view method with a mocked camera viewpoint input.
        """
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


    @mock.patch('geviewer.utils.prompt_for_html_path')
    def test_export_to_html(self, mocked_input):
        """Test the export_to_html method with a mocked file path input.
        """
        with tempfile.NamedTemporaryFile(suffix='.html') as temp:
            mocked_input.return_value = str(temp.name)
            self.gev.export_to_html()
            self.assertTrue(isfile(mocked_input.return_value))


    def test_save_and_load(self):
        """Test the save session method.
        """
        with tempfile.NamedTemporaryFile(suffix='.gev') as temp:
            with self.subTest():
                self.gev.save(str(temp.name))
                self.assertTrue(isfile(str(temp.name)))
            with self.subTest():
                gev = geviewer.GeViewer([str(temp.name)], off_screen=True)
                self.assertTrue(all([gev.actors[i].visibility for i in range(2)]))
    

if __name__ == '__main__':
    unittest.main()