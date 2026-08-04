# -*- coding: utf-8 -*-

"""Funções geométricas auxiliares para cotas de eixos no Revit."""

from Autodesk.Revit.DB import Line, XYZ


TOLERANCE = 0.001


def _validate_line(line):
    """Valida se o objeto recebido é uma linha reta do Revit."""
    if line is None or not isinstance(line, Line):
        raise ValueError("Era esperada uma Autodesk.Revit.DB.Line.")


def is_horizontal(line, tolerance=TOLERANCE):
    """Retorna True quando a linha é paralela ao eixo X do modelo."""
    _validate_line(line)
    direction = line.Direction.Normalize()

    return (
        abs(direction.X) >= (1.0 - tolerance)
        and abs(direction.Y) <= tolerance
    )


def is_vertical(line, tolerance=TOLERANCE):
    """Retorna True quando a linha é paralela ao eixo Y do modelo."""
    _validate_line(line)
    direction = line.Direction.Normalize()

    return (
        abs(direction.Y) >= (1.0 - tolerance)
        and abs(direction.X) <= tolerance
    )


def midpoint(line):
    """Retorna o ponto médio de uma linha limitada."""
    _validate_line(line)

    p0 = line.GetEndPoint(0)
    p1 = line.GetEndPoint(1)

    return XYZ(
        (p0.X + p1.X) / 2.0,
        (p0.Y + p1.Y) / 2.0,
        (p0.Z + p1.Z) / 2.0
    )


def offset_line(line, distance):
    """Cria uma linha paralela deslocada no plano XY."""
    _validate_line(line)

    direction = line.Direction.Normalize()
    normal = XYZ(-direction.Y, direction.X, 0.0).Normalize()
    offset = normal.Multiply(distance)

    return Line.CreateBound(
        line.GetEndPoint(0).Add(offset),
        line.GetEndPoint(1).Add(offset)
    )


def orientation(line, tolerance=TOLERANCE):
    """
    Retorna ``horizontal`` ou ``vertical`` para linhas ortogonais.

    Linhas diagonais retornam ``None`` para não serem classificadas
    incorretamente como um eixo horizontal ou vertical.
    """
    if is_horizontal(line, tolerance):
        return "horizontal"

    if is_vertical(line, tolerance):
        return "vertical"

    return None


def line_position(line):
    """Retorna a coordenada perpendicular usada para ordenar linhas."""
    line_orientation = orientation(line)

    if line_orientation is None:
        raise ValueError("A linha não é horizontal nem vertical.")

    point = midpoint(line)

    if line_orientation == "horizontal":
        return point.Y

    return point.X


def min_point(points):
    """Retorna as menores coordenadas X, Y e Z de uma coleção de pontos."""
    points = list(points)

    if not points:
        raise ValueError("A coleção de pontos está vazia.")

    return XYZ(
        min(point.X for point in points),
        min(point.Y for point in points),
        min(point.Z for point in points)
    )


def max_point(points):
    """Retorna as maiores coordenadas X, Y e Z de uma coleção de pontos."""
    points = list(points)

    if not points:
        raise ValueError("A coleção de pontos está vazia.")

    return XYZ(
        max(point.X for point in points),
        max(point.Y for point in points),
        max(point.Z for point in points)
    )
