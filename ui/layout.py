"""Layout global e responsivo do sistema RH."""

from __future__ import annotations

import streamlit as st


CSS_GLOBAL = """
<style>
:root {
    /* Identidade BRIDA — TMS dark corporativo */
    --rh-azul: #4C82E8;
    --rh-azul-escuro: #8FAEE0;
    --rh-azul-profundo: #0A1428;
    --rh-azul-claro: #6B9AFF;
    --rh-azul-suave: #8FAEE0;
    --rh-laranja: #F36C21;
    --rh-laranja-suave: #FF9A57;
    --rh-borda: #2A3A55;
    --rh-texto: #E8EEF8;
    --rh-texto-sec: #C8D4E6;
    --rh-texto-dis: #9AABC4;
    --rh-fundo: #0B1220;
    --rh-card: #151E33;
    --rh-suave: #121A2B;
    --rh-hover: #1C2A45;
    --rh-gap: .9rem;
    --rh-dash-radius: 12px;
    --rh-dash-shadow: 0 4px 16px rgba(0, 0, 0, .35);
    --rh-dash-gap: 1.1rem;
    --rh-dash-pad: 16px;
    --rh-fonte: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    --rh-fonte-base: 15px;
}

.stApp {
    background: var(--rh-fundo) !important;
    color: var(--rh-texto);
    font-family: var(--rh-fonte);
    font-size: var(--rh-fonte-base);
}

.stApp [data-testid="stAppViewContainer"] {
    background: var(--rh-fundo);
}

/* Evita a barra superior do Streamlit cortar o título */
header[data-testid="stHeader"] {
    background: transparent !important;
}

[data-testid="stToolbar"] {
    right: 0.75rem !important;
    top: 0.35rem !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

.block-container {
    max-width: 1900px;
    padding: 3rem clamp(.85rem, 1.2vw, 1.5rem) 2.1rem;
    width: 96vw;
}

/* Campos de texto — borda branca; azul no foco */
div[data-baseweb="input"],
div[data-baseweb="base-input"],
div[data-baseweb="textarea"],
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stTextArea"] div[data-baseweb="base-input"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stDateInput"] div[data-baseweb="input"],
[data-testid="stTimeInput"] div[data-baseweb="input"],
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stFileUploader"] section {
    border: 1.5px solid #FFFFFF !important;
    border-radius: 8px !important;
    background-color: var(--rh-card) !important;
    box-shadow: none !important;
}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="textarea"]:focus-within,
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stTextArea"] div[data-baseweb="base-input"]:focus-within,
[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stDateInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stTimeInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within,
[data-testid="stFileUploader"] section:focus-within {
    border-color: var(--rh-azul) !important;
    box-shadow: 0 0 0 1px var(--rh-azul) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: var(--rh-card) !important;
    color: var(--rh-texto) !important;
    -webkit-text-fill-color: var(--rh-texto) !important;
}

[data-testid="stTextInput"] input:disabled,
[data-testid="stNumberInput"] input:disabled,
[data-testid="stDateInput"] input:disabled,
[data-testid="stTextArea"] textarea:disabled {
    opacity: 1 !important;
    color: var(--rh-texto-sec) !important;
    -webkit-text-fill-color: var(--rh-texto-sec) !important;
}

[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: var(--rh-texto-dis) !important;
}

div[data-testid="stVerticalBlock"] {
    gap: var(--rh-gap);
}

div[data-testid="stHorizontalBlock"] {
    gap: var(--rh-gap);
}

h1 {
    color: var(--rh-texto);
    font-size: 1.65rem;
    font-weight: 700;
    letter-spacing: -.02em;
    margin-bottom: .15rem;
}

h2,
h3 {
    color: var(--rh-texto);
    font-size: 1.15rem;
    font-weight: 650;
    margin-bottom: .4rem;
    margin-top: .4rem;
}

p, label, .stMarkdown, .stCaption,
[data-testid="stCaption"],
[data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"] p {
    color: var(--rh-texto-sec);
    font-size: 1rem;
}

div[data-testid="stForm"] {
    border: 0;
    padding: 0;
}

div[data-testid="stPageLink"] a {
    align-items: center;
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: .5rem;
    color: var(--rh-texto-sec);
    font-size: .88rem;
    font-weight: 600;
    justify-content: center;
    min-height: 2.45rem;
}

div[data-testid="stPageLink"] a:hover {
    background: var(--rh-hover);
    border-color: var(--rh-azul);
    color: var(--rh-texto);
}

button[data-testid="stBaseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-primary"],
button[kind*="primary"],
form button[type="submit"],
div[data-testid="stFormSubmitButton"] button,
div[data-testid="stButton"] button[kind="primary"],
div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
    background: #2454C5 !important;
    border-color: #2454C5 !important;
    color: #FFFFFF !important;
    min-height: 2.7rem;
    font-size: .92rem !important;
    font-weight: 650;
}

button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[kind*="primary"]:hover,
form button[type="submit"]:hover,
div[data-testid="stFormSubmitButton"] button:hover,
div[data-testid="stButton"] button[kind="primary"]:hover,
div[data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover {
    background: #1B3F96 !important;
    border-color: #1B3F96 !important;
    color: #FFFFFF !important;
}

div[data-testid="stButton"] button[kind="secondary"],
div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
    background: var(--rh-card) !important;
    border: 1.5px solid #FFFFFF !important;
    color: var(--rh-texto) !important;
    font-size: .9rem !important;
}

div[data-testid="stButton"] button[kind="secondary"]:hover,
div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"]:hover {
    background: var(--rh-hover) !important;
    border-color: var(--rh-azul) !important;
    color: #FFFFFF !important;
}

/* Segmented control / pills — remove rosa padrão do Streamlit */
[data-testid="stButtonGroup"] {
    gap: .4rem !important;
    flex-wrap: wrap !important;
}

[data-testid="stButtonGroup"] button {
    background: var(--rh-card) !important;
    border: 1px solid var(--rh-borda) !important;
    color: var(--rh-texto-sec) !important;
    font-weight: 600 !important;
}

[data-testid="stButtonGroup"] button:hover {
    border-color: var(--rh-azul) !important;
    color: var(--rh-texto) !important;
    background: var(--rh-hover) !important;
}

/* Aba ativa — laranja BRIDA para orientar o usuário */
[data-testid="stButtonGroup"] button[kind="primary"],
[data-testid="stButtonGroup"] button[aria-pressed="true"],
[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"],
[data-testid="stButtonGroup"] button[data-testid="stBaseButton-pillsActive"] {
    background: var(--rh-laranja) !important;
    border-color: var(--rh-laranja) !important;
    color: #FFFFFF !important;
    box-shadow: 0 0 0 1px rgba(243, 108, 33, .35) !important;
    font-weight: 700 !important;
}

[data-testid="stButtonGroup"] button[kind="primary"]:hover,
[data-testid="stButtonGroup"] button[aria-pressed="true"]:hover {
    background: #D85A12 !important;
    border-color: #D85A12 !important;
    color: #FFFFFF !important;
}

/* Cabeçalho de página com identidade BRIDA */
.rh-page-brand {
    align-items: center;
    background: linear-gradient(105deg, #0F1E46 0%, #18285A 55%, #1E3A7A 100%);
    border: 1px solid #243656;
    border-bottom: 3px solid var(--rh-laranja);
    border-radius: 12px;
    box-shadow: var(--rh-dash-shadow);
    display: flex;
    gap: 1rem;
    margin: .15rem 0 .85rem;
    padding: .85rem 1.1rem;
}

.rh-page-brand-mark {
    align-items: center;
    background: rgba(255, 255, 255, .12);
    border: 1px solid rgba(255, 255, 255, .22);
    border-radius: 10px;
    color: #fff;
    display: flex;
    flex: 0 0 auto;
    font-size: .72rem;
    font-weight: 800;
    height: 2.6rem;
    justify-content: center;
    letter-spacing: .06em;
    min-width: 5.6rem;
    padding: 0 .7rem;
    white-space: nowrap;
}

.rh-page-brand-copy {
    display: flex;
    flex: 1 1 auto;
    flex-direction: column;
    gap: .15rem;
    min-width: 0;
}

.rh-page-brand-copy strong {
    color: #fff;
    font-size: 1.35rem;
    font-weight: 750;
    letter-spacing: -.02em;
    line-height: 1.2;
}

.rh-page-brand-copy span {
    color: rgba(255, 255, 255, .78);
    font-size: .88rem;
}

.rh-header {
    align-items: center;
    display: flex;
    gap: 1.1rem;
    padding: .35rem .1rem;
}

.rh-avatar {
    align-items: center;
    background: linear-gradient(145deg, #1E3A7A 0%, #2454C5 100%);
    border: 1px solid #3A5A9A;
    border-radius: 999px;
    color: #fff;
    display: flex;
    flex: 0 0 3.75rem;
    font-size: 1.1rem;
    font-weight: 750;
    height: 3.75rem;
    justify-content: center;
}

.rh-name-line {
    align-items: baseline;
    display: flex;
    flex-wrap: wrap;
    gap: .35rem 1rem;
    margin-bottom: .45rem;
}

.rh-name {
    color: var(--rh-texto);
    font-size: 1.4rem;
    font-weight: 700;
    line-height: 1.25;
}

.rh-cpf {
    color: var(--rh-texto-sec);
    font-size: .95rem;
    font-weight: 550;
    white-space: nowrap;
}

.rh-meta {
    align-items: center;
    color: var(--rh-texto-sec);
    display: flex;
    flex-wrap: wrap;
    font-size: .98rem;
    gap: .4rem 1.1rem;
}

.rh-meta-separator {
    color: var(--rh-texto-dis);
}

.rh-status-badge {
    background: var(--rh-hover);
    border: 1px solid var(--rh-borda);
    border-radius: 999px;
    color: var(--rh-texto-sec);
    font-size: .8rem;
    font-weight: 650;
    padding: .15rem .55rem;
    text-transform: uppercase;
}

.rh-status-ativo {
    background: rgba(47, 107, 66, .22);
    border-color: #3d7a52;
    color: #8fd4a4;
}

.rh-status-afastado {
    background: rgba(243, 108, 33, .18);
    border-color: #a85a28;
    color: var(--rh-laranja-suave);
}

.rh-status-desligado {
    background: rgba(132, 80, 80, .25);
    border-color: #7a4545;
    color: #e0a0a0;
}

.rh-status-inativo {
    background: var(--rh-hover);
    border-color: var(--rh-borda);
    color: var(--rh-texto-dis);
}

.rh-status-nao-informado {
    background: #f1f3f6;
    border-color: #dfe3e8;
    color: #687386;
}

.rh-section-title {
    align-items: center;
    color: var(--rh-azul-claro);
    display: flex;
    font-size: .95rem;
    font-weight: 700;
    gap: .45rem;
    letter-spacing: .03em;
    margin-bottom: .55rem;
    text-transform: uppercase;
}

.rh-section-icon {
    display: inline-flex;
    flex: 0 0 1.1rem;
    height: 1.1rem;
    width: 1.1rem;
}

.rh-section-icon svg {
    fill: none;
    height: 100%;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
    width: 100%;
}

.rh-row {
    align-items: start;
    border-bottom: 1px solid var(--rh-borda);
    display: grid;
    gap: .65rem;
    grid-template-columns: minmax(7.5rem, 42%) minmax(6rem, 58%);
    padding: .55rem 0;
}

.rh-row:last-child {
    border-bottom: 0;
}

.rh-label {
    color: var(--rh-texto-sec);
    font-size: .95rem;
    font-weight: 600;
    line-height: 1.35;
}

.rh-value {
    color: var(--rh-texto);
    display: -webkit-box;
    font-size: .98rem;
    font-weight: 600;
    line-height: 1.35;
    max-height: 2.7em;
    overflow-wrap: anywhere;
    overflow: hidden;
    text-align: right;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
}

.rh-section-divider {
    border-top: 1px solid var(--rh-borda);
    margin: .35rem 0 .15rem;
}

div[data-testid="stDataFrame"] {
    border: 1px solid var(--rh-borda);
    border-radius: .55rem;
    overflow: hidden;
}

@media (min-width: 901px) and (max-width: 1440px) {
    div[data-testid="stHorizontalBlock"]:has(.rh-section-title):has(
        > div[data-testid="stColumn"]:nth-child(4)
    ) {
        flex-wrap: wrap;
    }

    div[data-testid="stHorizontalBlock"]:has(.rh-section-title):has(
        > div[data-testid="stColumn"]:nth-child(4)
    ) > div[data-testid="stColumn"] {
        flex: 1 1 calc(50% - var(--rh-gap)) !important;
        min-width: min(21rem, 100%) !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.rh-section-title):has(
        > div[data-testid="stColumn"]:nth-child(3)
    ):not(:has(> div[data-testid="stColumn"]:nth-child(4))) {
        flex-wrap: wrap;
    }

    div[data-testid="stHorizontalBlock"]:has(.rh-section-title):has(
        > div[data-testid="stColumn"]:nth-child(3)
    ):not(:has(
        > div[data-testid="stColumn"]:nth-child(4)
    )) > div[data-testid="stColumn"] {
        flex: 1 1 calc(50% - var(--rh-gap)) !important;
        min-width: min(21rem, 100%) !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.rh-section-title):has(
        > div[data-testid="stColumn"]:nth-child(3)
    ):not(:has(
        > div[data-testid="stColumn"]:nth-child(4)
    )) > div[data-testid="stColumn"]:last-child {
        flex-basis: 100% !important;
    }
}

@media (max-width: 900px) {
    .block-container {
        padding-top: 3rem;
        padding-left: .8rem;
        padding-right: .8rem;
        width: 100%;
    }

    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    div[data-testid="stColumn"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    .rh-header {
        align-items: flex-start;
    }

    .rh-avatar {
        flex-basis: 3.4rem;
        height: 3.4rem;
    }

    .rh-name {
        font-size: 1.25rem;
    }
}

@media (max-width: 520px) {
    .rh-row {
        grid-template-columns: 1fr;
        gap: .2rem;
    }

    .rh-value {
        text-align: left;
    }
}

.st-key-home_header {
    margin: 1.75rem auto 0;
    max-width: 56rem;
    text-align: center;
}

.rh-login-wrap {
    margin: 2.5rem auto 1rem;
    max-width: 28rem;
    text-align: center;
}

.st-key-login_page {
    margin: 0 auto;
    max-width: 26rem;
}

.st-key-login_page [data-testid="stForm"] {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-top: 3px solid var(--rh-laranja);
    border-radius: 12px;
    box-shadow: var(--rh-dash-shadow);
    padding: 1.15rem 1.2rem .9rem;
}

.rh-sessao-bar {
    align-items: baseline;
    display: flex;
    flex-wrap: wrap;
    gap: .55rem;
    margin: .15rem 0 .35rem;
}

.rh-sessao-bar strong {
    color: var(--rh-texto);
    font-size: .95rem;
}

.rh-sessao-bar span {
    background: rgba(243, 108, 33, .18);
    border: 1px solid #a85a28;
    border-radius: 999px;
    color: var(--rh-laranja-suave);
    font-size: .78rem;
    font-weight: 650;
    padding: .18rem .6rem;
}

.rh-home-brand {
    align-items: center;
    background: #18285A;
    border: 1px solid #243656;
    border-bottom: 3px solid var(--rh-laranja);
    border-radius: .85rem;
    color: #fff;
    display: inline-flex;
    font-size: .85rem;
    font-weight: 750;
    height: 2.55rem;
    justify-content: center;
    letter-spacing: .08em;
    margin-bottom: .75rem;
    width: 2.55rem;
}

.rh-home-title {
    color: var(--rh-texto);
    font-size: 1.75rem;
    font-weight: 750;
    letter-spacing: -.02em;
    margin: 0 0 .65rem;
}

.rh-home-subtitle {
    color: var(--rh-texto-sec);
    font-size: 1rem;
    margin: 0 0 .7rem;
}

.rh-home-hint {
    color: var(--rh-texto-dis);
    font-size: .9rem;
    margin: 0;
}

.st-key-home_grid {
    margin: 2.75rem auto 0;
    max-width: 75rem;
}

.st-key-home_grid div[data-testid="stHorizontalBlock"] {
    column-gap: 2.5rem !important;
    justify-content: center !important;
    row-gap: 2rem !important;
}

.st-key-home_grid div[data-testid="stColumn"] {
    flex: 0 0 17rem !important;
    max-width: 17rem;
    min-width: 17rem !important;
}

@media (min-width: 901px) {
    .st-key-home_grid div[data-testid="stColumn"]:nth-child(-n + 3) {
        margin-bottom: 1rem;
    }
}

.rh-mod-wrap {
    margin: 0 auto;
    max-width: 17rem;
}

.rh-mod-card {
    align-items: center;
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: .75rem;
    box-shadow: var(--rh-dash-shadow);
    display: flex;
    gap: .75rem;
    height: 7rem;
    padding: 1.15rem 1.2rem;
    transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
    width: 100%;
}

[class*="st-key-home_card_"]:has(
    .rh-mod-card:not(.rh-mod-card-disabled)
):hover .rh-mod-card {
    border-color: var(--rh-azul-suave);
    box-shadow: 0 .5rem 1.1rem rgba(24, 40, 90, .1);
    transform: translateY(-2px);
}

.rh-mod-card-disabled {
    background: #f8fafc;
    opacity: .72;
}

.rh-mod-card-disabled:hover {
    border-color: var(--rh-borda);
    box-shadow: none;
    transform: none;
}

.rh-mod-icon {
    color: var(--rh-azul);
    flex: 0 0 1.35rem;
    height: 1.35rem;
    margin-top: .1rem;
    width: 1.35rem;
}

.rh-mod-icon svg {
    fill: none;
    height: 100%;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.7;
    width: 100%;
}

.rh-mod-title {
    color: var(--rh-azul-escuro);
    font-size: 1rem;
    font-weight: 650;
    margin-bottom: .3rem;
}

.rh-mod-desc {
    color: var(--rh-texto-sec);
    font-size: .88rem;
    line-height: 1.4;
}

[class*="st-key-home_card_"] {
    height: 7rem;
    position: relative;
}

[class*="st-key-home_card_"] div[data-testid="stElementContainer"]:has(
    > [data-testid="stPageLink"]
),
[class*="st-key-home_card_"] div[data-testid="stElementContainer"]:has(
    > div[data-testid="stButton"]
) {
    height: 100%;
    inset: 0;
    position: absolute;
    width: 100%;
    z-index: 2;
}

[class*="st-key-home_card_"] [data-testid="stPageLink"],
[class*="st-key-home_card_"] div[data-testid="stButton"] {
    height: 100%;
    inset: 0;
    position: absolute;
    width: 100%;
    z-index: 2;
}

[class*="st-key-home_card_"] [data-testid="stPageLink"] > div,
[class*="st-key-home_card_"] div[data-testid="stButton"] > div {
    height: 100%;
    width: 100%;
}

[class*="st-key-home_card_"] [data-testid="stPageLink"] a,
[class*="st-key-home_card_"] div[data-testid="stButton"] button {
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    color: transparent !important;
    height: 7rem !important;
    inset: .375rem 0 auto !important;
    margin: 0 !important;
    min-height: 7rem !important;
    opacity: 0;
    position: absolute !important;
    width: 100% !important;
}

[class*="st-key-home_card_"] div[data-testid="stButton"] button:disabled {
    cursor: not-allowed;
    opacity: 0;
}

.rh-home-footer {
    color: #8a98ab;
    display: flex;
    flex-wrap: wrap;
    font-size: .78rem;
    gap: .65rem 1.2rem;
    justify-content: center;
    margin: 4rem auto 0;
    max-width: 56rem;
    padding-top: .85rem;
}

@media (max-width: 900px) {
    .rh-home-title {
        font-size: 1.65rem;
    }

    .rh-mod-wrap {
        max-width: 100%;
    }

    .st-key-home_grid {
        margin-top: 2.25rem;
        max-width: 36.5rem;
    }

    .st-key-home_grid div[data-testid="stHorizontalBlock"] {
        column-gap: 2rem !important;
        row-gap: 2rem !important;
    }

    .st-key-home_grid div[data-testid="stColumn"] {
        flex: 0 0 17rem !important;
        max-width: 17rem;
        min-width: 17rem !important;
    }

    .st-key-home_grid div[data-testid="stColumn"]:nth-child(-n + 4) {
        margin-bottom: 1rem;
    }
}

@media (max-width: 620px) {
    .st-key-home_grid {
        margin-top: 2rem;
        max-width: 17rem;
    }

    .st-key-home_grid div[data-testid="stHorizontalBlock"] {
        gap: 1.75rem;
    }

    .st-key-home_grid div[data-testid="stColumn"] {
        flex-basis: 100% !important;
        max-width: 100%;
        min-width: 100% !important;
    }

    .st-key-home_grid div[data-testid="stColumn"]:not(:last-child) {
        margin-bottom: .75rem;
    }

    .rh-home-footer {
        margin-top: 3.5rem;
    }
}

.rh-setor-resumo {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: .7rem;
    box-shadow: var(--rh-dash-shadow);
    display: grid;
    gap: .55rem 1.25rem;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    margin: .35rem 0 .75rem;
    padding: .9rem 1.05rem;
}

.rh-setor-resumo span {
    color: var(--rh-texto-sec);
    display: block;
    font-size: .78rem;
    letter-spacing: .02em;
    text-transform: uppercase;
}

.rh-setor-resumo strong {
    color: var(--rh-azul-escuro);
    display: block;
    font-size: .95rem;
    font-weight: 650;
    margin-top: .15rem;
}

.rh-setor-kpi {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: .6rem;
    box-shadow: var(--rh-dash-shadow);
    min-height: 3.5rem;
    padding: .6rem .8rem;
}

.rh-setor-kpi span {
    color: var(--rh-texto-sec);
    display: block;
    font-size: .78rem;
}

.rh-setor-kpi strong {
    color: var(--rh-azul-escuro);
    display: block;
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: .2rem;
}

/* ========== Design System — Dashboard RH (BRIDA / TMS) ========== */
.rh-dash-card {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-left: 3px solid var(--rh-azul);
    border-radius: var(--rh-dash-radius);
    box-shadow: var(--rh-dash-shadow);
    min-height: 4.6rem;
    padding: 14px 16px;
    height: 100%;
}

.rh-dash-card-title {
    color: var(--rh-texto-sec);
    display: block;
    font-size: .78rem;
    font-weight: 650;
    letter-spacing: .03em;
    text-transform: uppercase;
}

.rh-dash-card-value {
    color: var(--rh-texto);
    display: block;
    font-size: 1.28rem;
    font-weight: 700;
    line-height: 1.25;
    margin-top: .3rem;
}

.rh-dash-card small {
    color: var(--rh-texto-dis);
    display: block;
    font-size: .78rem;
    margin-top: .2rem;
}

.rh-dash-insights {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: var(--rh-dash-radius);
    box-shadow: var(--rh-dash-shadow);
    color: var(--rh-texto);
    font-size: .92rem;
    margin-top: .65rem;
    padding: 14px 16px;
}

.rh-dash-cobertura {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-radius: var(--rh-dash-radius);
    box-shadow: var(--rh-dash-shadow);
    min-height: 320px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.rh-dash-cobertura p {
    color: var(--rh-texto-sec);
    font-size: .88rem;
    margin: .55rem 0 0;
}

.rh-dash-analise {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-top: 3px solid var(--rh-laranja);
    border-radius: var(--rh-dash-radius);
    box-shadow: var(--rh-dash-shadow);
    color: var(--rh-texto);
    display: flex;
    flex-direction: column;
    font-size: .9rem;
    justify-content: flex-start;
    min-height: 320px;
    padding: 16px 18px;
}

.rh-dash-analise .rh-dash-card-title {
    background: #18285A;
    border-radius: 6px;
    color: #E8EEF8;
    display: inline-block;
    margin-bottom: .55rem;
    padding: .28rem .55rem;
}

.rh-dash-analise ul {
    margin: .25rem 0 0 1.05rem;
    padding: 0;
}

.rh-dash-analise li {
    color: var(--rh-texto-sec);
    line-height: 1.35;
    margin-bottom: .45rem;
}

.rh-dash-nav-analise {
    background: var(--rh-card);
    border: 1px solid var(--rh-borda);
    border-left: 3px solid var(--rh-laranja);
    border-radius: var(--rh-dash-radius);
    box-shadow: var(--rh-dash-shadow);
    color: var(--rh-texto);
    font-size: .9rem;
    line-height: 1.45;
    margin: 0 0 .35rem;
    min-height: 4.8rem;
    overflow: visible;
    padding: 12px 16px;
    width: 100%;
}

.rh-dash-nav-analise-label {
    color: var(--rh-azul-claro);
    display: block;
    font-size: .76rem;
    font-weight: 700;
    letter-spacing: .03em;
    margin-bottom: .35rem;
    text-transform: uppercase;
}

.rh-dash-nav-analise ul {
    margin: 0;
    padding-left: 1.1rem;
}

.rh-dash-nav-analise li {
    color: var(--rh-texto);
    margin: 0 0 .35rem;
    overflow-wrap: anywhere;
}

.rh-dash-nav-analise li:last-child {
    margin-bottom: 0;
}

.rh-dash-insights ul {
    margin: .35rem 0 0 1.1rem;
    padding: 0;
}

.rh-dash-insights li {
    margin-bottom: .2rem;
}

/*
 * Containers dos gráficos: Streamlit aplica a key no bloco vertical.
 * Usamos border=True + override do wrapper nativo.
 */
[class*="st-key-rh_dash_chart"],
[class*="st-key-rh_dash_chart"] > div[data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-rh_dash_page"] div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stPlotlyChart"]) {
    background: var(--rh-card) !important;
    border: 1px solid var(--rh-borda) !important;
    border-radius: 10px !important;
    box-shadow: var(--rh-dash-shadow) !important;
    padding: 16px !important;
    overflow: hidden !important;
    height: 100%;
}

/* Listagens longas (ex.: Funções): rolagem no card; altura pode ser forçada pela grade. */
[class*="st-key-rh_dash_chart_scroll"],
[class*="st-key-rh_dash_chart_scroll"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    overflow-x: hidden !important;
    overflow-y: auto !important;
}

[class*="st-key-rh_dash_chart"] [data-testid="stPlotlyChart"],
[class*="st-key-rh_dash_page"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"] {
    margin-top: 4px;
    overflow: hidden !important;
}

[class*="st-key-rh_dash_chart"] [data-testid="stPlotlyChart"] > div,
[class*="st-key-rh_dash_chart"] .js-plotly-plot,
[class*="st-key-rh_dash_chart"] .plot-container {
    overflow: hidden !important;
}

[class*="st-key-rh_dash_chart_scroll"] [data-testid="stPlotlyChart"],
[class*="st-key-rh_dash_chart_scroll"] [data-testid="stPlotlyChart"] > div,
[class*="st-key-rh_dash_chart_scroll"] .js-plotly-plot,
[class*="st-key-rh_dash_chart_scroll"] .plot-container {
    overflow: visible !important;
}

[class*="st-key-rh_dash_chart"] [data-testid="stCaption"] {
    color: var(--rh-texto-dis);
    font-size: .72rem;
    margin-top: .35rem;
    padding: 0 .1rem;
    min-height: 1.35rem;
    line-height: 1.35rem;
}

.rh-dash-chart-footer {
    box-sizing: border-box;
    color: var(--rh-texto-dis);
    font-size: .72rem;
    height: 1.5rem;
    line-height: 1.5rem;
    margin-top: .35rem;
    overflow: hidden;
    padding: 0 .1rem;
    text-overflow: ellipsis;
    white-space: nowrap;
    width: 100%;
}

/* Faixa de filtros */
[class*="st-key-rh_dash_filters"],
[class*="st-key-rh_dash_filters"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--rh-card) !important;
    border: 1px solid var(--rh-borda) !important;
    border-radius: 10px !important;
    box-shadow: var(--rh-dash-shadow) !important;
    padding: 14px 16px 10px !important;
    margin: .25rem 0 .85rem;
}

[class*="st-key-rh_dash_filters"] [data-testid="stMultiSelect"] > div > div {
    border: 1.5px solid #FFFFFF !important;
    border-radius: 10px !important;
    background: var(--rh-suave) !important;
}

[class*="st-key-rh_dash_filters"] [data-testid="stMultiSelect"] > div > div:focus-within {
    border-color: var(--rh-azul) !important;
    box-shadow: 0 0 0 1px var(--rh-azul) !important;
}

[class*="st-key-rh_dash_filters"] [data-testid="stButton"] button {
    border: 1px solid var(--rh-borda) !important;
    border-radius: 10px !important;
    background: var(--rh-card) !important;
    color: var(--rh-texto) !important;
    font-weight: 600;
    min-height: 2.45rem;
    box-shadow: none !important;
}

[class*="st-key-rh_dash_filters"] [data-testid="stButton"] button:hover {
    border-color: var(--rh-azul) !important;
    background: var(--rh-hover) !important;
}

[class*="st-key-rh_dash_page"] div[role="radiogroup"] {
    gap: .45rem !important;
    margin-bottom: .45rem;
}

[class*="st-key-rh_dash_page"] div[role="radiogroup"] label {
    border: 1px solid var(--rh-borda) !important;
    border-radius: 10px !important;
    background: var(--rh-card) !important;
    color: var(--rh-texto) !important;
}

[class*="st-key-rh_dash_page"] [data-testid="stDataFrame"] {
    border: 1px solid var(--rh-borda);
    border-radius: 10px;
    box-shadow: var(--rh-dash-shadow);
    overflow: hidden;
    background: var(--rh-card);
}

[class*="st-key-rh_dash_kpis"] {
    margin: .25rem 0 .55rem;
}

@media (max-width: 1100px) {
    .rh-setor-resumo {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 700px) {
    .rh-setor-resumo {
        grid-template-columns: 1fr 1fr;
    }
}

/* ========== Cadastro: linhas label | valor/campo ========== */
.rh-cadastro-card-body {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-top: .35rem;
}

.rh-cadastro-row {
    align-items: center;
    border-bottom: 1px solid var(--rh-borda);
    display: grid;
    gap: .55rem;
    grid-template-columns: minmax(7.25rem, 38%) minmax(0, 62%);
    min-height: 2rem;
    padding: .42rem 0;
}

.rh-cadastro-row:last-child {
    border-bottom: 0;
}

.rh-cadastro-row-top,
.rh-cadastro-label-wrap.rh-cadastro-row-top {
    align-items: start;
}

.rh-cadastro-label {
    color: var(--rh-texto-sec);
    font-size: .95rem;
    font-weight: 600;
    letter-spacing: .01em;
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.rh-cadastro-value {
    color: var(--rh-texto);
    font-size: .98rem;
    font-weight: 600;
    line-height: 1.4;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

.rh-cadastro-value-locked {
    background: var(--rh-suave);
    border: 1.5px solid #FFFFFF;
    border-radius: .35rem;
    color: var(--rh-texto);
    font-size: .95rem;
    min-height: 2.15rem;
    padding: .4rem .55rem;
}

.rh-cadastro-lista-aviso {
    color: var(--rh-texto-sec);
    font-size: .8rem;
    font-weight: 550;
    margin-top: .2rem;
}

.rh-cadastro-ajuda {
    color: var(--rh-texto-sec);
    font-size: .8rem;
    font-weight: 550;
    line-height: 1.35;
    margin-top: .18rem;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}

/* Edição: só o VerticalBlock da linha vira grid 38/62 (não aninha widgets) */
div[data-testid="stVerticalBlock"][class*="st-key-cadastro_row_"],
[class*="st-key-cadastro_row_"] > div[data-testid="stVerticalBlock"],
[class*="st-key-cadastro_row_"]
> div[data-testid="stVerticalBlockBorderWrapper"]
> div[data-testid="stVerticalBlock"] {
    align-items: center;
    border-bottom: 1px solid var(--rh-borda);
    column-gap: .55rem;
    display: grid !important;
    grid-template-columns: minmax(7.25rem, 38%) minmax(0, 62%);
    margin: 0;
    padding: .28rem 0;
    row-gap: 0;
}

div[data-testid="stVerticalBlock"][class*="st-key-cadastro_row_MOTIVO"],
[class*="st-key-cadastro_row_MOTIVO"] > div[data-testid="stVerticalBlock"],
[class*="st-key-cadastro_row_MOTIVO"]
> div[data-testid="stVerticalBlockBorderWrapper"]
> div[data-testid="stVerticalBlock"] {
    align-items: start;
}

div[data-testid="stVerticalBlock"][class*="st-key-cadastro_row_"]
> div[data-testid="stElementContainer"],
[class*="st-key-cadastro_row_"] > div[data-testid="stVerticalBlock"]
> div[data-testid="stElementContainer"],
[class*="st-key-cadastro_row_"]
> div[data-testid="stVerticalBlockBorderWrapper"]
> div[data-testid="stVerticalBlock"]
> div[data-testid="stElementContainer"] {
    margin: 0 !important;
    min-width: 0;
    width: 100%;
}

[class*="st-key-cadastro_row_"] .rh-cadastro-label-wrap {
    padding-top: .35rem;
}

[class*="st-key-cadastro_row_"]
div[data-testid="stTextInput"],
[class*="st-key-cadastro_row_"]
div[data-testid="stSelectbox"],
[class*="st-key-cadastro_row_"]
div[data-testid="stNumberInput"],
[class*="st-key-cadastro_row_"]
div[data-testid="stDateInput"],
[class*="st-key-cadastro_row_"]
div[data-testid="stTextArea"] {
    width: 100% !important;
    max-width: 100% !important;
}

/* Slot da coluna de valor: um único filho do grid 38/62 */
[class*="st-key-cadastro_val_"] {
    min-width: 0 !important;
    width: 100% !important;
}

[class*="st-key-cadastro_val_"] > div[data-testid="stVerticalBlock"] {
    gap: .15rem !important;
    width: 100% !important;
}

[class*="st-key-cadastro_val_"] div[data-testid="stElementContainer"] {
    margin: 0 !important;
    min-width: 0 !important;
    width: 100% !important;
}

/* Evita ellipsis agressivo no valor selecionado do BaseWeb */
.st-key-cadastro_form_grid div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.st-key-cadastro_form_grid div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
    max-width: 100% !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.st-key-cadastro_form_grid div[data-testid="stTextInput"] input,
.st-key-cadastro_form_grid div[data-testid="stSelectbox"] > div,
.st-key-cadastro_form_grid div[data-testid="stNumberInput"] input,
.st-key-cadastro_form_grid div[data-testid="stDateInput"] input,
.st-key-cadastro_form_grid textarea {
    min-height: 2.15rem;
    width: 100% !important;
    background-color: var(--rh-card) !important;
    color: var(--rh-texto) !important;
    -webkit-text-fill-color: var(--rh-texto) !important;
}

.st-key-cadastro_acoes div[data-testid="stButton"] button {
    font-weight: 650 !important;
}

.st-key-cadastro_acoes div[data-testid="stButton"] button[kind="primary"],
.st-key-cadastro_acoes div[data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
    background: #2454C5 !important;
    border-color: #2454C5 !important;
    color: #FFFFFF !important;
}

.st-key-cadastro_acoes div[data-testid="stButton"] button[kind="secondary"],
.st-key-cadastro_acoes div[data-testid="stButton"] button[data-testid="stBaseButton-secondary"] {
    background: var(--rh-card) !important;
    border: 1.5px solid #FFFFFF !important;
    color: var(--rh-texto) !important;
}

.st-key-cadastro_form_grid textarea {
    max-height: 4.8rem;
    min-height: 4.5rem !important;
}

/* Cards: padding e sem altura forçada igual */
[class*="st-key-cadastro_card_"]
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: .9rem .9rem .75rem !important;
}

[class*="st-key-cadastro_card_"] .rh-section-title {
    margin-bottom: .75rem;
}

.st-key-cadastro_form_grid > div[data-testid="stVerticalBlock"] {
    gap: .7rem;
}

/* Quatro cards no grid principal (somente o horizontal de topo) */
.st-key-cadastro_form_grid
> div[data-testid="stVerticalBlock"]
> div[data-testid="stElementContainer"]
> div[data-testid="stHorizontalBlock"] {
    align-items: flex-start;
    flex-wrap: nowrap;
}

.st-key-cadastro_form_grid
> div[data-testid="stVerticalBlock"]
> div[data-testid="stElementContainer"]
> div[data-testid="stHorizontalBlock"]
> div[data-testid="stColumn"] {
    flex: 1 1 0 !important;
    max-width: 25% !important;
    min-width: 0 !important;
}

.st-key-cadastro_acoes {
    margin: .35rem 0 .85rem;
}

@media (max-width: 1400px) {
    .rh-cadastro-row,
    div[data-testid="stVerticalBlock"][class*="st-key-cadastro_row_"],
    [class*="st-key-cadastro_row_"] > div[data-testid="stVerticalBlock"],
    [class*="st-key-cadastro_row_"]
    > div[data-testid="stVerticalBlockBorderWrapper"]
    > div[data-testid="stVerticalBlock"] {
        grid-template-columns: minmax(7rem, 42%) minmax(0, 58%);
    }
}

@media (max-width: 1200px) {
    .st-key-cadastro_form_grid
    > div[data-testid="stVerticalBlock"]
    > div[data-testid="stElementContainer"]
    > div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        row-gap: .85rem;
    }

    .st-key-cadastro_form_grid
    > div[data-testid="stVerticalBlock"]
    > div[data-testid="stElementContainer"]
    > div[data-testid="stHorizontalBlock"]
    > div[data-testid="stColumn"] {
        flex: 0 0 calc(50% - .45rem) !important;
        max-width: calc(50% - .45rem) !important;
        min-width: calc(50% - .45rem) !important;
    }
}

@media (max-width: 700px) {
    .st-key-cadastro_form_grid
    > div[data-testid="stVerticalBlock"]
    > div[data-testid="stElementContainer"]
    > div[data-testid="stHorizontalBlock"]
    > div[data-testid="stColumn"] {
        flex: 0 0 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
    }
}
</style>
"""


def configurar_layout_global() -> None:
    """Aplica uma única configuração visual para todas as páginas."""
    st.set_page_config(
        page_title="RH BRIDA",
        page_icon="BR",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(CSS_GLOBAL, unsafe_allow_html=True)
