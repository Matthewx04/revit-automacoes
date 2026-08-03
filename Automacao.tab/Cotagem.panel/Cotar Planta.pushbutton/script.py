# -*- coding: utf-8 -*-

from pyrevit import revit, forms

from grids import get_grids


doc = revit.doc
view = doc.ActiveView


grids = get_grids(doc, view)


forms.alert(
    "Projeto: {}\n"
    "Vista: {}\n"
    "Grids encontrados: {}".format(
        doc.Title,
        view.Name,
        len(grids)
    ),
    title="Teste Grids"
)