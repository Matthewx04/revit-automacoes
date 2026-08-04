# -*- coding: utf-8 -*-
"""
script.py

Integração principal do comando Dimensionar Planta.

Fluxo:

1. Valida a vista ativa.
2. Permite escolher as categorias que serão cotadas.
3. Permite escolher as orientações horizontal e vertical.
4. Coleta os elementos visíveis na vista ativa.
5. Calcula os limites da planta.
6. Coleta as referências organizadas por categoria.
7. Solicita ao usuário a posição das linhas de cota.
8. Cria as dimensões em uma única transação.
9. Exibe um resumo da execução.

Compatível com pyRevit, IronPython e versões recentes do Revit.
"""

from Autodesk.Revit.Exceptions import OperationCanceledException

from pyrevit import revit, forms, script

import collector
import geometry
import references
import dimension


# ----------------------------------------------------------------------
# DOCUMENTO E VISTA
# ----------------------------------------------------------------------

doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView
output = script.get_output()


# ----------------------------------------------------------------------
# CONFIGURAÇÕES DA INTERFACE
# ----------------------------------------------------------------------

CATEGORY_OPTIONS = [
    "Paredes",
    "Portas",
    "Janelas",
    "Pilares",
    "Eixos",
]

CATEGORY_MAP = {
    "Paredes": "walls",
    "Portas": "doors",
    "Janelas": "windows",
    "Pilares": "columns",
    "Eixos": "grids",
}

ORIENTATION_OPTIONS = [
    "Horizontal",
    "Vertical",
]

ORIENTATION_MAP = {
    "Horizontal": dimension.DIMENSION_HORIZONTAL,
    "Vertical": dimension.DIMENSION_VERTICAL,
}


# ----------------------------------------------------------------------
# SELEÇÃO DE OPÇÕES
# ----------------------------------------------------------------------

def select_categories():
    """
    Solicita as categorias que serão cotadas.

    Returns:
        list[str]:
            Chaves internas das categorias.
    """

    selected = forms.SelectFromList.show(
        CATEGORY_OPTIONS,
        title="Categorias para cotagem",
        button_name="Continuar",
        multiselect=True,
    )

    if not selected:
        output.print_md(
            "Operação cancelada: nenhuma categoria foi selecionada."
        )
        script.exit()

    return [
        CATEGORY_MAP[item]
        for item in selected
        if item in CATEGORY_MAP
    ]


def select_orientations():
    """
    Solicita as orientações que serão criadas.

    Returns:
        list[str]:
            horizontal e/ou vertical.
    """

    selected = forms.SelectFromList.show(
        ORIENTATION_OPTIONS,
        title="Orientações das cotas",
        button_name="Continuar",
        multiselect=True,
    )

    if not selected:
        output.print_md(
            "Operação cancelada: nenhuma orientação foi selecionada."
        )
        script.exit()

    return [
        ORIENTATION_MAP[item]
        for item in selected
        if item in ORIENTATION_MAP
    ]


# ----------------------------------------------------------------------
# PONTOS DE POSICIONAMENTO
# ----------------------------------------------------------------------

def pick_dimension_point(orientation):
    """
    Solicita um ponto para posicionar a linha de cota.

    Args:
        orientation (str):
            horizontal ou vertical.

    Returns:
        XYZ:
            Ponto escolhido pelo usuário.
    """

    if orientation == dimension.DIMENSION_HORIZONTAL:

        message = (
            "Clique no local onde deseja posicionar "
            "a cota horizontal."
        )

    elif orientation == dimension.DIMENSION_VERTICAL:

        message = (
            "Clique no local onde deseja posicionar "
            "a cota vertical."
        )

    else:
        raise ValueError(
            "Orientação inválida para seleção do ponto."
        )

    return uidoc.Selection.PickPoint(message)


def create_dimension_line_from_point(
    orientation,
    picked_point,
    bounds,
):
    """
    Cria a linha de dimensão correspondente ao ponto escolhido.
    """

    if orientation == dimension.DIMENSION_HORIZONTAL:

        return geometry.create_horizontal_dimension_line(
            view=view,
            bounds=bounds,
            picked_point=picked_point,
            extension=0.0,
        )

    if orientation == dimension.DIMENSION_VERTICAL:

        return geometry.create_vertical_dimension_line(
            view=view,
            bounds=bounds,
            picked_point=picked_point,
            extension=0.0,
        )

    raise ValueError(
        "Orientação inválida para criação da linha."
    )


# ----------------------------------------------------------------------
# RESUMO
# ----------------------------------------------------------------------

def print_reference_summary(
    grouped_references,
    selected_categories,
):
    """
    Exibe a quantidade de referências por categoria.
    """

    summary = references.get_reference_summary(
        grouped_references
    )

    output.print_md("## Referências utilizadas")

    for category_name in selected_categories:

        category_summary = summary.get(
            category_name,
            {},
        )

        output.print_md(
            "- `{0}`: horizontal **{1}**, vertical **{2}**".format(
                category_name,
                category_summary.get(
                    references.REFERENCE_HORIZONTAL,
                    0,
                ),
                category_summary.get(
                    references.REFERENCE_VERTICAL,
                    0,
                ),
            )
        )


def print_creation_summary(result):
    """
    Exibe o resultado da criação das dimensões.
    """

    summary = dimension.get_creation_summary(result)

    output.print_md("---")
    output.print_md("## Resultado")

    output.print_md(
        "Dimensões criadas: **{0}**".format(
            summary["created"]
        )
    )

    output.print_md(
        "Solicitações ignoradas: **{0}**".format(
            summary["skipped"]
        )
    )

    output.print_md(
        "Erros: **{0}**".format(
            summary["errors"]
        )
    )

    for skipped in result.get("skipped", []):

        output.print_md(
            "- Ignorada `{0}`: {1}".format(
                skipped.get("name", "sem nome"),
                skipped.get("error", "erro desconhecido"),
            )
        )


# ----------------------------------------------------------------------
# EXECUÇÃO
# ----------------------------------------------------------------------

try:
    # ------------------------------------------------------------------
    # VALIDAÇÃO
    # ------------------------------------------------------------------

    collector.validate_active_view(view)

    # ------------------------------------------------------------------
    # OPÇÕES DO USUÁRIO
    # ------------------------------------------------------------------

    selected_categories = select_categories()
    selected_orientations = select_orientations()

    # ------------------------------------------------------------------
    # COLETA
    # ------------------------------------------------------------------

    elements = collector.collect_plan_elements(
        doc=doc,
        view=view,
        include_walls=("walls" in selected_categories),
        include_columns=("columns" in selected_categories),
        include_grids=("grids" in selected_categories),
        include_doors=("doors" in selected_categories),
        include_windows=("windows" in selected_categories),
    )

    bounds = geometry.calculate_plan_bounds(
        element_groups=elements,
        view=view,
    )

    grouped_references = references.collect_dimension_references(
        element_groups=elements,
        view=view,
    )

    # ------------------------------------------------------------------
    # POSICIONAMENTO E SOLICITAÇÕES
    # ------------------------------------------------------------------

    requests = []

    for orientation in selected_orientations:

        combined_reference_data = (
            dimension.get_combined_reference_data(
                grouped_references=grouped_references,
                category_names=selected_categories,
                orientation=orientation,
            )
        )

        if not dimension.can_create_dimension(
            combined_reference_data
        ):
            output.print_md(
                "A orientação `{0}` não possui referências suficientes "
                "e será ignorada.".format(orientation)
            )
            continue

        picked_point = pick_dimension_point(
            orientation
        )

        dimension_line = create_dimension_line_from_point(
            orientation=orientation,
            picked_point=picked_point,
            bounds=bounds,
        )

        request = dimension.create_combined_dimension_request(
            grouped_references=grouped_references,
            category_names=selected_categories,
            orientation=orientation,
            dimension_line=dimension_line,
            dimension_type=None,
            name="planta_{0}".format(orientation),
        )

        requests.append(request)

    if not requests:
        raise ValueError(
            "Nenhuma dimensão válida pôde ser preparada."
        )

    # ------------------------------------------------------------------
    # CRIAÇÃO DAS DIMENSÕES
    # ------------------------------------------------------------------

    result = dimension.create_dimensions_in_transaction(
        doc=doc,
        view=view,
        requests=requests,
        transaction_name="Dimensionar planta",
        skip_invalid=True,
    )

    # ------------------------------------------------------------------
    # SAÍDA
    # ------------------------------------------------------------------

    output.print_md("# Dimensionar planta")
    output.print_md(
        "**Vista:** {0}".format(view.Name)
    )

    output.print_md(
        "**Categorias:** {0}".format(
            ", ".join(selected_categories)
        )
    )

    output.print_md(
        "**Orientações:** {0}".format(
            ", ".join(selected_orientations)
        )
    )

    output.print_md("---")

    print_reference_summary(
        grouped_references=grouped_references,
        selected_categories=selected_categories,
    )

    print_creation_summary(result)

    if result.get("created"):

        forms.alert(
            "{0} dimensão(ões) criada(s) com sucesso.".format(
                len(result["created"])
            ),
            title="Dimensionar planta",
            warn_icon=False,
        )

    else:

        forms.alert(
            "Nenhuma dimensão foi criada.\n\n"
            "Consulte o painel de saída do pyRevit.",
            title="Dimensionar planta",
            warn_icon=True,
        )


# ----------------------------------------------------------------------
# CANCELAMENTO
# ----------------------------------------------------------------------

except OperationCanceledException:

    output.print_md(
        "Operação cancelada pelo usuário."
    )


# ----------------------------------------------------------------------
# ERROS DE VALIDAÇÃO
# ----------------------------------------------------------------------

except ValueError as error:

    forms.alert(
        str(error),
        title="Dimensionar planta",
        warn_icon=True,
    )


# ----------------------------------------------------------------------
# ERROS GERAIS
# ----------------------------------------------------------------------

except Exception as error:

    forms.alert(
        "Ocorreu um erro durante a cotagem da planta:\n\n{0}".format(
            error
        ),
        title="Dimensionar planta",
        warn_icon=True,
    )
