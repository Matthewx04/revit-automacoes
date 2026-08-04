# -*- coding: utf-8 -*-

"""Coleta, classificação e ordenação de eixos (grids)."""

from Autodesk.Revit.DB import (
    DatumExtentType,
    FilteredElementCollector,
    Grid,
    Line
)

from geometry import orientation, line_position


def get_grids(doc, view):
    """Retorna todos os grids visíveis na vista informada."""
    if doc is None:
        raise ValueError("O documento não foi informado.")

    if view is None:
        raise ValueError("A vista não foi informada.")

    return list(
        FilteredElementCollector(doc, view.Id)
        .OfClass(Grid)
        .WhereElementIsNotElementType()
        .ToElements()
    )


def get_grid_curve(grid, view=None):
    """
    Retorna a curva reta que representa o grid.

    Quando uma vista é fornecida, prioriza a extensão específica da vista e
    usa a extensão do modelo como alternativa. Grids em arco retornam None.
    """
    if grid is None:
        return None

    if view is not None:
        extent_types = (
            DatumExtentType.ViewSpecific,
            DatumExtentType.Model
        )

        for extent_type in extent_types:
            try:
                curves = list(grid.GetCurvesInView(extent_type, view))
            except Exception:
                curves = []

            for curve in curves:
                if isinstance(curve, Line):
                    return curve

    try:
        curve = grid.Curve
    except Exception:
        return None

    if isinstance(curve, Line):
        return curve

    return None


def split_grids(grids, view=None):
    """
    Separa os grids retos em horizontais, verticais e ignorados.

    O terceiro grupo contém grids curvos ou não ortogonais.
    """
    horizontais = []
    verticais = []
    ignorados = []

    for grid in grids:
        curve = get_grid_curve(grid, view)

        if curve is None:
            ignorados.append(grid)
            continue

        grid_orientation = orientation(curve)

        if grid_orientation == "horizontal":
            horizontais.append(grid)
        elif grid_orientation == "vertical":
            verticais.append(grid)
        else:
            ignorados.append(grid)

    return horizontais, verticais, ignorados


def sort_grids(grids, view=None):
    """Ordena grids pela coordenada perpendicular à sua direção."""
    valid_grids = []

    for grid in grids:
        curve = get_grid_curve(grid, view)

        if curve is not None and orientation(curve) is not None:
            valid_grids.append(grid)

    return sorted(
        valid_grids,
        key=lambda grid: line_position(get_grid_curve(grid, view))
    )
