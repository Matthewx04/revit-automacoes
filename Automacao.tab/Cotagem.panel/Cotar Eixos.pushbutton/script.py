# -*- coding: utf-8 -*-

from pyrevit import revit, forms
from Autodesk.Revit.UI import TaskDialog

from grids import get_grids
from dimensions import create_reference_array


doc = revit.doc
view = doc.ActiveView


# Busca os grids da vista ativa
grids = get_grids(doc, view)


# Cria as referências
refs = create_reference_array(grids)


TaskDialog.Show(
    "Teste",
    "Referências criadas: {}".format(refs.Size)
)