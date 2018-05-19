author: rami yankelov

***
summary:
-----------
this is an example of blender operator that is coupled with blender instance but has independent GUI (Tkinter-based in this example),
unlike the usual blender operator extensions that are meant to be accessed from blender GUI itself.
in its basis, the idea is to add a break in the main blender thread execution and execute delegated methods inside that break, this way making the blender environment
accessible to them.

note this is just sample of a single projoect component, not the full project. multiple pre-requisites and configurations are required for the full project.
the purpose is demonstration only.

in addition, few function examples are added, to demonstrate how to control and design the independet gui of the operator.
more general-purpose blender functions can be found in classes.SceneController.

blender version 2.78
python 3.6
***