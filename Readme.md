Manage and import Python packages stored in local directory

# Pythonloc

[PEP 582](https://www.python.org/dev/peps/pep-0582/) proposes a mechanism to import Python packages from a local `__pypackages__` directory. [pythonloc](https://github.com/cs01/pythonloc) provides an early prototype of this concept (see also [this article by the author](https://medium.com/@grassfedcode/goodbye-virtual-environments-b9f8115bc2b6)). This package aims to provide commands to manage and use your local `__pypackages__` directory conveniently within Sublime Text 3. The Sublime Text environment is modified such that Python will import packages preferably from the `__pypackages__` directory in the project path. This allows for running any python build systems without modifications.

**Note:** Pythonloc will only be available in projects. The `__pypackages__` directory will be located in the project root where the sublime-project file is located. However, the location of the `__pypackages__` directory might be configurable per project in the future.

## Quickstart

1. Install this package. This can be done conveniently by [adding this repository to Package Control](https://packagecontrol.io/docs/usage).
2. Create an awesome Python project or open an existing masterpiece.
3. Type `Pythonloc: Enable` into the Sublime Text 3 command palette.

**Tip:** Enable the `"auto_toggle"` option. Then Pythonloc will automatically enable and disable itself if a project with a local `__pypackages__` is focused.

## Commands

| Command                     | Description                                                                                                                                        |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Pythonloc:`<br>`Enable`    | Enable Pythonloc in the current project. This enables the other Pythonloc commands and modifies the Sublime Text 3 environment accordingly         |
| `Pythonloc:`<br>`Install`   | Install package into the local `__pypackages__` directory                                                                                          |
| `Pythonloc:`<br>`List`      | Show packages installed in the local `__pypackages__` directory                                                                                    |
| `Pythonloc:`<br>`Uninstall` | Remove packages from the local `__pypackages__` directory                                                                                          |
| `Pythonloc:`<br>`freeze`    | Freeze the currently installed packages into a requirement file                                                                                    |
| `Pythonloc:`<br>`Disable`   | Disable Pythonloc in the current project. This removes the changes made to the Sublime Text 3 environment                                          |

## Settings

| Key                     | Default      | Description                                                                                                                                                                                          |
| ----------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `"auto_toggle"`         | `false`      | Automatically enable Pythonloc in projects with a local `__pypackages__` directory. If the focus switches to Windows without project or local `__pypackages__` directory, Pythonloc will be disabled  |
| `"python_executable"`   | `"python"`   | Specify the Python executable used on the current OS. Valid OS keys are`"linux"`, `"osx"`, and `"windows"`.                                                                                           |
| `"debug"`               | `false`      | Show additional debug information in the console                                                                                                                                                     |

## Requirements:

* Sublime Text 3
* pip (version > 10)

## Acknowledgements

The following projects were very helpful for building this package:
* [pythonloc](https://github.com/cs01/pythonloc) by Chad Smith
* [list-target script](https://gist.github.com/igniteflow/0b26441d3617dc344565) by [igniteflow](https://gist.github.com/igniteflow)
