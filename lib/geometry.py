# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import *


TOLERANCE = 0.001


def is_horizontal(line):
    """Retorna True se a linha for horizontal."""
    direction = line.Direction.Normalize()

    return (
        abs(direction.X) > (1 - TOLERANCE)
        and abs(direction.Y) < TOLERANCE
    )


def is_vertical(line):
    """Retorna True se a linha for vertical."""
    direction = line.Direction.Normalize()

    return (
        abs(direction.Y) > (1 - TOLERANCE)
        and abs(direction.X) < TOLERANCE
    )


def midpoint(line):
    """Retorna o ponto médio de uma linha."""
    p0 = line.GetEndPoint(0)
    p1 = line.GetEndPoint(1)

    return XYZ(
        (p0.X + p1.X) / 2,
        (p0.Y + p1.Y) / 2,
        (p0.Z + p1.Z) / 2,
    )


def offset_line(line, distance):
    """Cria uma linha paralela deslocada."""

    direction = line.Direction.Normalize()

    normal = XYZ(
        -direction.Y,
        direction.X,
        0
    )

    offset = normal * distance

    return Line.CreateBound(
        line.GetEndPoint(0) + offset,
        line.GetEndPoint(1) + offset
    )


def line_position(line):
    """Retorna uma coordenada usada para ordenar linhas."""

    m = midpoint(line)

    if orientation(line) == "horizontal":
        return m.Y

    return m.X


def min_point(points):
    """Retorna o ponto mínimo da lista."""

    return XYZ(
        min(p.X for p in points),
        min(p.Y for p in points),
        0
    )


def max_point(points):
    """Retorna o ponto máximo da lista."""

    return XYZ(
        max(p.X for p in points),
        max(p.Y for p in points),
        0
    )


def orientation(line):
    """Retorna 'horizontal' ou 'vertical'."""

    direction = line.Direction.Normalize()

    if abs(direction.X) >= abs(direction.Y):
        return "horizontal"

    return "vertical"
