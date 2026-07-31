# -*- coding: utf-8 -*-

from pyrevit import revit, forms
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

doc = revit.doc
view = doc.ActiveView

# Procura os eixos
grids = (
    FilteredElementCollector(doc, view.Id)
    .OfCategory(BuiltInCategory.OST_Grids)
    .WhereElementIsNotElementType()
)

# Transforma em uma lista de objetos Grid
eixos = grids.ToElements()

# Aqui vamos guardar os nomes
nomes = []

# Percorre cada eixo
for eixo in eixos:
    nomes.append(eixo.Name)

# Mostra todos os nomes
forms.alert(
    "\n".join(nomes),
    title="Eixos encontrados"
)