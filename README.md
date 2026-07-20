# RH Juliana

Aplicação interna em **Streamlit** e **Pandas** para gestão e consulta
somente leitura da base persistente de colaboradores.

## Estrutura do projeto

```
RH_Juliana/
├── app.py                          # Home e navegação
├── ui/
│   ├── home.py                     # Cards da tela inicial
│   └── layout.py                   # Layout global e CSS
├── views/
│   ├── consulta_colaborador.py     # Consultar Colaborador
│   └── modulo_placeholder.py       # Módulos futuros
├── repositories/
│   └── colaborador_repository.py   # Leitura da planilha persistente
├── services/
│   └── colaborador_service.py      # Busca e organização da ficha
├── utils/
│   ├── datas.py                    # Idade, tempo e datas
│   ├── formatadores.py             # CPF e valores de exibição
│   └── normalizacao.py             # Matrícula, busca e PcD
├── tests/                          # Testes com dados fictícios
├── requirements.txt
└── README.md
```

## Pré-requisitos

- Python 3.10 ou superior
- pip

## Instalação

1. Clone ou acesse o diretório do projeto.
2. Crie e ative um ambiente virtual (recomendado):

   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux / macOS
   source .venv/bin/activate
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

## Execução

**Importante:** use sempre o Python do `.venv` do projeto. O interpretador
global (ex.: `Python313`) normalmente não tem `openpyxl` e falha ao ler a
base Excel com a mensagem “Não foi possível consultar a base de colaboradores”.

Preferencialmente, dê duplo clique em `iniciar_app.bat` ou execute:

```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

A aplicação será aberta no navegador em `http://localhost:8501`.

A tela inicial (Home) direciona aos módulos. A consulta de colaboradores
permanece disponível pelo card **Colaborador**.

## Fonte de dados

A base operacional oficial é o CSV interno `data/colaboradores.csv`
(separador `;`, encoding `utf-8-sig`). A chave principal é a matrícula
(`Empregado`).

Planilhas Excel (`Upload.xlsx` etc.) servem apenas para bootstrap inicial
ou importação incremental (atualiza/inclui por matrícula; não apaga
registros ausentes na planilha). Consultas e o Cadastro leem/gravam só o CSV.

```powershell
$env:RH_COLABORADORES_CSV = "C:\caminho\colaboradores.csv"
streamlit run app.py
```

## Testes

```bash
pytest -q
```
