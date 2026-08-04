# -*- coding: utf-8 -*-
"""
collector.py

Responsável por:

1. Validar a vista ativa.
2. Coletar elementos visíveis na vista ativa.
3. Separar os elementos por categoria.
4. Fornecer os elementos para os módulos de referências e dimensões.

Compatível com pyRevit e diferentes versões da Revit API.
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    ElementCategoryFilter,
    ElementId,
    FilteredElementCollector,
    LogicalOrFilter,
    ViewType,
)


# ----------------------------------------------------------------------
# TIPOS DE VISTA PERMITIDOS
# ----------------------------------------------------------------------

ALLOWED_VIEW_TYPES = (
    ViewType.FloorPlan,
    ViewType.CeilingPlan,
    ViewType.EngineeringPlan,
    ViewType.AreaPlan,
)


# ----------------------------------------------------------------------
# COMPATIBILIDADE DO ELEMENT ID
# ----------------------------------------------------------------------

def get_element_id_value(element_id):
    """
    Retorna o valor numérico de um ElementId.

    Algumas versões do Revit utilizam:

        ElementId.Value

    Outras versões utilizam:

        ElementId.IntegerValue

    Args:
        element_id (ElementId):
            Identificador do elemento.

    Returns:
        int:
            Valor numérico do ElementId.

    Raises:
        ValueError:
            Quando o ElementId é nulo ou não pode ser convertido.
    """

    if element_id is None:
        raise ValueError("O ElementId informado é nulo.")

    try:
        return element_id.Value
    except AttributeError:
        pass

    try:
        return element_id.IntegerValue
    except AttributeError:
        pass

    raise ValueError(
        "Não foi possível obter o valor numérico do ElementId."
    )


# ----------------------------------------------------------------------
# VALIDAÇÃO DA VISTA
# ----------------------------------------------------------------------

def validate_active_view(view):
    """
    Verifica se a vista ativa pode receber cotas de planta.

    Args:
        view (Autodesk.Revit.DB.View):
            Vista ativa do documento.

    Returns:
        bool:
            True quando a vista é válida.

    Raises:
        ValueError:
            Quando não existe vista ativa, a vista é template ou o tipo de
            vista não é compatível.
    """

    if view is None:
        raise ValueError(
            "Não foi possível identificar a vista ativa."
        )

    if view.IsTemplate:
        raise ValueError(
            "Templates de vista não podem receber cotas."
        )

    if view.ViewType not in ALLOWED_VIEW_TYPES:
        raise ValueError(
            "A ferramenta deve ser executada em uma vista de planta.\n\n"
            "Vista atual: {0}\n"
            "Tipo da vista: {1}".format(
                view.Name,
                view.ViewType,
            )
        )

    return True


# ----------------------------------------------------------------------
# FUNÇÃO GENÉRICA DE COLETA
# ----------------------------------------------------------------------

def collect_by_category(doc, view, category):
    """
    Coleta os elementos de uma categoria visíveis na vista informada.

    Args:
        doc (Autodesk.Revit.DB.Document):
            Documento atual do Revit.

        view (Autodesk.Revit.DB.View):
            Vista utilizada para restringir a coleta.

        category (Autodesk.Revit.DB.BuiltInCategory):
            Categoria Revit que será coletada.

    Returns:
        list:
            Lista de elementos encontrados.
    """

    if doc is None:
        raise ValueError(
            "O documento do Revit não foi informado."
        )

    if view is None:
        raise ValueError(
            "A vista utilizada na coleta não foi informada."
        )

    collector = (
        FilteredElementCollector(doc, view.Id)
        .OfCategory(category)
        .WhereElementIsNotElementType()
    )

    return list(collector)


# ----------------------------------------------------------------------
# COLETA COM MÚLTIPLAS CATEGORIAS
# ----------------------------------------------------------------------

def collect_by_categories(doc, view, categories):
    """
    Coleta elementos pertencentes a várias categorias.

    Args:
        doc (Autodesk.Revit.DB.Document):
            Documento atual do Revit.

        view (Autodesk.Revit.DB.View):
            Vista utilizada para restringir a coleta.

        categories (list):
            Categorias que serão coletadas.

    Returns:
        list:
            Elementos encontrados.
    """

    if doc is None:
        raise ValueError(
            "O documento do Revit não foi informado."
        )

    if view is None:
        raise ValueError(
            "A vista utilizada na coleta não foi informada."
        )

    if not categories:
        return []

    category_filters = []

    for category in categories:
        category_filter = ElementCategoryFilter(category)
        category_filters.append(category_filter)

    if len(category_filters) == 1:
        element_filter = category_filters[0]
    else:
        element_filter = LogicalOrFilter(category_filters)

    collector = (
        FilteredElementCollector(doc, view.Id)
        .WherePasses(element_filter)
        .WhereElementIsNotElementType()
    )

    return list(collector)


# ----------------------------------------------------------------------
# COLETORES ESPECÍFICOS
# ----------------------------------------------------------------------

def collect_walls(doc, view):
    """
    Coleta as paredes visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_Walls,
    )


def collect_structural_columns(doc, view):
    """
    Coleta os pilares estruturais visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_StructuralColumns,
    )


def collect_architectural_columns(doc, view):
    """
    Coleta os pilares arquitetônicos visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_Columns,
    )


def collect_columns(doc, view):
    """
    Coleta pilares estruturais e arquitetônicos.

    Returns:
        list:
            Lista combinada de pilares, sem elementos repetidos.
    """

    structural_columns = collect_structural_columns(
        doc,
        view,
    )

    architectural_columns = collect_architectural_columns(
        doc,
        view,
    )

    columns = structural_columns + architectural_columns

    return remove_duplicates(columns)


def collect_grids(doc, view):
    """
    Coleta os eixos visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_Grids,
    )


def collect_doors(doc, view):
    """
    Coleta as portas visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_Doors,
    )


def collect_windows(doc, view):
    """
    Coleta as janelas visíveis na vista.
    """

    return collect_by_category(
        doc,
        view,
        BuiltInCategory.OST_Windows,
    )


# ----------------------------------------------------------------------
# TRATAMENTO DE ELEMENTOS
# ----------------------------------------------------------------------

def remove_duplicates(elements):
    """
    Remove elementos repetidos utilizando o ElementId.

    Args:
        elements (list):
            Elementos que serão analisados.

    Returns:
        list:
            Elementos sem duplicação.
    """

    unique_elements = []
    registered_ids = set()

    for element in elements:

        if element is None:
            continue

        try:
            element_id = get_element_id_value(
                element.Id
            )
        except Exception:
            continue

        if element_id in registered_ids:
            continue

        registered_ids.add(element_id)
        unique_elements.append(element)

    return unique_elements


def remove_invalid_elements(elements):
    """
    Remove elementos nulos ou inválidos.

    Args:
        elements (list):
            Lista original.

    Returns:
        list:
            Elementos válidos.
    """

    valid_elements = []

    for element in elements:

        if element is None:
            continue

        try:
            if element.Id == ElementId.InvalidElementId:
                continue
        except Exception:
            continue

        try:
            if not element.IsValidObject:
                continue
        except Exception:
            continue

        valid_elements.append(element)

    return valid_elements


# ----------------------------------------------------------------------
# COLETA COMPLETA DA PLANTA
# ----------------------------------------------------------------------

def collect_plan_elements(
    doc,
    view,
    include_walls=True,
    include_columns=True,
    include_grids=True,
    include_doors=True,
    include_windows=True,
):
    """
    Executa a coleta completa dos elementos da planta.

    Cada categoria pode ser ativada ou desativada individualmente.

    Args:
        doc (Autodesk.Revit.DB.Document):
            Documento atual.

        view (Autodesk.Revit.DB.View):
            Vista que será processada.

        include_walls (bool):
            Coletar paredes.

        include_columns (bool):
            Coletar pilares.

        include_grids (bool):
            Coletar eixos.

        include_doors (bool):
            Coletar portas.

        include_windows (bool):
            Coletar janelas.

    Returns:
        dict:
            Elementos separados por categoria.
    """

    validate_active_view(view)

    elements = {
        "walls": [],
        "columns": [],
        "grids": [],
        "doors": [],
        "windows": [],
    }

    if include_walls:
        elements["walls"] = collect_walls(
            doc,
            view,
        )

    if include_columns:
        elements["columns"] = collect_columns(
            doc,
            view,
        )

    if include_grids:
        elements["grids"] = collect_grids(
            doc,
            view,
        )

    if include_doors:
        elements["doors"] = collect_doors(
            doc,
            view,
        )

    if include_windows:
        elements["windows"] = collect_windows(
            doc,
            view,
        )

    for category_name in elements:

        elements[category_name] = remove_invalid_elements(
            elements[category_name]
        )

        elements[category_name] = remove_duplicates(
            elements[category_name]
        )

    return elements


# ----------------------------------------------------------------------
# INFORMAÇÕES DA COLETA
# ----------------------------------------------------------------------

def get_collection_summary(elements):
    """
    Retorna a quantidade de elementos encontrados em cada categoria.

    Args:
        elements (dict):
            Resultado de collect_plan_elements().

    Returns:
        dict:
            Quantidades por categoria.
    """

    return {
        "walls": len(elements.get("walls", [])),
        "columns": len(elements.get("columns", [])),
        "grids": len(elements.get("grids", [])),
        "doors": len(elements.get("doors", [])),
        "windows": len(elements.get("windows", [])),
    }


def get_total_element_count(elements):
    """
    Retorna a quantidade total de elementos coletados.

    Args:
        elements (dict):
            Resultado de collect_plan_elements().

    Returns:
        int:
            Quantidade total de elementos.
    """

    summary = get_collection_summary(elements)

    return sum(summary.values())