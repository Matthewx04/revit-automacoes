# -*- coding: utf-8 -*-

"""Criação de cotas lineares para eixos (grids) no Revit."""

from Autodesk.Revit.DB import (
    Line,
    Reference,
    ReferenceArray,
    Transaction,
    XYZ
)

from geometry import orientation
from grids import get_grid_curve, sort_grids


# Unidade interna do Revit: pés. 0.5 pé equivale a aproximadamente 152,4 mm.
DEFAULT_OFFSET = 0.5


def create_reference_array(grids):
    """Cria um ReferenceArray com referências de elementos Grid."""
    references = ReferenceArray()
    valid_grids = []
    errors = []

    for grid in grids:
        try:
            # Grid não possui GetReference(). A referência do datum é criada
            # diretamente a partir do elemento.
            reference = Reference(grid)
            references.Append(reference)
            valid_grids.append(grid)
        except Exception as error:
            errors.append((grid, error))

    return references, valid_grids, errors


def _collect_endpoints(grids, view):
    """Coleta os pontos finais das curvas visíveis dos grids."""
    points = []

    for grid in grids:
        curve = get_grid_curve(grid, view)

        if curve is None:
            continue

        points.append(curve.GetEndPoint(0))
        points.append(curve.GetEndPoint(1))

    return points


def create_dimension_line(grids, view, offset=DEFAULT_OFFSET):
    """
    Cria a linha perpendicular aos grids onde a cota será posicionada.

    Grids horizontais recebem uma linha de cota vertical; grids verticais
    recebem uma linha de cota horizontal.
    """
    if view is None:
        raise ValueError("A vista não foi informada.")

    if grids is None or len(grids) < 2:
        raise ValueError("São necessários pelo menos dois grids.")

    first_curve = get_grid_curve(grids[0], view)

    if first_curve is None:
        raise ValueError("Não foi possível obter a curva do primeiro grid.")

    grid_orientation = orientation(first_curve)

    if grid_orientation is None:
        raise ValueError("Os grids devem ser horizontais ou verticais.")

    points = _collect_endpoints(grids, view)

    if len(points) < 4:
        raise ValueError("Não há geometria suficiente para criar a cota.")

    min_x = min(point.X for point in points)
    max_x = max(point.X for point in points)
    min_y = min(point.Y for point in points)
    max_y = max(point.Y for point in points)
    z = sum(point.Z for point in points) / float(len(points))

    if grid_orientation == "horizontal":
        # Grids horizontais variam em Y; a cota precisa ser vertical.
        dimension_x = min_x - offset
        start = XYZ(dimension_x, min_y - offset, z)
        end = XYZ(dimension_x, max_y + offset, z)
    else:
        # Grids verticais variam em X; a cota precisa ser horizontal.
        dimension_y = min_y - offset
        start = XYZ(min_x - offset, dimension_y, z)
        end = XYZ(max_x + offset, dimension_y, z)

    if start.DistanceTo(end) <= 1.0e-9:
        raise ValueError("A linha de cota calculada possui comprimento nulo.")

    return Line.CreateBound(start, end)


def create_dimension(doc, view, line, references):
    """Cria uma dimensão linear na vista informada."""
    if doc is None or view is None:
        raise ValueError("Documento e vista são obrigatórios.")

    if line is None:
        raise ValueError("A linha de cota não foi informada.")

    if references is None or references.Size < 2:
        raise ValueError("A cota exige pelo menos duas referências.")

    return doc.Create.NewDimension(view, line, references)


def create_grid_dimension(doc, view, grids, offset=DEFAULT_OFFSET):
    """
    Ordena os grids, cria as referências, a linha e a dimensão.

    Abre uma transação somente quando o documento ainda não está modificável,
    permitindo que a função também seja usada dentro de uma transação externa.
    """
    if grids is None or len(grids) < 2:
        return None

    ordered_grids = sort_grids(grids, view)

    if len(ordered_grids) < 2:
        return None

    references, valid_grids, errors = create_reference_array(ordered_grids)

    if references.Size < 2:
        error_text = "; ".join(
            "{0}: {1}".format(getattr(grid, "Name", "Grid"), error)
            for grid, error in errors
        )
        raise ValueError(
            "Não foi possível obter duas referências de grids. {0}".format(
                error_text
            )
        )

    dimension_line = create_dimension_line(valid_grids, view, offset)

    transaction = None

    try:
        if not doc.IsModifiable:
            transaction = Transaction(doc, "Criar cota de eixos")
            transaction.Start()

        dimension = create_dimension(
            doc,
            view,
            dimension_line,
            references
        )

        if transaction is not None:
            transaction.Commit()

        return dimension

    except Exception:
        if transaction is not None and transaction.HasStarted():
            transaction.RollBack()
        raise
