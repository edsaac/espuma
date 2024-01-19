from pathlib import Path
import xarray as xr
import numpy as np
import os
import subprocess
from dataclasses import dataclass
from itertools import chain

from . import Case_Directory


@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float
    z: float


class Boundary_Probe:
    """
    Assumes that the contents of postProcessing probes have been parsed already
    with pointFiles.sh
    """

    def __init__(self, of_case: Case_Directory):
        
        ## Generate organized files
        _boundaryProbes_to_txt(of_case)

        ## 
        processed_probes_path = of_case.path / "postProcessing/espuma_BoundaryProbes/"
        self.path_data = list(processed_probes_path.glob("points_*"))
        self.path_time = processed_probes_path / "time.txt"
        self.path_xyz = processed_probes_path / "xyz.txt"

        self._id = str(processed_probes_path.relative_to(of_case.path))
        
    @property
    def field_names(self):
        return list(chain.from_iterable(self._field_names))

    @property
    def _field_names(self):
        names = []
        for f in self.path_data:
            names.append(f.stem.replace("points_", "").split("_"))
        return names

    @property
    def _n_fields(self):
        return [len(field_name) for field_name in self._field_names]

    @property
    def n_fields(self):
        return sum(self._n_fields)

    @property
    def probe_points(self):
        with open(self.path_xyz) as f:
            xyz = f.readlines()
            xyz = [list(map(float, line.split())) for line in xyz]

        return [Point(*p) for p in xyz]

    @property
    def n_probes(self):
        return len(self.probe_points)

    @property
    def dimensionality(self):
        
        dims = [] 

        for nf, data in enumerate(self.path_data):
        
            with open(data) as f:
                first_line = f.readline().split()
                n_cols = len(first_line)

            if n_cols == self.n_probes * self._n_fields[nf]:
                dims.append("scalar")
            elif n_cols == 3 * self.n_probes * self._n_fields[nf]:
                dims.append("vector")
            else:
                raise RuntimeError("Field is neither vector nor scalar.")
        
        return dims

    @property
    def times(self):
        return np.loadtxt(self.path_time)

    @property
    def array_data(self):

        data = dict()

        for nf, file_data in enumerate(self.path_data):

            full_data = np.loadtxt(file_data).T

            if self.dimensionality[nf] == "scalar":
                field_names_for_parsing = self._field_names[nf]
                dimension_number = 1

            elif self.dimensionality[nf] == "vector":
                field_names_for_parsing = [
                    f"{field}{dim}" for field in self._field_names[nf] for dim in [*"xyz"]
                ]
                dimension_number = 3

            for i, field in enumerate(field_names_for_parsing):
                data[field] = xr.DataArray(
                    full_data[i :: len(self._field_names[nf]) * dimension_number],
                    dims=("probes", "time"),
                    coords={"probes": self.probe_points, "time": self.times},
                )

        return xr.Dataset(
            data, coords={"time": self.times, "probes": self.probe_points}
        )

    def _repr_html_(self):
        return (
            f"<b>{self.__repr__()}</b><br>"
            "<dl>\n"
            + "<dt><i>Fields:</i></dt>\n" 
            + "<dd>" + ", ".join(self.field_names)  + "</dd>\n"
            + "<dt><i>Probes:</i></dt>\n" 
            + "<dd>" + ", ".join([str(p) for p in self.probe_points]) + "</dd>\n"
            + f"<dt><i>Times:</i></dt>\n<dd>From {self.times[0]} to {self.times[-1]} </dd>\n</dl>"
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id})"


def _boundaryProbes_to_txt(of_case: Case_Directory):
    """
    Run pointFiles.sh on the case to parse the probe data into single files

    Parameterss
    ----------
    None

    Returns
    -------
    None

        The following files are created:
            - time.txt
            - xyz.txt
            - $field.xy
    """
    if not (of_case.path / "postProcessing/espuma_BoundaryProbes").exists():

        if "ESPUMA_SCRIPTS" in os.environ and os.name == "posix":
            script_path = str(Path(os.environ["ESPUMA_SCRIPTS"]) / "pointFiles.sh")

            ## Allow permisions
            subprocess.run(["chmod", "a+x", script_path])

            command = [
                script_path,
                str(of_case.path / "postProcessing/boundaryProbes"),
                str(of_case.path / "postProcessing/espuma_BoundaryProbes"),
            ]

            value = subprocess.run(command, cwd=of_case.path)

            if value.returncode != 0:
                raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

            print(" ".join(command) + " finished successfully!")

    else:
        print("postProcessing/espuma_BoundaryProbes already exists.")

def main():
    pass


if __name__ == "__main__":
    main()
