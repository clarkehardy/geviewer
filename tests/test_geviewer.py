import unittest
from unittest import mock
import os
import tempfile
from geviewer import viewer

class TestGeViewer(unittest.TestCase):

    def setUp(self):
        self.gev = viewer.GeViewer()

    def test_load_vrml_file(self):
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        # geometry, step markers, and trajectories should have been loaded
        self.assertEqual(len(self.gev.components[0]['children']), 3)
        
    def test_load_heprep_file(self):
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        # geometry and events should have been loaded
        self.assertEqual(len(self.gev.components[0]['children']), 2)

    def test_save_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.gev.clear_meshes()
            self.gev.load_file('tests/sample.wrl', off_screen=True)
            self.gev.save(os.path.join(temp_dir, 'sample.gev'))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'sample.gev')))
            self.gev.load(os.path.join(temp_dir, 'sample.gev'))
            self.assertEqual(len(self.gev.components[0]['children']), 3)

    def test_clear_meshes(self):
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.clear_meshes()
        self.assertEqual(len(self.gev.plotter.actors), 0)

    def test_find_overlaps(self):
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        # one overlap between two components
        self.assertEqual(len(self.gev.find_overlaps(tolerance=0.01, n_samples=10000)), 2)

    def test_count_components(self):
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.assertEqual(self.gev.count_components(self.gev.components), 69)

    def test_create_plotter(self):
        self.gev.clear_meshes()
        self.gev.load_file('tests/sample.heprep', off_screen=True)
        self.gev.create_plotter()
        self.assertEqual(len(self.gev.plotter.actors), 53)

    def test_toggle_parallel_projection(self):
        self.gev.toggle_parallel_projection()
        self.assertEqual(self.gev.plotter.camera.parallel_projection, True)

    def test_toggle_background(self):
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_background()
        self.assertEqual(self.gev.plotter.background_color, 'white')

    def test_toggle_wireframe(self):
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_wireframe()
        self.assertEqual(self.gev.wireframe, True)

    def test_toggle_transparent(self):
        self.gev.load_file('tests/sample.wrl', off_screen=True)
        self.gev.create_plotter()
        self.gev.toggle_transparent()
        self.assertEqual(next(iter(self.gev.actors.values())).GetProperty().GetOpacity(), 0.3)

if __name__ == '__main__':
    unittest.main()
