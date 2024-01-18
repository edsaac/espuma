from pathlib import Path
import xarray as xr
import numpy as np
import os
import subprocess
from dataclasses import dataclass

from . import Case_Directory


@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float
    z: float


class boundaryProbe:
    """
    Assumes that the contents of postProcessing probes have been parsed already
    with pointFiles.sh
    """

    def __init__(
        self, path_data: str | Path, path_time: str | Path, path_xyz: str | Path
    ):
        self.path_data = Path(path_data)
        self.path_time = Path(path_time)
        self.path_xyz = Path(path_xyz)

    @property
    def field_names(self):
        ## Get the number of probed fields
        return self.path_data.stem.replace("points_", "").split("_")

    @property
    def n_fields(self):
        return len(self.field_names)

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
        """Should be n_probes * n_fields * (1 or 3)"""
        with open(self.path_data) as f:
            first_line = f.readline().split()
            n_cols = len(first_line)

        if n_cols == self.n_probes * self.n_fields:
            return "scalar"
        elif n_cols == 3 * self.n_probes * self.n_fields:
            return "vector"
        else:
            raise RuntimeError("Field is neither vector nor scalar.")

    @property
    def times(self):
        return np.loadtxt(self.path_time)

    @property
    def array_data(self):
        full_data = np.loadtxt(self.path_data).T

        data = dict()

        if self.dimensionality == "scalar":
            field_names_for_parsing = self.field_names
            dimension_number = 1

        elif self.dimensionality == "vector":
            field_names_for_parsing = [
                f"{field}{dim}" for field in self.field_names for dim in [*"xyz"]
            ]
            dimension_number = 3

        for i, field in enumerate(field_names_for_parsing):
            data[field] = xr.DataArray(
                full_data[i :: self.n_fields * dimension_number],
                dims=("probes", "time"),
                coords={"probes": self.probe_points, "time": self.times},
            )

        return xr.Dataset(
            data, coords={"time": self.times, "probes": self.probe_points}
        )

    def _repr_html_(self):
        return self.array_data._repr_html_()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path_data.name})"


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


def process_boundaryProbes(of_case: Case_Directory):
    """
    Read the processed boundaryProbes and parse them in xarrays

    """
    _boundaryProbes_to_txt(of_case)

    processed_probes_path = of_case.path / "postProcessing/espuma_BoundaryProbes/"
    files = processed_probes_path.glob("points_*")
    f_time = processed_probes_path / "time.txt"
    f_xyz = processed_probes_path / "xyz.txt"

    return {f.name: boundaryProbe(f, f_time, f_xyz) for f in files}


def main():
    pass


if __name__ == "__main__":
    main()
