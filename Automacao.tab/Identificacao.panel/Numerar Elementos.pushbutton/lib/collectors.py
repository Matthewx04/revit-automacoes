# -*- coding: utf-8 -*-

"""
collectors.py

Responsável exclusivamente pela seleção/coleta
dos elementos que serão processados pelo plugin.

Fluxo:

1. Verifica se já existem elementos selecionados.
2. Se existirem, utiliza essa seleção.
3. Se não existirem, solicita seleção por retângulo.
4. Filtra tipos, elementos inválidos e elementos
   sem categoria.

Este módulo NÃO:
- ordena elementos;
- altera parâmetros;
- renumera elementos;
- inicia Transaction.
"""

from pyrevit import revit

from Autodesk.Revit.DB import ElementType

from Autodesk.Revit.Exceptions import (
    OperationCanceledException
)

from Autodesk.Revit.UI.Selection import (
    ISelectionFilter
)


# ============================================================
# CONTEXTO
# ============================================================

doc = revit.doc
uidoc = revit.uidoc


# ============================================================
# FILTRO
# ============================================================

class RenumberSelectionFilter(ISelectionFilter):
    """
    Filtro utilizado durante a seleção por caixa.

    Permite somente elementos de instância
    com categoria válida.
    """

    def AllowElement(self, element):

        if element is None:
            return False

        # Não queremos selecionar tipos.
        if isinstance(element, ElementType):
            return False

        # Elementos sem categoria normalmente não são úteis
        # para nossa ferramenta.
        try:

            if element.Category is None:
                return False

        except Exception:
            return False

        return True


    def AllowReference(
        self,
        reference,
        position
    ):
        """
        Obrigatório para ISelectionFilter.

        Não é necessário para PickElementsByRectangle.
        """

        return False


# ============================================================
# VALIDAÇÃO BÁSICA DE ELEMENTO
# ============================================================

def is_valid_collected_element(element):
    """
    Verifica se um elemento coletado pode
    seguir para o restante do plugin.
    """

    if element is None:
        return False

    if isinstance(element, ElementType):
        return False

    try:

        if element.Category is None:
            return False

    except Exception:
        return False

    return True


# ============================================================
# PRÉ-SELEÇÃO
# ============================================================

def get_preselected_elements():
    """
    Obtém os elementos que já estavam selecionados
    antes de clicar no botão.

    Isso permite o fluxo:

        selecionar por janela no Revit
                ↓
        clicar em Renumerar
                ↓
        plugin utiliza a seleção existente

    Returns
    -------
    list
        Lista dos elementos previamente selecionados.
    """

    try:

        element_ids = (
            uidoc.Selection.GetElementIds()
        )

    except Exception:
        return []

    if not element_ids:
        return []

    elements = []

    for element_id in element_ids:

        try:

            element = doc.GetElement(
                element_id
            )

        except Exception:
            continue

        if not is_valid_collected_element(
            element
        ):
            continue

        elements.append(
            element
        )

    return elements


# ============================================================
# SELEÇÃO POR RETÂNGULO
# ============================================================

def select_elements_by_rectangle():
    """
    Solicita ao usuário uma seleção por caixa.

    Returns
    -------
    list
        Elementos selecionados.

    Se o usuário pressionar ESC:
        retorna []
    """

    selection_filter = (
        RenumberSelectionFilter()
    )

    try:

        selected_elements = (
            uidoc.Selection.PickElementsByRectangle(
                selection_filter,
                (
                    "Crie uma caixa de seleção sobre "
                    "os elementos que deseja renumerar."
                )
            )
        )

    except OperationCanceledException:
        return []

    except Exception:
        return []

    if not selected_elements:
        return []

    elements = []

    for element in selected_elements:

        if not is_valid_collected_element(
            element
        ):
            continue

        elements.append(
            element
        )

    return elements


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def pick_elements_by_rectangle(
    use_preselection=True
):
    """
    Função utilizada pelo script.py.

    IMPORTANTE:
    não precisa receber uidoc nem doc.

    Fluxo padrão:

        1. verifica pré-seleção;
        2. se existir, retorna imediatamente;
        3. caso contrário, abre seleção por retângulo.

    Isso mantém compatibilidade com:

        elements = pick_elements_by_rectangle()

    Parameters
    ----------
    use_preselection : bool
        Se True, utiliza elementos já selecionados
        antes da execução do botão.

    Returns
    -------
    list
        Elementos selecionados.
    """

    # --------------------------------------------------------
    # 1. PRÉ-SELEÇÃO
    # --------------------------------------------------------

    if use_preselection:

        preselected_elements = (
            get_preselected_elements()
        )

        if preselected_elements:

            return preselected_elements


    # --------------------------------------------------------
    # 2. SELEÇÃO POR CAIXA
    # --------------------------------------------------------

    return select_elements_by_rectangle()


# ============================================================
# ALIAS PRINCIPAL
# ============================================================

def collect_elements(
    use_preselection=True
):
    """
    Alias mais genérico para uso futuro.

    Atualmente possui o mesmo comportamento de
    pick_elements_by_rectangle().
    """

    return pick_elements_by_rectangle(
        use_preselection=use_preselection
    )