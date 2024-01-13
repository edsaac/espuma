from espuma.base import Case_Directory

PATH = "/home/edsaa/cavity"
d = Case_Directory(PATH)


def test_case_directory():
    assert str(d) == PATH


def test_zero_directory():
    assert str(d.zero) == f"{PATH}/0"

    assert getattr(d.zero, "p")
    assert getattr(d.zero, "U")

    assert f"{PATH}/0/p" in d.zero.files
    assert f"{PATH}/0/U" in d.zero.files
    assert len(d.zero.files) == 2


def test_scalar_field():
    p = d.zero.p
    assert str(p) == f"{PATH}/0/p"
    assert p.FoamFile["class"] == "volScalarField"

    assert str(p.dimensions) == "[0 2 -2 0 0 0 0]"
    assert str(p.internalField) == "uniform 0"
    assert all(
        i in p.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert p.boundaryField["fixedWalls"]["type"] == "zeroGradient"


def test_vector_field():
    U = d.zero.U
    assert str(U) == f"{PATH}/0/U"
    assert U.FoamFile["class"] == "volVectorField"

    assert str(U.dimensions) == "[0 1 -1 0 0 0 0]"
    assert str(U.internalField) == "uniform ( 0 0 0 )"
    assert all(
        i in U.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert U.boundaryField["fixedWalls"]["type"] == "noSlip"

def test_constant_directory():
    constant = d.constant
    assert str(constant) == f"{PATH}/constant"

    assert str(constant.transportProperties) == f"{PATH}/constant/transportProperties"
    assert constant.transportProperties.FoamFile["class"] == "dictionary"

    assert constant.transportProperties["nu"] == "[ 0 2 -1 0 0 0 0 ] 0.01"

def test_system_directory():
    system = d.system
    assert str(system) == f"{PATH}/system"

    assert str(system.controlDict) == f"{PATH}/system/controlDict"
    assert system.controlDict.FoamFile["class"] == "dictionary"
    assert system.controlDict["application"] == "icoFoam"
    assert system.controlDict["deltaT"] == "0.005"

    assert str(system.fvSolution) == f"{PATH}/system/fvSolution"
    assert system.fvSolution["PISO"]["nCorrectors"] == "2"