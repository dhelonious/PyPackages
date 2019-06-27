Manage and use locally installed Python packages directly in Sublime Text 3

# PyPackages

[PEP 582](https://www.python.org/dev/peps/pep-0582/) proposes a mechanism to import Python packages from a local `__pypackages__` directory, which is a nice and consistent alternative to virtual environments. [pythonloc](https://github.com/cs01/pythonloc) provides an early prototype of this concept (see also [this article by the author](https://medium.com/@grassfedcode/goodbye-virtual-environments-b9f8115bc2b6)). PyPackages brings the same functionality directly to your Sublime Text 3!

This package provides commands to manage and use your local `__pypackages__` directory conveniently within Sublime Text 3. The Sublime Text environment is modified such that Python will import packages preferably from the `__pypackages__` directory in the project path. This allows for running any python build systems without modifications. This feature is even available in terminals opened by Sublime Text 3 (e. g. by the [Sublime Terminal](https://github.com/wbond/sublime_terminal) package), if the environment is passed correctly. If PEP 582 is accepted, Python will automatically look for packages in the local `__pypackages__` directory.

**Note:** PyPackages will only be available in projects. By default the `__pypackages__` directory will be located in the project root where the sublime-project file is located. However, the `__pypackages__` root directory can be configured with the key `"pypackages_root"` in the project settings.

## Quickstart

1. Install this package. This can be done conveniently by [adding this repository to Package Control](https://packagecontrol.io/docs/usage).
2. Create an awesome Python project or open an existing masterpiece.
3. Type `PyPackages: Enable` into the Sublime Text 3 command palette.

**Tip:** Enable the `"auto_toggle"` option. Then PyPackages will automatically enable and disable itself if a project with a local `__pypackages__` is focused.

## Commands

| Command                      | Description                                                                                                                                  |
| --                           | --                                                                                                                                           |
| `PyPackages:`<br>`Enable`    | Enable PyPackages in the current project. This enables the other PyPackages commands and modifies the Sublime Text 3 environment accordingly |
| `PyPackages:`<br>`Install`   | Install package into the local `__pypackages__` directory                                                                                    |
| `PyPackages:`<br>`Upgrade`   | Upgrade selected package in the local `__pypackages__` directory                                                                             |
| `PyPackages:`<br>`List`      | Show packages installed in the local `__pypackages__` directory                                                                              |
| `PyPackages:`<br>`Uninstall` | Remove packages from the local `__pypackages__` directory                                                                                    |
| `PyPackages:`<br>`freeze`    | Freeze the currently installed packages into a requirement file                                                                              |
| `PyPackages:`<br>`Disable`   | Disable PyPackages in the current project. This removes the changes made to the Sublime Text 3 environment                                   |

## Settings

| Key                   | Default    | Description                                                                                                                                                                                            |
| --                    | --         | --                                                                                                                                                                                                     |
| `"auto_toggle"`       | `false`    | Automatically enable PyPackages in projects with a local `__pypackages__` directory. If the focus switches to Windows without project or local `__pypackages__` directory, PyPackages will be disabled |
| `"python_executable"` | `"python"` | Specify the Python executable used on the current OS. Valid OS keys are`"linux"`, `"osx"`, and `"windows"`.                                                                                            |
| `"debug"`             | `false`    | Show additional debug information in the console                                                                                                                                                       |

### Project settings

The `__pypackages__` root directory can be set in the project file:
```json
{
    "folders": [
        {"path": "."}
    ],
    "settings": {
        "pypackages_root": "$project_path/python/"
    }
}
```

## Requirements:

* Sublime Text 3
* pip (version > 10)

## Acknowledgements

The following projects were very helpful for building this package:
* [pythonloc](https://github.com/cs01/pythonloc) by Chad Smith
* [list-target](https://gist.github.com/igniteflow/0b26441d3617dc344565) by Phil Tysoe
