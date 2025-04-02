# Changelog
## [v 0.0.15] - 2025-04-02
- Add `export_to_xarray` method to export results of a line probeas a single xarray dataset
- Use `shlex.split` to parse shell commands in clone_from_template

## [v 0.0.14] - 2024-09-04
- `BoundaryProbe` supports CVS format. Raw format dropped.
- Add `BoundaryProbe` tests.

## [v 0.0.13] - 2024-02-01
- Boundary probe bug 

## [v 0.0.12] - 2024-01-29
- Some type hints
- BoundaryProbe checks if data was processed before and it is stored
in the espuma postprocessing folder.  

## [v 0.0.11] - 2024-01-25
- Set regex identification as `*` present
- Encapsulate data in list if BoundaryProbe only probes a single field.
- Add template and example of column breakthrough curve
- Fix bug in Directory class skipping path validation

## [v 0.0.10] - 2024-01-24
- Add fix to partially deal regex boundary probes (issue #1)

## [v 0.0.9] - 2024-01-19
- Add example based on damBreak tutorial
- Add setFields command 
- Rewrite postProcessing sh script parser in python

## [v 0.0.8] - 2024-01-19
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