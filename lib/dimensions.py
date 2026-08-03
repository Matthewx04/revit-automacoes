# -*- coding: utf-8 -*-

from Autodesk.Revit.DB import (
    ReferenceArray,
    Line,
    Transaction
)


DEFAULT_OFFSET = 0.5


def create_reference_array(grids):
    """
    Cria um ReferenceArray a partir de uma lista de grids.
    """
    pass


def create_dimension_line(grids, offset):
    """
    Cria a linha onde a cota será posicionada.
    """
    pass


def create_dimension(doc, view, line, references):
    """
    Cria uma dimensão no Revit.
    """
    pass


def create_grid_dimension(doc, view, grids, offset):
    """
    Função principal para criar cotas de grids.
    """
    pass