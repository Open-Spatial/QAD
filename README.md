# QAD_QT6

Quantum Aided Design is a CAD-style tools plugin for QGIS. This repository is
the Open Spatial Qt6 / QGIS 4 fork of the original QAD plugin at
https://github.com/gam17/QAD.

## Status

This fork ports QAD for the QGIS 4.x / Qt6 runtime. The plugin metadata targets
QGIS 4.0 through 4.99.

## Installation

Install the `QAD_QT6` plugin folder into the active QGIS profile's Python plugin
directory, then enable QAD from the QGIS Plugin Manager.

For the current Open Spatial QGIS 4 profile, the plugin folder is typically:

```text
C:\Users\<user>\AppData\Roaming\QGIS\QGIS4\profiles\default\python\plugins\QAD_QT6
```

## Development

The checked-in generated UI/resource modules are rewritten to use `qgis.PyQt`
so they can be loaded inside the QGIS Python runtime. Use `compila_ui.bat` and
`compila_risorse.bat` to regenerate those files with `pyuic6` / `pyrcc6` when
available, with a fallback to the Qt5 tools if needed.

Package releases should include this repository root as the `QAD_QT6` plugin
directory and exclude local development workspace files.

## License

QAD is free software distributed under the GNU General Public License. The
original source headers generally state GPL version 2 or later, and this fork
includes the GNU GPL version 3 license text as a permitted later version. Keep
the upstream copyright notices, author credits, and GPL notices intact when
redistributing modified versions.

## Modification Notice

Open Spatial modified this fork for QGIS 4.x / Qt6 compatibility and packages
the plugin as `QAD_QT6`.

## Credits

Original QAD developers: gam17

User interface designers: gam17, em-rezende

Documentation: gam17

Testers: Aitor Gil (jaitor1), Gabriel De Luca, Tony Shepherd
