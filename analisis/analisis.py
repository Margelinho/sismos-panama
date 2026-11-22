"""
Análisis probabilístico de los sismos de Panamá.
Lee data/sismos.csv y genera analisis/resultados.xlsx con una hoja por tema del curso.

Uso (desde la carpeta principal del proyecto):
    python analisis/analisis.py                       -> usa todos los datos
    python analisis/analisis.py --hasta 2026-12-01    -> fecha de corte para el trabajo escrito

Requisitos:
    python -m pip install pandas openpyxl
"""
import argparse
import math
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "sismos.csv"
SALIDA = RAIZ / "analisis" / "resultados.xlsx"

TERREMOTO = pd.Timestamp("2026-10-09")   # inicio del periodo de réplicas (hora local)
UMBRAL_MAG = 4.0                         # "sismo fuerte" para binomial, contingencia y árbol
N_BINOMIAL = 20                          # de los próximos n sismos...
N_MUESTRA_HIPER = 10                     # tamaño de la muestra sin reemplazo


# ---------------------------------------------------------------------------
# Fórmulas de las distribuciones (sin librerías extra, igual que en clase)
# ---------------------------------------------------------------------------
def binomial(x, n, p):
    return math.comb(n, x) * p ** x * (1 - p) ** (n - x)


def hipergeometrica(x, N, K, n):
    return math.comb(K, x) * math.comb(N - K, n - x) / math.comb(N, n)


def poisson(k, lam):
    # en forma logarítmica para que no se desborde con k grandes
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1)) if lam > 0 else float(k == 0)


def normal_acum(x, mu, sigma):
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


# ---------------------------------------------------------------------------
# Carga y preparación
# ---------------------------------------------------------------------------
def cargar(hasta):
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["fecha_local"] = pd.to_datetime(df["fecha_local"])
    if hasta is not None:
        df = df[df["fecha_local"] <= hasta]
    df["periodo"] = df["fecha_local"].apply(lambda f: "Antes del terremoto" if f < TERREMOTO else "Desde el terremoto")
    df["fuerte"] = df["magnitud"] >= UMBRAL_MAG
    return df


def conteo_diario(df):
    """Sismos por día, incluyendo los días con 0 sismos."""
    dias = pd.date_range(df["fecha_local"].min(), df["fecha_local"].max(), freq="D")
    c = df.groupby("fecha_local").size().reindex(dias, fill_value=0)
    diario = pd.DataFrame({"fecha": dias, "sismos": c.values})
    diario["periodo"] = diario["fecha"].apply(lambda f: "Antes del terremoto" if f < TERREMOTO else "Desde el terremoto")
    mag_max = df.groupby("fecha_local")["magnitud"].max()
    diario["magnitud_maxima"] = diario["fecha"].map(mag_max)
    return diario


# ---------------------------------------------------------------------------
# Hojas
# ---------------------------------------------------------------------------
def hoja_variables(df):
    clasif = pd.DataFrame([
        ["region", "Cualitativa", "Nominal", "Azuero-Soná"],
        ["pais", "Cualitativa", "Nominal", "Panamá"],
        ["categoria", "Cualitativa", "Ordinal", "Leve (3.0-3.9)"],
        ["superficial", "Cualitativa (dicotómica)", "Nominal", "Sí"],
        ["fecha_hora", "Cuantitativa", "Intervalo", "2026-11-19 13:52"],
        ["magnitud", "Cuantitativa continua", "Intervalo", "4.5"],
        ["profundidad_km", "Cuantitativa continua", "Razón", "8.0"],
        ["sismos por día", "Cuantitativa discreta", "Razón", "3"],
    ], columns=["Variable", "Tipo", "Nivel de medición", "Ejemplo"])

    filas = []
    for periodo, g in [("Todo", df)] + list(df.groupby("periodo")):
        for col in ["magnitud", "profundidad_km"]:
            s = g[col]
            filas.append([periodo, col, len(s), s.mean(), s.median(), s.std(), s.min(),
                          s.quantile(0.25), s.quantile(0.75), s.max()])
    desc = pd.DataFrame(filas, columns=["Periodo", "Variable", "n", "Media", "Mediana", "Desv. estándar",
                                        "Mínimo", "Q1", "Q3", "Máximo"]).round(3)
    return [("Clasificación de variables", clasif), ("Estadística descriptiva", desc)]


def hoja_contingencia(df):
    orden_cat = ["Menor (<3.0)", "Leve (3.0-3.9)", "Ligero (4.0-4.9)", "Moderado o mayor (>=5.0)"]
    tablas = []
    for var in ["region", "pais"]:
        ct = pd.crosstab(df[var], df["categoria"], margins=True, margins_name="Total")
        ct = ct.reindex(columns=[c for c in orden_cat if c in ct.columns] + ["Total"])
        tablas.append((f"Frecuencias: {var} × categoría de magnitud", ct.reset_index()))
        cond = pd.crosstab(df[var], df["categoria"], normalize="index").round(4)
        cond = cond.reindex(columns=[c for c in orden_cat if c in cond.columns])
        tablas.append((f"Probabilidad condicional P(categoría | {var})", cond.reset_index()))

    p_fuerte = df.groupby("region")["fuerte"].agg(["sum", "count"])
    p_fuerte["P(mag >= 4.0 | región)"] = (p_fuerte["sum"] / p_fuerte["count"]).round(4)
    p_fuerte = p_fuerte.rename(columns={"sum": "Sismos >= 4.0", "count": "Total sismos"}).reset_index()
    tablas.append(("Probabilidad de sismo fuerte por región", p_fuerte))

    per = pd.crosstab(df["periodo"], df["categoria"], margins=True, margins_name="Total")
    per = per.reindex(columns=[c for c in orden_cat if c in per.columns] + ["Total"])
    tablas.append(("Frecuencias: periodo × categoría", per.reset_index()))
    return tablas


def hoja_arbol(df):
    n = len(df)
    filas = []
    for reg, g in df.groupby("region"):
        p_reg = len(g) / n
        p_f = g["fuerte"].mean()
        filas.append([reg, len(g), p_reg, "Magnitud >= 4.0", p_f, p_reg * p_f])
        filas.append([reg, len(g), p_reg, "Magnitud < 4.0", 1 - p_f, p_reg * (1 - p_f)])
    arbol = pd.DataFrame(filas, columns=["Rama 1: región", "Sismos", "P(región)", "Rama 2",
                                         "P(rama 2 | región)", "P(región y rama 2)"]).round(4)
    p_total_fuerte = df["fuerte"].mean()
    bayes = (df[df["fuerte"]].groupby("region").size() / df["fuerte"].sum()).round(4)
    bayes = bayes.rename("P(región | magnitud >= 4.0)").reset_index()
    resumen = pd.DataFrame({"Concepto": ["P(magnitud >= 4.0) total (suma de ramas)"],
                            "Valor": [round(p_total_fuerte, 4)]})
    return [("Diagrama de árbol: región → magnitud", arbol),
            ("Probabilidad total", resumen),
            ("Teorema de Bayes: si el sismo fue fuerte, ¿de qué región vino?", bayes)]


def hoja_binomial(df):
    tablas = []
    for periodo, g in [("Todo", df)] + list(df.groupby("periodo")):
        p = g["fuerte"].mean()
        filas, acum = [], 0
        for x in range(N_BINOMIAL + 1):
            px = binomial(x, N_BINOMIAL, p)
            acum += px
            filas.append([x, px, acum, 1 - acum + px])
        t = pd.DataFrame(filas, columns=["x", "P(X = x)", "P(X <= x)", "P(X >= x)"]).round(6)
        info = (f"{periodo}: p = P(mag >= {UMBRAL_MAG}) = {p:.4f}, n = {N_BINOMIAL}, "
                f"media np = {N_BINOMIAL * p:.2f}, varianza np(1-p) = {N_BINOMIAL * p * (1 - p):.2f}")
        tablas.append((info, t))
    return tablas


def hoja_hipergeometrica(df):
    fin = df["fecha_local"].max()
    semana = df[df["fecha_local"] > fin - pd.Timedelta(days=7)]
    region_top = semana["region"].value_counts().idxmax()
    N, K = len(semana), int((semana["region"] == region_top).sum())
    n = min(N_MUESTRA_HIPER, N)
    filas, acum = [], 0
    for x in range(max(0, n - (N - K)), min(n, K) + 1):
        px = hipergeometrica(x, N, K, n)
        acum += px
        filas.append([x, px, acum])
    t = pd.DataFrame(filas, columns=["x", "P(X = x)", "P(X <= x)"]).round(6)
    info = (f"Última semana ({(fin - pd.Timedelta(days=6)).date()} a {fin.date()}): N = {N} sismos, "
            f"K = {K} de la región '{region_top}', muestra sin reemplazo n = {n}. "
            f"Media nK/N = {n * K / N:.2f}")
    return [(info, t)]


def hoja_poisson(diario):
    tablas, resumen = [], []
    lam_antes = None
    for periodo, g in diario.groupby("periodo"):
        lam, var = g["sismos"].mean(), g["sismos"].var()
        if periodo.startswith("Antes"):
            lam_antes = lam
        dias = len(g)
        obs = g["sismos"].value_counts()
        kmax = int(g["sismos"].max())
        filas = []
        for k in range(kmax + 1):
            pk = poisson(k, lam)
            filas.append([k, int(obs.get(k, 0)), pk, pk * dias])
        t = pd.DataFrame(filas, columns=["k sismos en un día", "Días observados", "P(X = k)", "Días esperados"])
        t = t[(t["Días observados"] > 0) | (t["Días esperados"] >= 0.5)].round(4)
        info = (f"{periodo}: {dias} días, λ = media de sismos por día = {lam:.3f}, varianza = {var:.3f}, "
                f"índice de dispersión varianza/media = {var / lam:.2f} (Poisson ideal = 1)")
        tablas.append((info, t))
        resumen.append([periodo, dias, round(lam, 3), round(var, 3), round(var / lam, 2), kmax])
    tablas.insert(0, ("Resumen por periodo", pd.DataFrame(
        resumen, columns=["Periodo", "Días", "λ (media/día)", "Varianza", "Varianza/media", "Máximo en un día"])))

    if lam_antes:
        top = diario.sort_values("sismos", ascending=False).head(5)
        filas = []
        for _, r in top.iterrows():
            k = int(r["sismos"])
            p_cola = 1 - sum(poisson(i, lam_antes) for i in range(k))
            if p_cola > 1e-15:
                texto = f"{p_cola:.3e}"
            else:  # demasiado pequeña para calcularla directo: se usa el logaritmo de P(X = k)
                log10_p = (-lam_antes + k * math.log(lam_antes) - math.lgamma(k + 1)) / math.log(10)
                texto = f"≈ 10^{math.floor(log10_p)}"
            filas.append([r["fecha"].date(), k, texto])
        tablas.append((f"Días con más sismos: ¿qué tan probables eran con la λ normal ({lam_antes:.3f}/día)?",
                       pd.DataFrame(filas, columns=["Fecha", "Sismos", "P(X >= k) con λ de antes"])))
    return tablas


def hoja_normal(df):
    tablas = []
    for col, cortes in [("profundidad_km", [5, 10, 20, 30, 70]), ("magnitud", [2.5, 3.0, 3.5, 4.0, 4.5, 5.0])]:
        s = df[col]
        mu, sd = s.mean(), s.std()
        filas = []
        limites = [-math.inf] + cortes + [math.inf]
        for a, b in zip(limites[:-1], limites[1:]):
            p_teo = normal_acum(b, mu, sd) - normal_acum(a, mu, sd)
            p_obs = ((s >= a) & (s < b)).mean()
            etiqueta = f"{'' if a == -math.inf else a} a {'' if b == math.inf else b}".strip()
            filas.append([etiqueta, p_obs, p_teo])
        t = pd.DataFrame(filas, columns=["Intervalo", "Proporción observada", "Probabilidad normal"]).round(4)
        tablas.append((f"{col}: μ = {mu:.3f}, σ = {sd:.3f}, n = {len(s)}", t))
    return tablas


def hoja_chebyshev(diario):
    base = diario[diario["periodo"].str.startswith("Antes")]["sismos"]
    mu, sd = base.mean(), base.std()
    filas = []
    for k in [1.5, 2, 3, 4]:
        umbral_sup = mu + k * sd
        dentro = ((base > mu - k * sd) & (base < umbral_sup)).mean()
        filas.append([k, round(mu - k * sd, 2), round(umbral_sup, 2), round(1 - 1 / k ** 2, 4), round(dentro, 4)])
    t = pd.DataFrame(filas, columns=["k", "μ - kσ", "μ + kσ", "Chebyshev: mínimo dentro (1 - 1/k²)",
                                     "Proporción observada dentro"])
    umbral = mu + 3 * sd
    anomalos = diario[diario["sismos"] > umbral][["fecha", "sismos", "magnitud_maxima", "periodo"]].copy()
    anomalos["fecha"] = anomalos["fecha"].dt.date
    info = f"Base: días antes del terremoto. μ = {mu:.3f} sismos/día, σ = {sd:.3f}"
    return [(info, t), (f"Días anómalos (más de μ + 3σ = {umbral:.1f} sismos)", anomalos)]


# ---------------------------------------------------------------------------
# Escritura del Excel
# ---------------------------------------------------------------------------
def escribir(writer, nombre, bloques):
    fila = 0
    for titulo, tabla in bloques:
        pd.DataFrame([[titulo]]).to_excel(writer, sheet_name=nombre, startrow=fila, index=False, header=False)
        tabla.to_excel(writer, sheet_name=nombre, startrow=fila + 1, index=False)
        fila += len(tabla) + 4
    hoja = writer.sheets[nombre]
    for col in hoja.columns:
        ancho = max(len(str(c.value)) if c.value is not None and len(str(c.value)) < 45 else 12 for c in col)
        hoja.column_dimensions[col[0].column_letter].width = min(max(ancho + 2, 10), 40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasta", help="fecha de corte YYYY-MM-DD (hora local)")
    args = ap.parse_args()
    hasta = pd.Timestamp(args.hasta) if args.hasta else None

    df = cargar(hasta)
    diario = conteo_diario(df)

    resumen = pd.DataFrame({
        "Dato": ["Fecha de corte", "Primer sismo", "Último sismo", "Total de sismos",
                 "Sismos antes del terremoto", "Sismos desde el terremoto", "Días analizados"],
        "Valor": [args.hasta or "sin corte (todos los datos)", df["fecha_local"].min().date(),
                  df["fecha_local"].max().date(), len(df),
                  int((df["periodo"] == "Antes del terremoto").sum()),
                  int((df["periodo"] == "Desde el terremoto").sum()), len(diario)],
    })

    with pd.ExcelWriter(SALIDA, engine="openpyxl") as w:
        escribir(w, "Resumen", [("Resumen de los datos analizados", resumen)])
        escribir(w, "Variables", hoja_variables(df))
        escribir(w, "Contingencia", hoja_contingencia(df))
        escribir(w, "Arbol", hoja_arbol(df))
        escribir(w, "Binomial", hoja_binomial(df))
        escribir(w, "Hipergeometrica", hoja_hipergeometrica(df))
        escribir(w, "Poisson", hoja_poisson(diario))
        escribir(w, "Normal", hoja_normal(df))
        escribir(w, "Chebyshev", hoja_chebyshev(diario))
        d = diario.copy()
        d["fecha"] = d["fecha"].dt.date
        escribir(w, "Diario", [("Sismos por día (para gráficas)", d)])

    print(resumen.to_string(index=False))
    print(f"\nListo: {SALIDA}")


if __name__ == "__main__":
    main()
