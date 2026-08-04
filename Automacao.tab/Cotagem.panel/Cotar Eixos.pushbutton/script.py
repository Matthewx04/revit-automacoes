# -*- coding: utf-8 -*-

"""Botão pyRevit para criação automática de cotas entre eixos visíveis."""

from Autodesk.Revit.DB import Transaction

from pyrevit import revit, forms, script

from dimensions import create_grid_dimension
from grids import get_grids, split_grids
from utils import (
    centimeters_to_internal,
    ensure_minimum_count,
    format_exception,
    validate_active_view
)


__title__ = "Cotar\nEixos"
__author__ = "Mateus Oliveira"
__doc__ = (
    "Cria uma cadeia de cotas para os eixos horizontais e outra para os "
    "eixos verticais visíveis na vista ativa."
)


# Afastamento entre os extremos dos eixos e a linha de cota.
OFFSET_CM = 50.0


doc = revit.doc
view = doc.ActiveView
output = script.get_output()


def stop(message):
    """Exibe uma mensagem e encerra a execução do botão."""
    forms.alert(
        message,
        title="Cotas automáticas de eixos",
        warn_icon=True,
        exitscript=True
    )


def main():
    """Executa a coleta, classificação e criação das cotas."""
    is_valid, validation_message = validate_active_view(view)

    if not is_valid:
        stop(validation_message)

    try:
        grids = get_grids(doc, view)
    except Exception as error:
        stop(
            "Não foi possível coletar os eixos visíveis na vista.\n\n{0}".format(
                format_exception(error)
            )
        )

    if not grids:
        stop("Nenhum eixo visível foi encontrado na vista ativa.")

    try:
        horizontal_grids, vertical_grids, ignored_grids = split_grids(
            grids,
            view
        )
    except Exception as error:
        stop(
            "Não foi possível classificar os eixos.\n\n{0}".format(
                format_exception(error)
            )
        )

    can_dimension_horizontal = ensure_minimum_count(
        horizontal_grids,
        minimum=2,
        element_name="eixos horizontais"
    )
    can_dimension_vertical = ensure_minimum_count(
        vertical_grids,
        minimum=2,
        element_name="eixos verticais"
    )

    if not can_dimension_horizontal and not can_dimension_vertical:
        stop(
            "São necessários pelo menos dois eixos paralelos para criar uma "
            "cota.\n\n"
            "Eixos horizontais: {0}\n"
            "Eixos verticais: {1}\n"
            "Eixos ignorados: {2}".format(
                len(horizontal_grids),
                len(vertical_grids),
                len(ignored_grids)
            )
        )

    offset = centimeters_to_internal(OFFSET_CM)
    transaction = Transaction(doc, "Criar cotas automáticas de eixos")

    horizontal_dimension = None
    vertical_dimension = None

    try:
        transaction.Start()

        # Eixos horizontais são espaçados no eixo Y e recebem uma linha de
        # cota vertical.
        if can_dimension_horizontal:
            horizontal_dimension = create_grid_dimension(
                doc,
                view,
                horizontal_grids,
                offset
            )

        # Eixos verticais são espaçados no eixo X e recebem uma linha de
        # cota horizontal.
        if can_dimension_vertical:
            vertical_dimension = create_grid_dimension(
                doc,
                view,
                vertical_grids,
                offset
            )

        transaction.Commit()

    except Exception as error:
        if transaction.HasStarted():
            transaction.RollBack()

        stop(
            "Não foi possível criar as cotas. Nenhuma alteração foi "
            "mantida no modelo.\n\nErro:\n{0}".format(
                format_exception(error)
            )
        )

    dimensions_created = 0

    if horizontal_dimension is not None:
        dimensions_created += 1

    if vertical_dimension is not None:
        dimensions_created += 1

    message = (
        "Cotas criadas com sucesso.\n\n"
        "Eixos visíveis: {0}\n"
        "Eixos horizontais: {1}\n"
        "Eixos verticais: {2}\n"
        "Eixos ignorados: {3}\n"
        "Cadeias de cota criadas: {4}\n"
        "Afastamento: {5:g} cm"
    ).format(
        len(grids),
        len(horizontal_grids),
        len(vertical_grids),
        len(ignored_grids),
        dimensions_created,
        OFFSET_CM
    )

    forms.alert(
        message,
        title="Cotas automáticas de eixos"
    )


if __name__ == "__main__":
    main()
