# Changelog

## [v 0.0.8] - 2024-01-
- Identify zero folder with decimals and raises and exception if multiple valid zero folders are found
- Organize boundary probes in a single xarray

## [v 0.0.7] - 2024-01-18
- Partial refactoring of boundary_probe 

## [v 0.0.6] - 2024-01-18
- Drop StringIO buffer building short _repr_html_
- Add rough boundaryProbe management

## [v 0.0.5] - 2024-01-18
- Defaulting foamDictionary to -disableFunctionEntries option to avoid dynamicCode compilation

## [v 0.0.4] - 2024-01-17
- Add `_repr_html_` for nicer jupyter notebook visualization
- Update notebook examples

## [v 0.0.3] - 2024-01-17
- Add `__delitem__` method
- Add .foam file to case for vtk/pyvista hook

## [v 0.0.2] - 2024-01-16
- Initial useful release
- Implement getting and setting data for case directory
- Implement wrappers for running the application and getting simulated times 

## [v 0.0.1] - 2024-01-11
- Create package and initial release