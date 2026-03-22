# FertiCalc

Prototipo inicial do FertiCalc em TkBootstrap inspirado no layout do EasyIOP.

## Estrutura

- `main.py` - ponto de entrada que inicia a aplicacao TkBootstrap.
- `ui/main_window.py` - shell principal com o `Notebook` que hospeda cada aba.
- `ui/base_page.py` - contrato simples para todas as abas.
- `pages/add_fields.py` - primeira aba ("Adicionar talhoes") com canvas a esquerda e painel lateral a direita.
- `processing/kmz_loader.py` - leitura de arquivos KMZ/KML e extracao de poligonos.

Cada nova aba principal deve ganhar um modulo em `pages/` e ser registrada em `ui/main_window.py`.

## Preparacao

```bash
pip install -r requirements.txt
```

## Execucao

```bash
python main.py
```

Na aba "Adicionar talhoes" clique em **Carregar KMZ / KML**, selecione um ou varios arquivos e os contornos aparecem automaticamente no canvas. O painel lateral lista os talhoes carregados e destaca o desenho quando voce seleciona uma linha. Essa base fornece o padrao para adicionar novas abas e funcionalidades com o avanco do projeto.
