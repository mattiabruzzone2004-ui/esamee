"""
Dashboard: Consumo di energia vs PIL nel mondo
Esegui con:  python rappre.py     ->  http://127.0.0.1:8050/
Dati richiesti nella stessa cartella: energia_paesi.csv
    (colonne: country, year, gdp, energia_TWh)
Librerie (una volta):
    pip install dash plotly pandas statsmodels country_converter
"""

import os
import glob
import logging

import numpy as np
import pandas as pd
import plotly.express as px
import country_converter as coco
from dash import Dash, dcc, html, Input, Output

# ----------------------------------------------------------------------
# PALETTE / STILE
# ----------------------------------------------------------------------
BLU         = "#0A2C6B"   # blu intestazione
SFONDO      = "white"     # sfondo dei grafici (richiesto bianco)
GRIGLIA     = "#E5E5E5"   # colore griglie (grigio chiaro, visibile su bianco)
TESTO       = "#33312B"
PALETTE     = ["#5B6770", "#C9A227", "#E0653A", "#0A2C6B", "#2E8B7A", "#9C3B3B"]

FONT_TITOLO = "PT Serif, Georgia, serif"
FONT_TESTO  = "Lato, Arial, sans-serif"

# ----------------------------------------------------------------------
# DATI
# ----------------------------------------------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))


def _trova_csv():
    """Trova il file dati per paese (gestisce anche i vecchi nomi)."""
    for nome in ("energia_paesi.csv", "energia_pil.csv", "energia_pil (5).csv"):
        p = os.path.join(BASE, nome)
        if os.path.exists(p):
            return p
    trovati = sorted(glob.glob(os.path.join(BASE, "energia_*.csv")))
    if trovati:
        return trovati[0]
    raise FileNotFoundError("Nessun file 'energia_*.csv' nella cartella.")


paesi = pd.read_csv(_trova_csv())

# La colonna del consumo nel CSV si chiama 'energia_TWh' (in TWh): la riporto
# al nome 'primary_energy_consumption' usato nel resto del codice.
paesi = paesi.rename(columns={"energia_TWh": "primary_energy_consumption"})

# --- Colonne derivate (intensita energetica + continente + codici ISO) ----
# Intensita energetica (kWh/$): consumo in TWh -> kWh (x1e9) diviso il PIL ($)
paesi["intensita"] = paesi["primary_energy_consumption"] * 1e9 / paesi["gdp"]

# Continente e codici ISO derivati dal NOME del paese (no dataset extra).
# country_converter riconosce i nomi stile Our World in Data e restituisce
# None per gli aggregati (World, Europe, European Union (27), ...).
logging.getLogger("country_converter").setLevel(logging.ERROR)
_cc = coco.CountryConverter()
_uniq = pd.DataFrame({"country": sorted(paesi["country"].unique())})
_uniq["iso3"] = _cc.convert(_uniq["country"], to="ISO3", not_found=None)
_uniq["iso2"] = _cc.convert(_uniq["country"], to="ISO2", not_found=None)
_uniq["continente"] = _cc.convert(_uniq["country"], to="continent", not_found=None)
# iso2 minuscolo per le bandiere di flagcdn.com (es. 'it', 'us')
_uniq["iso2"] = _uniq["iso2"].apply(lambda x: x.lower() if isinstance(x, str) else None)
paesi = paesi.merge(_uniq, on="country", how="left")

anni = sorted(paesi["year"].unique())
anno_default = 2022 if 2022 in anni else anni[-1]
paesi_default = ["Italy", "Germany", "United States", "China", "India"]
lista_paesi = sorted(paesi["country"].unique())


def stile(fig):
    """Applica lo stile grafico (sfondo bianco) a una figura cartesiana."""
    fig.update_layout(
        paper_bgcolor=SFONDO,
        plot_bgcolor=SFONDO,
        font=dict(family=FONT_TESTO, size=13, color=TESTO),
        margin=dict(l=55, r=25, t=20, b=45),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRIGLIA, zeroline=False)
    fig.update_yaxes(gridcolor=GRIGLIA, zeroline=False)
    return fig


# ----------------------------------------------------------------------
# APP
# ----------------------------------------------------------------------
FONTS = ("https://fonts.googleapis.com/css2?"
         "family=PT+Serif:wght@700&family=Lato:wght@400;700&display=swap")
app = Dash(__name__, external_stylesheets=[FONTS])
server = app.server
app.title = "Energia e PIL"

# --- stili riutilizzabili ---
lbl_sezione = {"fontFamily": FONT_TITOLO, "color": BLU, "fontSize": "16px",
               "fontWeight": "700", "margin": "0 0 4px 4px"}
lbl_controllo = {"fontFamily": FONT_TESTO, "fontSize": "13px",
                 "fontWeight": "700", "color": BLU, "marginTop": "16px"}
pannello = {"flex": "1 1 46%", "minWidth": "420px", "padding": "8px 14px"}

app.layout = html.Div(
    style={"fontFamily": FONT_TESTO, "color": TESTO, "background": "#FFFFFF",
           "margin": "0", "padding": "0"},
    children=[

        # ---------------- INTESTAZIONE ----------------
        html.Div(
            style={"background": BLU, "color": "white", "padding": "18px 28px"},
            children=[
                html.H1("Il consumo di energia e il PIL nel mondo",
                        style={"fontFamily": FONT_TITOLO, "fontSize": "26px",
                               "margin": "4px 0 0 0", "fontWeight": "700"}),
            ],
        ),

        # ---------------- CORPO: Controlli + Grafici ----------------
        html.Div(
            style={"display": "flex", "flexWrap": "wrap", "padding": "18px"},
            children=[

                # ----- Pannello Controlli -----
                html.Div(
                    style={"width": "260px", "background": "#F3F1EA",
                           "borderRadius": "8px", "padding": "16px",
                           "marginRight": "18px", "alignSelf": "flex-start"},
                    children=[
                        html.H2("Controlli",
                                style={"fontFamily": FONT_TITOLO, "color": BLU,
                                       "fontSize": "20px", "marginTop": "0"}),

                        html.Div("Serie storiche", style=lbl_controllo),
                        dcc.Dropdown(
                            id="paesi",
                            options=[{"label": p, "value": p} for p in lista_paesi],
                            value=paesi_default, multi=True,
                        ),

                        html.Div("Anno di riferimento", style=lbl_controllo),
                        dcc.Dropdown(
                            id="anno",
                            options=[{"label": str(a), "value": a} for a in anni],
                            value=anno_default, clearable=False,
                        ),

                        html.P("Nota: barre, mappa e scatter usano l'anno "
                               "selezionato; barre e scatter usano anche i paesi "
                               "scelti. La mappa colora i paesi per consumo del "
                               "loro continente. Nello scatter ogni bandiera e un "
                               "paese: la posizione e PIL vs consumo totale, "
                               "mentre il colore indica l'intensita energetica - "
                               "cioe l'efficienza (rosso = energivoro, verde = "
                               "efficiente).",
                               style={"fontSize": "12px", "color": "#666",
                                      "marginTop": "20px", "lineHeight": "1.5"}),
                    ],
                ),

                # ----- Griglia dei 4 grafici -----
                html.Div(
                    style={"flex": "1", "display": "flex", "flexWrap": "wrap",
                           "minWidth": "640px"},
                    children=[
                        html.Div([html.Div("Serie storiche", style=lbl_sezione),
                                  dcc.Graph(id="g_linea")], style=pannello),
                        html.Div([html.Div("Confronto del GDP tra paesi", style=lbl_sezione),
                                  dcc.Graph(id="g_barre")], style=pannello),
                        html.Div([html.Div("Mappa del consumo (per continente)",
                                            style=lbl_sezione),
                                  dcc.Graph(id="g_mappa")], style=pannello),
                        html.Div([html.Div("Relazione tra gli indicatori", style=lbl_sezione),
                                  dcc.Graph(id="g_scatter")], style=pannello),
                    ],
                ),
            ],
        ),

        # ---------------- PIE DI PAGINA ----------------
        html.Div("Fonte dati: Our World in Data (Energy)",
                 style={"textAlign": "right", "padding": "8px 28px 24px",
                        "color": "#999", "fontSize": "12px"}),
    ],
)


# ----------------------------------------------------------------------
# CALLBACK
# ----------------------------------------------------------------------
@app.callback(
    Output("g_linea", "figure"),
    Output("g_barre", "figure"),
    Output("g_mappa", "figure"),
    Output("g_scatter", "figure"),
    Input("anno", "value"),
    Input("paesi", "value"),
)
def aggiorna(anno, paesi_sel):
    if not paesi_sel:
        paesi_sel = paesi_default

    d_anno = paesi[paesi["year"] == anno]

    # 1) LINEA -------------------------------------------------------------
    d = paesi[paesi["country"].isin(paesi_sel)]
    g_linea = px.line(
        d, x="year", y="primary_energy_consumption", color="country",
        color_discrete_sequence=PALETTE,
        labels={"year": "Anno", "primary_energy_consumption": "Consumo (TWh)",
                "country": "Paese"},
    )

    # 2) BARRE: PIL dei paesi selezionati nell'anno scelto ----------------
    d_barre = (d_anno[d_anno["country"].isin(paesi_sel)]
               .sort_values("gdp", ascending=False))
    g_barre = px.bar(
        d_barre, x="country", y="gdp",
        color_discrete_sequence=[BLU],
        labels={"country": "Paese", "gdp": "GDP ($)"},
    )
    g_barre.update_layout(xaxis_tickangle=-45)

    # 3) MAPPA MONDO per continente (piu rosso = piu consumo) -------------
    dm = d_anno.dropna(subset=["iso3", "continente"]).copy()
    tot_cont = dm.groupby("continente")["primary_energy_consumption"].sum()
    dm["consumo_continente"] = dm["continente"].map(tot_cont)
    g_mappa = px.choropleth(
        dm, locations="iso3", color="consumo_continente",
        hover_name="continente", color_continuous_scale="Reds",
        labels={"consumo_continente": "Consumo continente (TWh)"},
    )
    g_mappa.update_geos(bgcolor=SFONDO, showframe=False, showcoastlines=False,
                        landcolor="#F2F2F2")
    g_mappa.update_layout(paper_bgcolor=SFONDO,
                          font=dict(family=FONT_TESTO, size=13, color=TESTO),
                          margin=dict(l=0, r=0, t=0, b=0))

    # 4) SCATTER: GDP vs Consumo (paesi selezionati), bandiere + R^2 ------
    dd = (d_anno[d_anno["country"].isin(paesi_sel)]
          .dropna(subset=["gdp", "primary_energy_consumption",
                          "intensita", "iso2"]).copy())
    dd = dd[(dd["gdp"] > 0) & (dd["primary_energy_consumption"] > 0)]

    # la regressione (e quindi R^2) ha senso solo con almeno 2 paesi
    trend = "ols" if len(dd) >= 2 else None
    g_scatter = px.scatter(
        dd, x="gdp", y="primary_energy_consumption",
        color="intensita", hover_name="country",
        custom_data=["country", "gdp", "primary_energy_consumption",
                     "intensita", "continente"],
        log_x=True, log_y=True, color_continuous_scale="RdYlGn_r",
        trendline=trend, trendline_options=dict(log_x=True, log_y=True),
        trendline_color_override=BLU,
        labels={"gdp": "GDP", "primary_energy_consumption": "Consumo (TWh)",
                "intensita": "Intensita (kWh/$)"},
    )
    # marker dati piccoli e semitrasparenti: sopra ci mettiamo le bandiere,
    # ma il marker resta per hover/click (mostra nome paese + dati)
    g_scatter.update_traces(
        selector=dict(mode="markers"),
        marker=dict(size=16, opacity=0.25),
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "GDP: %{customdata[1]:,.0f} $<br>"
                       "Consumo: %{customdata[2]:,.1f} TWh<br>"
                       "Intensita: %{customdata[3]:.3f} kWh/$<br>"
                       "Continente: %{customdata[4]}<extra></extra>"),
    )

    # range espliciti in scala log per posizionare le bandiere
    lx = np.log10(dd["gdp"])
    ly = np.log10(dd["primary_energy_consumption"])
    xr = [lx.min() - 0.4, lx.max() + 0.4]
    yr = [ly.min() - 0.4, ly.max() + 0.4]
    sx = (xr[1] - xr[0]) * 0.045
    sy = (yr[1] - yr[0]) * 0.060
    for _, r in dd.iterrows():
        g_scatter.add_layout_image(dict(
            source=f"https://flagcdn.com/w40/{r['iso2']}.png",
            xref="x", yref="y",
            x=np.log10(r["gdp"]), y=np.log10(r["primary_energy_consumption"]),
            sizex=sx, sizey=sy, xanchor="center", yanchor="middle",
            sizing="contain", layer="above",
        ))
    g_scatter.update_xaxes(range=xr)
    g_scatter.update_yaxes(range=yr)

    # R^2 della regressione (coefficiente di determinazione) - ben evidente
    try:
        res = px.get_trendline_results(g_scatter)
        r2 = res.iloc[0]["px_fit_results"].rsquared
        g_scatter.add_annotation(
            text=f"<b>R&#178; = {r2:.2f}</b>", xref="paper", yref="paper",
            x=0.03, y=0.97, showarrow=False, xanchor="left", yanchor="top",
            font=dict(family=FONT_TITOLO, color="white", size=26),
            bgcolor=BLU, bordercolor=BLU, borderwidth=2, borderpad=8,
            opacity=0.95,
        )
    except Exception:
        pass

    return stile(g_linea), stile(g_barre), g_mappa, stile(g_scatter)


if __name__ == "__main__":
    import webbrowser
    import threading

    port = int(os.environ.get("PORT", 8050))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    debug = not bool(os.environ.get("PORT"))
    url = f"http://127.0.0.1:{port}/"

    if debug:
        # In locale apre il browser da solo; online lo fa il servizio hosting.
        print(f"Avvio dashboard... si aprira da solo su {url}")
        threading.Timer(2.5, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=debug, use_reloader=False)
