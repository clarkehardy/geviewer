import pyvista as pv


class Plotter(pv.Plotter):
    '''
    Custom plotter class that overrides the default key events for the viewer.
    '''

    def geviewer_key_event(self, obj, event):
        '''
        This function is called when a key is pressed in the viewer.
        It overrides the default key events for the viewer, allowing
        only the custom key events defined in the GeViewer class.
        '''
        key = obj.GetInteractor().GetKeyCode()
        overriden_keys = ['c', 't', 'm', 'b', 'd', 'i', 'p', 'h',\
                          'w', 'e','+', '-', 's', 'r', 'u', 'f']
        if key in overriden_keys:
            return
        else:
            # commands for other keys are passed to the original key event handler
            obj.OnChar()


    def show(self, *args, **kwargs):
        '''
        Override the default key events and then show the plotter window.
        '''
        interactor_style = self.iren.interactor.GetInteractorStyle()
        interactor_style.AddObserver("CharEvent", self.geviewer_key_event)

        # now call the original show method
        super().show(*args, **kwargs)