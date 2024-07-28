import pyvista as pv

class Plotter(pv.Plotter):
    """
    A custom plotter class that extends `pyvista.Plotter` to provide
    enhanced key event handling.

    This class inherits from `pyvista.Plotter` and modifies key event
    handling to override specific key behaviors. Keys that are not overridden
    by this class will be passed to the original key event handler.

    :param args: Positional arguments to pass to the base class constructor.
    :param kwargs: Keyword arguments to pass to the base class constructor.

    Methods:
        - `geviewer_key_event`: Handles key press events and overrides specific key behaviors.
        - `show`: Displays the plotter window with custom key event handling.

    Inherited Methods:
        - `pyvista.Plotter.show`: Displays the plotter window.
    """

    def geviewer_key_event(self, obj, event):
        """Handles key press events to override specific key behaviors.

        This method intercepts key press events and checks if the key pressed
        is in the list of overridden keys. If it is, the method performs no
        action for these keys. For other keys, the method delegates the event
        to the original key event handler.

        :param obj: The VTK object that triggered the event.
        :type obj: vtkObject
        :param event: The event name (e.g., "CharEvent").
        :type event: str
        """
        key = obj.GetInteractor().GetKeyCode()
        overriden_keys = ['c', 't', 'm', 'b', 'd', 'i', 'p', 'h',\
                          'w', 'e', '+', '-', 's', 'r', 'u', 'f']
        if key in overriden_keys:
            return
        else:
            # Commands for other keys are passed to the original key event handler
            obj.OnChar()


    def show(self, *args, **kwargs):
        """Displays the plotter window with custom key event handling.

        This method overrides the `show` method from `pyvista.Plotter` to include
        custom key event handling. It first sets up an observer for key press events
        and then calls the base class `show` method to displaythe plotter window.

        :param args: Positional arguments passed to the base class `show` method.
        :param kwargs: Keyword arguments passed to the base class `show` method.
        """
        interactor_style = self.iren.interactor.GetInteractorStyle()
        interactor_style.AddObserver("CharEvent", self.geviewer_key_event)

        # Now call the original show method
        super().show(*args, **kwargs)
