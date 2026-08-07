# Automação para pyRevit

Extensão desenvolvida para automatizar tarefas no Autodesk Revit utilizando pyRevit e Python.

O projeto tem como objetivo agilizar processos repetitivos de modelagem, documentação e identificação de elementos, reduzindo operações manuais dentro do Revit.

## Funcionalidades

### Cotagem
- [x] Cotar eixos automaticamente
- [x] Cotar pilares automaticamente
- [x] Cotar paredes automaticamente
- [x] Cotar pisos automaticamente
- [x] Interface de configuração das cotas

### Identificação
- [x] Seleção de elementos na vista
- [x] Numeração automática de elementos
- [x] Preenchimento do parâmetro Marca
- [x] Preenchimento do parâmetro Marca de Tipo
- [x] Ordenação dos elementos para numeração
- [x] Criação automática de tags
- [x] Posicionamento automático das tags
- [x] Configuração do tipo de tag

## Estrutura

```text
Automacao.extension/
│
├── Automacao.tab/
│   │
│   ├── Cotagem.panel/
│   │   └── ...
│   │
│   ├── Identificacao.panel/
│   │   └── Numerar Elementos.pushbutton/
│   │       ├── script.py
│   │       ├── icon.png
│   │       └── lib/
│   │           ├── __init__.py
│   │           ├── annotations.py
│   │           ├── collectors.py
│   │           ├── parameters.py
│   │           ├── renumber.py
│   │           ├── sorting.py
│   │           └── validation.py
│   │
│   └── Modelagem.panel/
│       └── ...
│
└── README.md
```

## Ferramentas utilizadas

- Autodesk Revit
- pyRevit
- Python
- Revit API
- Git / GitHub

## Objetivo

Centralizar ferramentas de automação para Revit em uma única extensão pyRevit, facilitando tarefas de documentação, identificação, cotagem e modelagem.

## Autor

Mateus Henrique