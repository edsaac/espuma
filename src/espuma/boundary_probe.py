import xarray as xr
import numpy as np
from dataclasses import dataclass

import csv
from itertools import chain
from io import StringIO
from re import findall

from . import Case_Directory
from .base import Dict_File


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

    def __init__(
        self,
        of_case: Case_Directory,
        probe_dict: Dict_File,
        parser_kwargs: dict | None = None,
    ):
        ## Generate organized files
        if parser_kwargs is None:
            parser_kwargs = {}

        _boundaryProbes_to_txt(of_case, **parser_kwargs)

        ##
        processed_probes_path = of_case.path / "postProcessing/espuma_BoundaryProbes/"
        self.path_data = list(processed_probes_path.glob("points_*"))
        self.path_time = processed_probes_path / "time.txt"
        self.path_xyz = processed_probes_path / "xyz.txt"

        self._id = str(processed_probes_path.relative_to(of_case.path))

        ## Currently assuming raw format
        # TODO: Add functionality for CSV and VTK
        self._format = probe_dict["setFormat"].strip()
        self._fields_expression = probe_dict["fields"].strip()

    @property
    def field_names(self):
        return list(chain.from_iterable(self._field_names))

    @property
    def _field_names(self):
        names = []
        for f in self.path_data:
            if "*" not in self._fields_expression:
                ## Probably not a regex
                names.append(f.stem.replace("points_", "").split("_"))

            else:
                ## It was some OpenFOAM regexpr
                available = f.stem
                pattern = self._fields_expression
                pattern = "_" + pattern.replace('"', "").replace("*", "*?").replace(
                    " ", ""
                )
                names.append(findall(pattern, available))
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
                    f"{field}{dim}"
                    for field in self._field_names[nf]
                    for dim in [*"xyz"]
                ]
                dimension_number = 3

            for i, field in enumerate(field_names_for_parsing):
                data[field] = xr.DataArray(
                    full_data[i :: len(self._field_names[nf]) * dimension_number]
                    if len(field_names_for_parsing) > 1
                    else [full_data],
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
            + "<dd>"
            + ", ".join(self.field_names)
            + "</dd>\n"
            + "<dt><i>Probes:</i></dt>\n"
            + "<dd>"
            + ", ".join([str(p) for p in self.probe_points])
            + "</dd>\n"
            + f"<dt><i>Times:</i></dt>\n<dd>From {self.times[0]} to {self.times[-1]} in {len(self.times)} steps</dd>\n</dl>"
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id})"


def _boundaryProbes_to_txt(of_case: Case_Directory, **parser_kwargs):
    """
    Parse the probe data into single files. The following files are created:
            - time.txt
            - xyz.txt
            - points_<fields>.xy

    Parameters
    ----------
    None

    Returns
    -------
    None

    """

    bprbs = of_case.path / "postProcessing/boundaryProbes"
    outbprs = of_case.path / "postProcessing/espuma_BoundaryProbes"

    if not bprbs.exists():
        raise FileNotFoundError("{bprbs.name} does not exist. Nothing to parse")

    if parser_kwargs.get("rebuild", False) or not outbprs.exists():
        if not outbprs.exists():
            outbprs.mkdir()

        ## Write times file
        times = [x for x in bprbs.iterdir() if x.is_dir()]
        times.sort(key=lambda x: float(x.name))

        with open(outbprs / "time.txt", "w") as out:
            out.writelines([str(t.name) + "\n" for t in times])

        ## Write probe locations
        sample = next(times[1].iterdir())  ## Grab a sample
        with open(outbprs / "xyz.txt", "w") as out:
            with open(sample) as f:
                for line in f:
                    coords = line.split()[:3]
                    out.write(" ".join(coords) + "\n")

        ## Write the data file
        vars = [f.name for f in times[1].iterdir()]
        for var in vars:
            with StringIO() as buffer:
                for t in times:
                    with open(t / var) as f:
                        r = csv.reader(f, delimiter="\t")
                        r = (y[3:] for y in list(r))  ## Gets rid of first three columns
                        r = chain.from_iterable(r)  ## Make single row
                        r = " ".join(r).replace(
                            "  ", " "
                        )  ## Format single space separation
                        buffer.write(r + "\n")

                with open(outbprs / var, "w") as f:
                    f.write(buffer.getvalue())

    else:
        print("postProcessing/espuma_BoundaryProbes already exists.")


def main():
    pass


if __name__ == "__main__":
    main()
