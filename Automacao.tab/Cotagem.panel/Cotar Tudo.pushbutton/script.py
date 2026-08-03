
def linha_de_cota(curva, offset):
    """Cria uma linha paralela e deslocada da curva da parede."""
    inicio = curva.GetEndPoint(0)
    fim = curva.GetEndPoint(1)
    direcao = (fim - inicio).Normalize()

    # A vista define o plano em que a cota sera criada. O produto vetorial
    # gera uma normal lateral a parede dentro desse plano.
    normal = view.ViewDirection.CrossProduct(direcao).Normalize()
    return DB.Line.CreateBound(inicio + normal * offset, fim + normal * offset)


if not pode_receber_cotas(view):
    forms.alert(
        'Abra uma planta, corte ou elevacao. O Revit nao permite cotas em 3D.',
        title='Cotar paredes da vista ativa',
        exitscript=True
    )

paredes = (DB.FilteredElementCollector(doc, view.Id)
           .OfClass(DB.Wall)
           .WhereElementIsNotElementType()
           .ToElements())

if not paredes:
    forms.alert('Nenhuma parede visivel foi encontrada nesta vista.', exitscript=True)

criadas = 0
ignoradas = []

with revit.Transaction('Cotar paredes visiveis'):
    for parede in paredes:
        try:
            location = parede.Location
            if not isinstance(location, DB.LocationCurve):
                ignoradas.append(parede.Id)
                continue

            curva = location.Curve
            # GetEndPointReference fornece referencias estaveis para a cota;
            # usar apenas coordenadas criaria uma linha, mas nao uma dimensao
            # associativa ao elemento.
            ref_inicio = curva.GetEndPointReference(0)
            ref_fim = curva.GetEndPointReference(1)
            if ref_inicio is None or ref_fim is None:
                ignoradas.append(parede.Id)
                continue

            referencias = DB.ReferenceArray()
            referencias.Append(ref_inicio)
            referencias.Append(ref_fim)
            doc.Create.NewDimension(view, linha_de_cota(curva, OFFSET), referencias)
            criadas += 1
        except Exception:
            # Uma parede pode nao ter referencias ou estar fora do plano da
            # vista. Nao interrompemos a cotagem das demais paredes.
            ignoradas.append(parede.Id)

msg = '{} cota(s) criada(s).'.format(criadas)
if ignoradas:
    msg += ' {} parede(s) foram ignoradas.'.format(len(ignoradas))

forms.alert(msg, title='Cotar paredes da vista ativa')
output.print_md('### ' + msg)
if ignoradas:
    output.print_md('IDs ignorados: ' + ', '.join(str(x.IntegerValue) for x in ignoradas))