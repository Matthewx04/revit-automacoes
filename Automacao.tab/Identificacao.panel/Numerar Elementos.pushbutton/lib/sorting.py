# -*- coding: utf-8 -*-

"""
sorting.py

Responsável por ordenar elementos do Revit de acordo com
a posição deles na vista/modelo.

Direções disponíveis:
- left_to_right
- right_to_left
- top_to_bottom
- bottom_to_top
"""

from pyrevit import DB


def get_element_point(element):
    """
    Retorna um ponto representativo do elemento.

    FamilyInstance / elementos pontuais:
        usa LocationPoint.

    Elementos lineares:
        usa o ponto médio da LocationCurve.

    Se não existir Location válida:
        tenta usar o centro da BoundingBox.
    """

    location = element.Location

    # Elemento baseado em ponto
    if isinstance(location, DB.LocationPoint):
        return location.Point

    # Elemento baseado em linha/curva
    if isinstance(location, DB.LocationCurve):
        curve = location.Curve

        try:
            return curve.Evaluate(0.5, True)
        except Exception:
            pass

    # Fallback usando BoundingBox
    try:
        bbox = element.get_BoundingBox(None)

        if bbox:
            return DB.XYZ(
                (bbox.Min.X + bbox.Max.X) / 2.0,
                (bbox.Min.Y + bbox.Max.Y) / 2.0,
                (bbox.Min.Z + bbox.Max.Z) / 2.0
            )

    except Exception:
        pass

    return None


def sort_left_to_right(elements):
    """
    Ordena da esquerda para a direita.
    """

    return sorted(
        elements,
        key=lambda element: get_element_point(element).X
    )


def sort_right_to_left(elements):
    """
    Ordena da direita para a esquerda.
    """

    return sorted(
        elements,
        key=lambda element: get_element_point(element).X,
        reverse=True
    )


def sort_top_to_bottom(elements):
    """
    Ordena de cima para baixo.
    """

    return sorted(
        elements,
        key=lambda element: get_element_point(element).Y,
        reverse=True
    )


def sort_bottom_to_top(elements):
    """
    Ordena de baixo para cima.
    """

    return sorted(
        elements,
        key=lambda element: get_element_point(element).Y
    )


def sort_elements(elements, direction="left_to_right"):
    """
    Função principal utilizada pelo script.py.

    Parameters
    ----------
    elements : list
        Elementos que serão ordenados.

    direction : str
        Direção da ordenação.

        Opções:
            left_to_right
            right_to_left
            top_to_bottom
            bottom_to_top

    Returns
    -------
    list
        Lista ordenada de elementos.
    """

    if not elements:
        return []

    # Remove elementos sem localização válida
    valid_elements = [
        element
        for element in elements
        if get_element_point(element) is not None
    ]

    if direction == "left_to_right":
        return sort_left_to_right(valid_elements)

    elif direction == "right_to_left":
        return sort_right_to_left(valid_elements)

    elif direction == "top_to_bottom":
        return sort_top_to_bottom(valid_elements)

    elif direction == "bottom_to_top":
        return sort_bottom_to_top(valid_elements)

    else:
        raise ValueError(
            "Direcao de ordenacao invalida: {}".format(direction)
        )