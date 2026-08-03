# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    Grid
)

from geometry import (
    orientation,
    line_position
)


def get_grids(doc, view):
    """
    Retorna todos os grids visíveis na vista ativa.
    """

    return list(
        FilteredElementCollector(doc, view.Id)
        .OfClass(Grid)
        .WhereElementIsNotElementType()
    )


def split_grids(grids):
    """
    Separa os grids em horizontais e verticais.
    """

    horizontais = []
    verticais = []

    for grid in grids:

        curve = grid.Curve

        if orientation(curve) == "horizontal":
            horizontais.append(grid)
        else:
            verticais.append(grid)

    return horizontais, verticais


def sort_grids(grids):
    """
    Ordena os grids pela posição.
    """

    return sorted(
        grids,
        key=lambda g: line_position(g.Curve)
    )