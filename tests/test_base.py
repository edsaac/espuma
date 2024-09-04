import os
from pathlib import Path
import pytest
from espuma import Case_Directory

FOAM_TUTORIALS = os.environ["FOAM_TUTORIALS"]
TEMPLATE = f"{FOAM_TUTORIALS}/incompressible/icoFoam/cavity/cavity"
PATH = Path("./tests/pytest_cavity_base")


def test_initialize():
    of_tpl = Case_Directory(TEMPLATE)
    assert str(of_tpl) == TEMPLATE

    global of_case
    of_case = Case_Directory.clone_from_template(of_tpl, PATH, overwrite=True)


def test_case_directory():
    assert of_case.path.samefile(PATH)
    assert of_case.zero.path.samefile(PATH / "0")
    assert of_case.system.path.samefile(PATH / "system")


def test_zero_directory():
    assert getattr(of_case.zero, "p")
    assert getattr(of_case.zero, "U")

    assert len(of_case.zero.files) == 2

    assert of_case.zero.p.path.samefile(PATH / "0/p")
    assert of_case.zero.U.path.samefile(PATH / "0/U")


def test_scalar_field():
    p = of_case.zero.p

    assert p["FoamFile.class"] == "volScalarField"

    assert str(p.dimensions) == "[0 2 -2 0 0 0 0]"
    assert str(p.internalField) == "uniform 0"
    assert all(
        i in p.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert p.boundaryField["fixedWalls"]["type"] == "zeroGradient"
    assert p.boundaryField["fixedWalls.type"] == "zeroGradient"


def test_vector_field():
    U = of_case.zero.U

    assert U["FoamFile.class"] == "volVectorField"

    assert str(U.dimensions) == "[0 1 -1 0 0 0 0]"
    assert str(U.internalField) == "uniform ( 0 0 0 )"
    assert all(
        i in U.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert U.boundaryField["fixedWalls"]["type"] == "noSlip"
    assert U.boundaryField["fixedWalls.type"] == "noSlip"


def test_constant_directory():
    constant = of_case.constant
    assert constant.path.samefile(PATH / "constant/")

    assert getattr(constant, "transportProperties")
    assert constant.transportProperties.path.samefile(
        PATH / "constant/transportProperties"
    )

    assert constant.transportProperties["FoamFile.class"] == "dictionary"
    assert constant.transportProperties["nu"] == "[ 0 2 -1 0 0 0 0 ] 0.01"


def test_system_directory():
    system = of_case.system
    assert system.path.samefile(PATH / "system/")

    assert getattr(system, "controlDict")
    assert system.controlDict.path.samefile(PATH / "system/controlDict")

    assert system.controlDict["FoamFile.class"] == "dictionary"
    assert system.controlDict["application"] == "icoFoam"
    assert system.controlDict["deltaT"] == "0.005"

    assert getattr(system, "fvSolution")
    assert system.fvSolution.path.samefile(PATH / "system/fvSolution")
    assert system.fvSolution["PISO"]["nCorrectors"] == "2"


def test_setters():
    fv_solution = of_case.system.fvSolution

    # An existing key
    assert fv_solution["solvers.p.solver"] == "PCG"

    fv_solution["solvers.p.solver"] = "banana"
    assert fv_solution["solvers.p.solver"] == "banana"

    fv_solution["solvers.p.solver"] = "PCG"
    assert fv_solution["solvers.p.solver"] == "PCG"

    # A whole new entry
    fv_solution["solvers.p.coconut"] = "coconut"
    assert fv_solution["solvers.p.coconut"] == "coconut"

    del fv_solution["solvers.p.coconut"]
    with pytest.raises(ValueError):
        fv_solution["solvers.p.coconut"]


def test_run_solver():
    ## If it's none, means that ended with code 0
    assert of_case._blockMesh() is None

    assert of_case.is_finished() is False

    ## If it's none, means that ended with code 0
    assert of_case._runCase() is None

    assert all(t in of_case.list_times for t in [0.1, 0.2, 0.3, 0.4, 0.5])

    assert of_case.is_finished() is True


def test_vtk_import():
    assert of_case.get_vtk_reader()
