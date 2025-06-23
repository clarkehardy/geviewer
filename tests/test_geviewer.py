import unittest
from unittest import mock
import os
import tempfile
from geviewer import viewer, utils

class TestGeViewer(unittest.TestCase):

    def setUp(self):
        """Sets up the GeViewer object."""
        self.gev = viewer.GeViewer()

    def test_load_vrml_file(self):
        """Tests the load_file method with a VRML file."""
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        # geometry, step markers, and trajectories should have been loaded
        self.assertEqual(len(self.gev.components[0]['children']), 3)
        
    def test_load_heprep_file(self):
        """Tests the load_file method with a HepRep file."""
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        # geometry and events should have been loaded
        self.assertEqual(len(self.gev.components[0]['children']), 2)

    def test_save_file(self):
        """Tests the save and load methods."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            self.gev.save_session(os.path.join(temp_dir, 'sample.gev'))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'sample.gev')))
            self.gev.load_session(os.path.join(temp_dir, 'sample.gev'))
            self.assertEqual(len(self.gev.components[0]['children']), 3)

    def test_clear_meshes(self):
        """Tests the clear_meshes method."""
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.clear_meshes()
        self.assertEqual(len(self.gev.plotter.actors), 0)

    def test_find_overlaps(self):
        """Tests the find_overlaps method."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        # one overlap between two components
        self.assertEqual(len(self.gev.find_overlaps(tolerance=0.01, n_samples=10000)), 2)

    def test_count_components(self):
        """Tests the count_components method."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.assertEqual(self.gev.count_components(self.gev.components), 69)

    def test_create_plotter(self):
        """Tests the create_plotter method."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.gev.create_plotter()
        self.assertEqual(len(self.gev.plotter.actors), 53)

    def test_toggle_parallel_projection(self):
        """Tests the toggle_parallel_projection method."""
        self.gev.off_screen = True
        self.gev.toggle_parallel_projection()
        self.assertEqual(self.gev.plotter.camera.parallel_projection, True)

    def test_toggle_background(self):
        """Tests the toggle_background method."""
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_background()
        self.assertEqual(self.gev.plotter.background_color, 'white')

    def test_toggle_wireframe(self):
        """Tests the toggle_wireframe method."""
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_wireframe()
        self.assertEqual(self.gev.wireframe, True)

    def test_toggle_transparent(self):
        """Tests the toggle_transparent method."""
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_transparent()
        self.assertEqual(next(iter(self.gev.actors.values())).GetProperty().GetOpacity(), 0.3)

    def test_export_figure(self):
        """Tests the export figure method."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.gev.create_plotter()
        with tempfile.TemporaryDirectory() as temp_dir:
            exts = ['.png', '.jpeg', '.jpg', '.bmp', '.tif', '.tiff', '.svg', '.eps', '.ps', '.pdf', '.tex']
            for ext in exts:
                self.gev.export_figure(os.path.join(temp_dir, 'test_fig' + ext), \
                                        *self.gev.plotter.window_size)
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'test_fig' + ext)))

    def test_clipping(self):
        """Tests clipping."""
        self.gev.off_screen = True
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.gev.create_plotter()
        image_before = self.gev.export_figure(None, 100, 100)
        clipping_params = [0, 0, 0, 1e5, 1e5, 1e5, 0, 0, 1, 0]
        self.gev.clip_geometry(clipping_params, show=False)
        image_after = self.gev.export_figure(None, 100, 100)
        # check that the red geometry has been clipped away
        self.assertLess(image_after[:,:,0].sum(), image_before[:,:,0].sum())
        self.gev.clip_geometry(clipping_params, show=False, enabled=False)
        image_final = self.gev.export_figure(None, 100, 100)
        # check that the red geometry has been restored
        self.assertEqual(image_before[:,:,0].sum(), image_final[:,:,0].sum())

class TestUtils(unittest.TestCase):

    def test_get_license(self):
        """Tests the get_license function.
        """
        license_raw = utils.get_license()
        self.assertIn('MIT License', license_raw)

if __name__ == '__main__':
    unittest.main()
