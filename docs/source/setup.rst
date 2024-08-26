Setup
-----

Dependencies
~~~~~~~~~~~~

The following packages are required:

-  ``PyQt6``

-  ``pyvistaqt``

-  ``lxml``

-  ``tqdm``

Installation
~~~~~~~~~~~~

To ensure there are no conflicts with existing packages, it is
recommended that you install GeViewer in a new Python environment.

::

   python -m venv geviewer-env
   source geviewer-env/bin/activate

The GeViewer version 0.2.0 beta can then be installed using ``pip`` as
follows:

.. code:: bash

   pip install --pre geviewer

To avoid having to manually activate the environment each time you want
to launch GeViewer, you can add the following line to your ``.bashrc``
file:

.. code:: bash

   alias geviewer='/path/to/geviewer-env/bin/python /path/to/geviewer-env/bin/geviewer'

If you wish to uninstall GeViewer, you can use
``pip uninstall geviewer``, or you can simply delete the environment
containing the installation:

.. code:: bash

   rm -rf geviewer-env
