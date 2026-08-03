# -*- coding: utf-8 -*-

"""
Automacao - Cotar Paredes

Versão 1.0

Autor:
Mateus Henrique + ChatGPT

Descrição:
Cria automaticamente uma cota para cada parede reta visível
na vista ativa.

Esta primeira versão suporta:

✔ Planta
✔ Corte
✔ Elevação
✔ Paredes retas

Versões futuras:

- paredes curvas
- cotagem em cadeia
- portas
- janelas
- eixos
"""

from pyrevit import revit
from pyrevit import DB
from pyrevit import forms
from pyrevit import script


doc = revit.doc
uidoc = revit.uidoc
view = doc.ActiveView
output = script.get_output()


# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

OFFSET_MM = 800.0

MM_TO_FT = 304.8

OFFSET = OFFSET_MM / MM_TO_FT

PARALLEL_TOLERANCE = 0.99


# ==========================================================
# VALIDAÇÃO DA VISTA
# ==========================================================

def vista_permite_cotas(vista):

    if vista.IsTemplate:
        return False

    if vista.ViewType == DB.ViewType.ThreeD:
        return False

    if vista.ViewType == DB.ViewType.DrawingSheet:
        return False

    return True


# ==========================================================
# PROJETAR UM PONTO SOBRE O PLANO DA VISTA
# ==========================================================

def projetar_no_plano_da_vista(ponto):

    distancia = view.ViewDirection.DotProduct(
        ponto - view.Origin
    )

    return ponto - view.ViewDirection * distancia


# ==========================================================
# LINHA DA COTA
# ==========================================================

def criar_linha_de_cota(curva):

    inicio = projetar_no_plano_da_vista(
        curva.GetEndPoint(0)
    )

    fim = projetar_no_plano_da_vista(
        curva.GetEndPoint(1)
    )

    direcao = (fim - inicio).Normalize()

    lateral = (
        view.ViewDirection
        .CrossProduct(direcao)
        .Normalize()
    )

    return DB.Line.CreateBound(
        inicio + lateral * OFFSET,
        fim + lateral * OFFSET
    )


# ==========================================================
# GEOMETRIA DA PAREDE
# ==========================================================

def obter_solidos(elemento):

    opt = DB.Options()

    opt.ComputeReferences = True

    opt.IncludeNonVisibleObjects = False

    geo = elemento.get_Geometry(opt)

    if geo is None:
        return []

    solidos = []

    for obj in geo:

        if isinstance(obj, DB.Solid):

            if obj.Volume > 0:

                solidos.append(obj)

        elif isinstance(obj, DB.GeometryInstance):

            instancia = obj.GetInstanceGeometry()

            for geo2 in instancia:

                if isinstance(geo2, DB.Solid):

                    if geo2.Volume > 0:

                        solidos.append(geo2)

    return solidos


# ==========================================================
# REFERÊNCIAS DAS FACES
# ==========================================================

def referencias_extremidades(parede):

    location = parede.Location

    if not isinstance(location, DB.LocationCurve):

        return None, None

    curva = location.Curve

    if not isinstance(curva, DB.Line):

        return None, None

    direcao = (
        curva.GetEndPoint(1)
        - curva.GetEndPoint(0)
    ).Normalize()

    melhor_inicio = None
    melhor_fim = None

    maior_inicio = -1
    maior_fim = -1

    for solid in obter_solidos(parede):

        for face in solid.Faces:

            if not isinstance(face, DB.PlanarFace):
                continue

            if face.Reference is None:
                continue

            normal = face.FaceNormal.Normalize()

            alinhamento = normal.DotProduct(direcao)

            if alinhamento > PARALLEL_TOLERANCE:

                if alinhamento > maior_fim:

                    maior_fim = alinhamento
                    melhor_fim = face.Reference

            elif alinhamento < -PARALLEL_TOLERANCE:

                if abs(alinhamento) > maior_inicio:

                    maior_inicio = abs(alinhamento)
                    melhor_inicio = face.Reference

    return melhor_inicio, melhor_fim