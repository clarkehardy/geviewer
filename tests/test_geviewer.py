import unittest
from unittest import mock
import tempfile
from os.path import isfile
from geviewer import main, geviewer


class TestGeViewerMain(unittest.TestCase):

    def setUp(self):
        '''
        Create a GeViewer object.
        '''
        self.gev = geviewer.GeViewer('tests/sample.wrl',off_screen=True)


    def test_print_instructions(self):
        '''
        Test the print_instructions function.
        '''
        main.print_instructions()


    def test_key_inputs(self):
        '''
        Test the key inputs for the GeViewer object.
        '''
        for i in range(2):
            with self.subTest():
                track_status = self.gev.visible[0]
                self.gev.toggle_tracks()
                track_actors = self.gev.actors[:self.gev.counts[0]]
                self.assertTrue(all([a.visibility!=track_status for a in track_actors]))
            with self.subTest():
                hit_status = self.gev.visible[2]
                self.gev.toggle_hits()
                hit_actors = self.gev.actors[sum(self.gev.counts[:1]):sum(self.gev.counts[:2])]
                self.assertTrue(all([a.visibility!=hit_status for a in hit_actors]))
            with self.subTest():
                colors = ['lightskyblue','white']
                bkg_status = self.gev.bkg_on
                self.gev.toggle_background()
                self.assertEqual(self.gev.plotter.background_color,colors[bkg_status])


    @mock.patch.object(geviewer.GeViewer,'prompt_for_file_path')
    def test_save_screenshot(self,mocked_input):
        '''
        Test the save_screenshot method with a mocked file name input.
        '''
        file_names = [tempfile.mkstemp(suffix='.png')[1]]
        mocked_input.side_effect = file_names
        self.gev.save_screenshot()
        self.assertTrue(isfile(file_names[0]))


    @mock.patch.object(geviewer.GeViewer,'prompt_for_file_path')
    def test_save_graphic(self,mocked_input):
        '''
        Test the save_graphic method with mocked file name inputs.
        '''
        file_names = [tempfile.mkstemp(suffix='.svg')[1],\
                      tempfile.mkstemp(suffix='.eps')[1],\
                      tempfile.mkstemp(suffix='.ps')[1],\
                      tempfile.mkstemp(suffix='.pdf')[1],\
                      tempfile.mkstemp(suffix='.tex')[1]]
        mocked_input.side_effect = file_names
        self.gev.save_graphic()
        for i in mocked_input.side_effect:
            with self.subTest():
                self.assertTrue(isfile(i))


    @mock.patch.object(geviewer.GeViewer,'prompt_for_window_size',return_value=[800,600])
    def test_set_window_size(self,mocked_input):
        '''
        Test the set_window_size method with a mocked window size input.
        '''
        self.gev.set_window_size()
        self.assertEqual(self.gev.plotter.window_size,[800,600])
    

if __name__ == '__main__':
    unittest.main()