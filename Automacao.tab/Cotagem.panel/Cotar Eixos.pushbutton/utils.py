# -*- coding: utf-8 -*-

"""Utilitários gerais para ferramentas pyRevit de cotas de eixos."""

from Autodesk.Revit.DB import UnitUtils, UnitTypeId, ViewType


# Tipos de vista normalmente adequados para cotas lineares de grids.
SUPPORTED_VIEW_TYPES = (
    ViewType.FloorPlan,
    ViewType.CeilingPlan,
    ViewType.EngineeringPlan,
    ViewType.Section,
    ViewType.Elevation,
    ViewType.Detail,
    ViewType.DraftingView
)


def millimeters_to_internal(value):
    """Converte milímetros para a unidade interna do Revit (pés)."""
    if value is None:
        raise ValueError("O valor em milímetros não foi informado.")

    return UnitUtils.ConvertToInternalUnits(
        float(value),
        UnitTypeId.Millimeters
    )


def centimeters_to_internal(value):
    """Converte centímetros para a unidade interna do Revit (pés)."""
    if value is None:
        raise ValueError("O valor em centímetros não foi informado.")

    return millimeters_to_internal(float(value) * 10.0)


def internal_to_millimeters(value):
    """Converte a unidade interna do Revit (pés) para milímetros."""
    if value is None:
        raise ValueError("O valor interno não foi informado.")

    return UnitUtils.ConvertFromInternalUnits(
        float(value),
        UnitTypeId.Millimeters
    )


def validate_active_view(view):
    """
    Valida se a vista pode ser usada para a criação de cotas.

    Retorna uma tupla ``(is_valid, message)`` para que o ``script.py`` possa
    apresentar uma mensagem clara ao usuário sem duplicar regras de validação.
    """
    if view is None:
        return False, "Nenhuma vista ativa foi encontrada."

    if view.IsTemplate:
        return False, "Não é possível criar cotas em uma vista template."

    if view.ViewType not in SUPPORTED_VIEW_TYPES:
        return (
            False,
            "A vista ativa não é compatível com a criação de cotas lineares."
        )

    return True, ""


def ensure_minimum_count(elements, minimum=2, element_name="elementos"):
    """Valida se uma coleção possui a quantidade mínima necessária."""
    if elements is None:
        return False

    try:
        return len(elements) >= int(minimum)
    except TypeError:
        raise ValueError(
            "A coleção de {0} não possui tamanho definido.".format(
                element_name
            )
        )


def element_name(element, default="Elemento"):
    """Retorna um nome legível para mensagens e relatórios."""
    if element is None:
        return default

    try:
        name = element.Name
    except Exception:
        name = None

    if name:
        return name

    try:
        return "{0} {1}".format(default, element.Id.IntegerValue)
    except Exception:
        return default


def format_exception(error):
    """Converte uma exceção em texto seguro para exibição no pyRevit."""
    if error is None:
        return "Erro desconhecido."

    try:
        message = str(error)
    except Exception:
        message = ""

    if message:
        return message

    return error.__class__.__name__
