"""
Genera las gráficas del trabajo escrito a partir de data/sismos.csv.
Las guarda en analisis/graficas/ como PNG (listas para pegar en Word).

Uso (desde la carpeta principal del proyecto):
    python analisis/graficas.py
    python analisis/graficas.py --hasta 2026-12-01

Requisitos:
    python -m pip install pandas matplotlib
"""
import argparse
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "sismos.csv"
DIR = RAIZ / "analisis" / "graficas"
TERREMOTO = pd.Timestamp("2026-10-09")

AZUL, NARANJA = "#2a78d6", "#eb6834"
TINTA, TINTA2, MUTED, GRID, EJE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

plt.rcParams.update({
    "font.family": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "font.size": 10, "axes.edgecolor": EJE, "axes.labelcolor": TINTA2,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 200,
})


def titulo(ax, t, sub=None):
    ax.set_title(t, loc="left", fontsize=12, fontweight="bold", color=TINTA, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=TINTA2)


def guardar(fig, nombre):
    fig.tight_layout()
    fig.savefig(DIR / nombre, facecolor="white")
    plt.close(fig)
    print("  ", nombre)


def poisson(k, lam):
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def binomial(x, n, p):
    return math.comb(n, x) * p ** x * (1 - p) ** (n - x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasta")
    args = ap.parse_args()
    DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["fecha_local"] = pd.to_datetime(df["fecha_local"])
    if args.hasta:
        df = df[df["fecha_local"] <= pd.Timestamp(args.hasta)]
    antes = df[df["fecha_local"] < TERREMOTO]
    desde = df[df["fecha_local"] >= TERREMOTO]

    dias = pd.date_range(df["fecha_local"].min(), df["fecha_local"].max(), freq="D")
    diario = df.groupby("fecha_local").size().reindex(dias, fill_value=0)
    base = diario[diario.index < TERREMOTO]
    mu, sd = base.mean(), base.std()
    umbral = mu + 3 * sd

    # 1. Sismos por día con el umbral de Chebyshev
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    colores = [NARANJA if v > umbral else AZUL for v in diario.values]
    ax.bar(diario.index, diario.values, width=1.0, color=colores, linewidth=0)
    ax.axhline(umbral, color=TINTA2, linewidth=1, linestyle="--")
    ax.text(diario.index[5], umbral + 3, f"Umbral μ + 3σ = {umbral:.1f} sismos/día", fontsize=8.5, color=TINTA2)
    ax.annotate("Terremoto del 9 de octubre", xy=(TERREMOTO, diario.max()), xytext=(TERREMOTO - pd.Timedelta(days=150), diario.max() * 0.85),
                fontsize=8.5, color=TINTA, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_ylabel("Sismos por día")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=AZUL, label="Día normal"), Patch(color=NARANJA, label="Día anómalo (supera el umbral)")],
              frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 0.92))
    titulo(ax, "El terremoto multiplicó la actividad diaria muy por encima del umbral",
           f"Sismos por día en Panamá y alrededores, {dias[0]:%d/%m/%Y} a {dias[-1]:%d/%m/%Y}")
    guardar(fig, "fig1_sismos_por_dia.png")

    # 2. Poisson observado vs teórico (antes del terremoto)
    lam = base.mean()
    obs = base.value_counts()
    ks = list(range(0, 13))
    o = [int(obs.get(k, 0)) for k in ks[:-1]] + [int(obs[obs.index >= 12].sum())]
    e = [poisson(k, lam) * len(base) for k in ks[:-1]] + [(1 - sum(poisson(k, lam) for k in range(12))) * len(base)]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    w = 0.4
    ax.bar([k - w / 2 for k in ks], o, width=w - 0.04, color=AZUL, label="Días observados")
    ax.bar([k + w / 2 for k in ks], e, width=w - 0.04, color=NARANJA, label=f"Días esperados con Poisson (λ = {lam:.2f})")
    ax.set_xticks(ks, [str(k) for k in ks[:-1]] + ["12+"])
    ax.set_xlabel("Sismos en un día (k)")
    ax.set_ylabel("Número de días")
    ax.legend(frameon=False, fontsize=8.5)
    titulo(ax, "Poisson se aproxima, pero hubo más días extremos de lo esperado",
           f"Antes del terremoto: {len(base)} días, del {base.index[0]:%d/%m/%Y} al {base.index[-1]:%d/%m/%Y}")
    guardar(fig, "fig2_poisson_antes.png")

    # 3. Mapa de epicentros
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for g, c, lab in [(antes, AZUL, f"Antes del terremoto ({len(antes)})"), (desde, NARANJA, f"Desde el terremoto ({len(desde)})")]:
        ax.scatter(g["longitud"], g["latitud"], s=(g["magnitud"] - 2) ** 2.4 * 4, color=c, alpha=0.45,
                   edgecolors="white", linewidths=0.3, label=lab)
    ax.set_xlim(-84, -77)
    ax.set_ylim(5, 10)
    ax.set_aspect("equal")
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    for x, y, t in [(-80.9, 6.9, "Azuero-Soná"), (-82.9, 9.5, "Chiriquí y\nfrontera"), (-78.2, 9.4, "Este y\nDarién")]:
        ax.text(x, y, t, fontsize=8.5, color=TINTA2, ha="center")
    leg = ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    for h in leg.legend_handles:
        h.set_sizes([30])
    titulo(ax, "Las réplicas se concentran en Azuero; la frontera tiene actividad constante",
           "Epicentros; el tamaño del punto indica la magnitud")
    guardar(fig, "fig3_mapa_epicentros.png")

    # 4. P(mag >= 4 | región)
    p = df.groupby("region")["magnitud"].apply(lambda s: (s >= 4).mean()).sort_values()
    n = df["region"].value_counts()
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ax.barh(p.index, p.values, color=AZUL, height=0.55)
    for i, (r, v) in enumerate(p.items()):
        ax.text(v + 0.008, i, f"{v:.1%}  (n = {n[r]})", va="center", fontsize=8.5, color=TINTA2)
    ax.set_xlim(0, max(p.values) * 1.35)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", visible=False)
    titulo(ax, "La probabilidad de un sismo fuerte cambia según la región",
           "P(magnitud ≥ 4.0 | región)")
    guardar(fig, "fig4_prob_condicional_region.png")

    # 5. Binomial antes vs desde
    xs = list(range(0, 13))
    pa, pd_ = (antes["magnitud"] >= 4).mean(), (desde["magnitud"] >= 4).mean()
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.bar([x - w / 2 for x in xs], [binomial(x, 20, pa) for x in xs], width=w - 0.04, color=AZUL, label=f"Antes del terremoto (p = {pa:.3f})")
    ax.bar([x + w / 2 for x in xs], [binomial(x, 20, pd_) for x in xs], width=w - 0.04, color=NARANJA, label=f"Desde el terremoto (p = {pd_:.3f})")
    ax.set_xticks(xs)
    ax.set_xlabel("x = sismos de magnitud ≥ 4.0 entre 20 sismos")
    ax.set_ylabel("P(X = x)")
    ax.legend(frameon=False, fontsize=8.5)
    titulo(ax, "Después del terremoto se esperan más sismos fuertes en cada grupo de 20",
           "Distribución binomial con n = 20")
    guardar(fig, "fig5_binomial.png")

    # 6 y 7. Histogramas con curva normal
    for col, nombre, etiqueta, bins, t in [
        ("magnitud", "fig6_normal_magnitud.png", "Magnitud", [2.5 + 0.2 * i for i in range(27)],
         "La magnitud se aproxima a una normal, recortada en 2.5"),
        ("profundidad_km", "fig7_normal_profundidad.png", "Profundidad (km)", list(range(0, 81, 4)),
         "La profundidad no es normal: casi todos los sismos son superficiales"),
    ]:
        s = df[col]
        m, d = s.mean(), s.std()
        fig, ax = plt.subplots(figsize=(7.5, 3.2))
        ax.hist(s.clip(upper=bins[-1]), bins=bins, density=True, color=AZUL, edgecolor="white", linewidth=0.6,
                label="Datos observados")
        xs_ = [bins[0] + (bins[-1] - bins[0]) * i / 300 for i in range(301)]
        ax.plot(xs_, [math.exp(-((x - m) / d) ** 2 / 2) / (d * math.sqrt(2 * math.pi)) for x in xs_],
                color=NARANJA, linewidth=2, label=f"Normal (μ = {m:.2f}, σ = {d:.2f})")
        ax.set_xlabel(etiqueta + (" (los valores mayores a 80 se agrupan al final)" if col == "profundidad_km" else ""))
        ax.set_ylabel("Densidad")
        ax.legend(frameon=False, fontsize=8.5)
        titulo(ax, t, f"Histograma de {len(s)} sismos con la curva normal ajustada")
        guardar(fig, nombre)


if __name__ == "__main__":
    print("Generando gráficas en analisis/graficas/ ...")
    main()
