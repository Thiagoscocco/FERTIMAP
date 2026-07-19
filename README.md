# FertiMap

Aplicativo desktop em Python com TkBootstrap para carregar talhoes via KMZ/KML, visualizar mapas e apoiar rotinas de manejo como cultivos, condicoes do solo, calagem e adubacao.

## Funcionalidades atuais

- Importacao de talhoes a partir de arquivos `.kmz` e `.kml`.
- Visualizacao dos poligonos em canvas com selecao e destaque por talhao.
- Cadastro e edicao de atributos agronomicos por area.
- Abas dedicadas para `Cultivos`, `Condicoes do solo`, `Calagem` e `Adubacao`.
- Calculos auxiliares de recomendacao com base nos dados preenchidos no app.
- Bootstrap automatico de ambiente local quando as dependencias nao estao instaladas.

## Estrutura do projeto

- `main.py` - ponto de entrada e rotina de bootstrap da execucao.
- `ui/main_window.py` - janela principal e registro das abas.
- `ui/base_page.py` - comportamento base compartilhado entre as paginas.
- `pages/` - telas principais da aplicacao.
- `processing/` - regras de negocio, leitura de arquivos e calculos agronomicos.

## Requisitos

- Python 3.11 ou superior.

## Instalacao

```bash
pip install -r requirements.txt
```

Se preferir, voce tambem pode apenas executar o projeto. Quando `ttkbootstrap` nao estiver disponivel, o app cria uma `.venv-local`, instala as dependencias e reinicia automaticamente usando esse ambiente.

## Execucao

```bash
python main.py
```

## Fluxo basico de uso

1. Abra a aba `Adicionar talhoes`.
2. Clique em `Carregar KMZ / KML` para importar um ou mais arquivos.
3. Revise os talhoes no mapa e no painel lateral.
4. Complete os dados agronomicos de cada area.
5. Navegue pelas abas de `Cultivos`, `Condicoes do solo`, `Calagem` e `Adubacao` para visualizar e configurar os resultados.
