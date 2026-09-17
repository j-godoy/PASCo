#!/usr/bin/env python3
"""
run_batch.py
============

Corre PASCo.py sobre una lista de archivos de configuracion (los que arma
la persona a mano, separados entre los que van en modo "epa" y los que van
en modo "states"), repitiendo cada corrida N veces, y arma una tabla resumen
con el promedio, mediana y desvio estandar de May/Must/Total, lista para
pegar en el escrito de la tesis.

Por que la medicion vive en PASCo.py y la orquestacion aca
------------------------------------------------------------
- La frontera entre "parte May" (exploracion de estados/precondiciones,
  reduccion de combinaciones, try_init) y "parte Must" (analyze_must_transitions
  + construccion/render de los grafos may y must) solo la conoce PASCo.py:
  es el unico lugar donde se sabe exactamente donde termina una y empieza
  la otra. Por eso los cronometros (time.time()) estan puestos adentro de
  PASCo.py (ver self.time_may / self.time_must en run_mode(), y la linea
  "TIMING_SUMMARY|..." que imprime run()).
- Lo que SI es trabajo de un script batch es la orquestacion: iterar la
  lista de configs, correr cada una varias veces, y agregar (promedio,
  mediana, desvio) todos los resultados en una unica tabla. Esa parte no
  necesita saber nada del funcionamiento interno de PASCo, asi que va aca.

Uso
---
1. Completar las listas CONFIGS_EPA y CONFIGS_STATES mas abajo con los
   nombres de config que quieras correr (el mismo string que le pasarias
   a --file, ej. "HelloBlockchainConfig").
2. Definir cuantas veces se repite cada corrida (ver REPETITIONS mas
   abajo; aplica por igual a todos los configs de ambas listas).
3. Ejecutar:

       python run_batch.py

   Opcionalmente se puede fijar parametros extra que se propagan a cada
   corrida de PASCo.py (ver EXTRA_ARGS).
4. Al terminar, en "resultados_tesis/" quedan:
   - timing_raw_<fecha>.csv       -> una fila por CADA corrida individual
                                      (por si querés graficar la dispersión).
   - timing_summary_<fecha>.csv   -> una fila por config+mode, con
                                      promedio/mediana/desvío de May, Must
                                      y Total, mas la cantidad de corridas.
   - timing_summary_<fecha>.txt   -> la misma tabla en formato texto
                                      (mean ± std), lista para pegar.

Cada corrida individual sigue generando ademas sus propios archivos de
resultados (grafos, csv de queries, etc.) en la carpeta de siempre
(graph/<run_id>/...), esto no cambia nada de eso.
"""

import csv
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 1) LISTA DE CONFIGS A CORRER (completar a mano)
# ---------------------------------------------------------------------------
# Poner aca el nombre del config tal cual se le pasa a --file
# (ej. "HelloBlockchainConfig", sin .py y sin la carpeta "Configs/").

CONFIGS_EPA = [
    # 1
    # "AssetTransferConfig",
    # "BasicProvenanceConfig",
    # "DefectiveComponentCounterConfig",
    # "DigitalLockerConfig",
    # "FrequentFlyerRewardsCalculatorConfig",
    # "HelloBlockchainConfig",
    # "RefrigeratedTransportationConfig",
    # "RoomThermostatConfig",
    # "SimpleMarketplaceConfig",

    # 2
    "CrowdfundingTime_BaseBalanceFixConfig",
    # "CrowdfundingTime_BaseBalanceConfig",
    # "EPXCrowdsaleConfig",
    "EPXCrowdsaleIsCrowdsaleClosedConfig",
    ## "EscrowVaultConfig",
    # "RefundEscrowConfig",
    ## "SimpleAuctionHBConfig",
    ## "ValidatorAuctionConfig",
    # "RockPaperScissorsOneWinnerConfig"
]

CONFIGS_STATES = [
    # "AuctionConfig",
    # "AuctionTime_FixConfig",
    # "AuctionEndedConfig",
    # "EPXCrowdsaleConfig",
    ## "EscrowVaultConfig",
    # "RefundEscrowConfig",
    # "RockPaperScissorsConfig",
    # "SimpleAuctionTimeConfig",
    # "SimpleAuctionEndedConfig",
    ## "ValidatorAuctionConfig"

    #   - Bug corral
    ##  - no podemos identificar estado concreto
]

# 2) REPETICIONES: cuantas veces se corre cada config+mode para promediar.
REPETITIONS = 1

# ---------------------------------------------------------------------------
# 3) Parametros extra que se le pasan a TODAS las corridas de PASCo.py
#    (ademas de --file, --mode y --must, que van siempre).
#    Agregar/sacar flags segun necesites (ej. "--time_out", "600").
# ---------------------------------------------------------------------------
EXTRA_ARGS = [
    "--must"
    # "--time_out", "600",
    # "--txBound", "8",
]

# Carpeta donde queda la tabla final (no confundir con --folder_store_results
# de PASCo.py, que sigue siendo "graph" salvo que la cambies con EXTRA_ARGS).
OUTPUT_DIR = Path("resultados_tesis")

# Ruta al script PASCo.py (por defecto, al lado de este script).
PASCO_SCRIPT = Path(__file__).parent / "PASCo.py"

TIMING_LINE_RE = re.compile(
    r"^TIMING_SUMMARY\|(?P<config>.+)\|(?P<mode>.+)\|(?P<may>[\d.]+)\|(?P<must>[\d.]+)\|(?P<total>[\d.]+)$"
)


def run_single(config_file: str, mode: str, repetition: int) -> dict | None:
    """Corre PASCo.py UNA vez para un config+mode y devuelve la fila de
    timing parseada desde la linea TIMING_SUMMARY que imprime PASCo.py.
    Devuelve None si la corrida fallo o no se pudo parsear el resultado."""

    cmd = [
        sys.executable, str(PASCO_SCRIPT),
        "--file", config_file,
        "--mode", mode,
        # "--must",
        *EXTRA_ARGS,
    ]

    print(f"\n=== Corriendo: {config_file} ({mode}) - repeticion {repetition} ===")
    print("  ", " ".join(cmd))

    log_path = OUTPUT_DIR / f"{config_file}_{mode}_rep{repetition}.log"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timing_row = None
    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        for line in process.stdout:
            log_file.write(line)
            print(line, end="")  # eco en vivo, util para correr algo largo
            match = TIMING_LINE_RE.match(line.strip())
            if match:
                timing_row = {
                    "Config": match.group("config"),
                    "Mode": match.group("mode"),
                    "Repeticion": repetition,
                    "May(s)": float(match.group("may")),
                    "Must(s)": float(match.group("must")),
                    "Total(s)": float(match.group("total")),
                }
        process.wait()

    if process.returncode != 0:
        print(f"  [!] {config_file} ({mode}) rep {repetition} termino con error (ver {log_path})")

    if timing_row is None:
        print(f"  [!] No se encontro la linea TIMING_SUMMARY para {config_file} ({mode}) rep {repetition}")

    return timing_row


def summarize(config_file: str, mode: str, rows: list[dict]) -> dict:
    """Agrega N corridas de un mismo config+mode en promedio/mediana/desvio
    estandar para May, Must y Total."""

    def stats(values: list[float]) -> dict:
        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            # stdev necesita al menos 2 valores; con 1 sola corrida no hay
            # desvio que calcular (queda en 0.0, y N=1 avisa que no se promedio).
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        }

    may_vals = [r["May(s)"] for r in rows]
    must_vals = [r["Must(s)"] for r in rows]
    total_vals = [r["Total(s)"] for r in rows]

    may_stats = stats(may_vals)
    must_stats = stats(must_vals)
    total_stats = stats(total_vals)

    return {
        "Config": config_file,
        "Mode": mode,
        "N": len(rows),
        "May_mean(s)": may_stats["mean"],
        "May_median(s)": may_stats["median"],
        "May_std(s)": may_stats["std"],
        "Must_mean(s)": must_stats["mean"],
        "Must_median(s)": must_stats["median"],
        "Must_std(s)": must_stats["std"],
        "Total_mean(s)": total_stats["mean"],
        "Total_median(s)": total_stats["median"],
        "Total_std(s)": total_stats["std"],
    }


def main():
    jobs = [(c, "epa") for c in CONFIGS_EPA] + [(c, "states") for c in CONFIGS_STATES]

    if not jobs:
        print("No hay configs cargados en CONFIGS_EPA / CONFIGS_STATES. "
              "Completa esas listas al principio del script y volve a correr.")
        return

    raw_rows = []       # una fila por cada corrida individual
    summary_rows = []   # una fila por config+mode, ya agregada

    for config_file, mode in jobs:
        job_rows = []
        for rep in range(1, REPETITIONS + 1):
            row = run_single(config_file, mode, rep)
            if row is not None:
                job_rows.append(row)
                raw_rows.append(row)

        if not job_rows:
            print(f"  [!] {config_file} ({mode}): ninguna repeticion dio resultado, se omite del resumen.")
            continue

        if len(job_rows) < REPETITIONS:
            print(f"  [!] {config_file} ({mode}): solo {len(job_rows)}/{REPETITIONS} "
                  "repeticiones dieron resultado; el promedio se calcula con esas.")

        summary_rows.append(summarize(config_file, mode, job_rows))

    if not summary_rows:
        print("\nNo se obtuvo ningun resultado de timing. Revisa los logs en "
              f"{OUTPUT_DIR}/*.log")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Datos crudos: una fila por corrida individual ---------------------
    raw_csv_path = OUTPUT_DIR / f"timing_raw_{timestamp}.csv"
    raw_fieldnames = ["Config", "Mode", "Repeticion", "May(s)", "Must(s)", "Total(s)"]
    with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=raw_fieldnames)
        writer.writeheader()
        writer.writerows(raw_rows)

    # --- Resumen agregado: una fila por config+mode -------------------------
    summary_csv_path = OUTPUT_DIR / f"timing_summary_{timestamp}.csv"
    summary_fieldnames = [
        "Config", "Mode", "N",
        "May_mean(s)", "May_median(s)", "May_std(s)",
        "Must_mean(s)", "Must_median(s)", "Must_std(s)",
        "Total_mean(s)", "Total_median(s)", "Total_std(s)",
    ]
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    # --- Version .txt en formato "tabla" (mean ± std), lista para pegar ----
    summary_txt_path = OUTPUT_DIR / f"timing_summary_{timestamp}.txt"
    with open(summary_txt_path, "w", encoding="utf-8") as f:
        header = (
            f"{'Config':<30} | {'Mode':<7} | {'N':>2} | "
            f"{'May (s)':>18} | {'Must (s)':>18} | {'Total (s)':>18}"
        )
        f.write(header + "\n")
        f.write("-" * len(header) + "\n")
        for row in summary_rows:
            may_str = f"{row['May_mean(s)']:.2f} ± {row['May_std(s)']:.2f}"
            must_str = f"{row['Must_mean(s)']:.2f} ± {row['Must_std(s)']:.2f}"
            total_str = f"{row['Total_mean(s)']:.2f} ± {row['Total_std(s)']:.2f}"
            f.write(
                f"{row['Config']:<30} | {row['Mode']:<7} | {row['N']:>2} | "
                f"{may_str:>18} | {must_str:>18} | {total_str:>18}\n"
            )
        f.write("\n(N=1 significa que esa fila no se promedio; el ± queda en 0.00)\n")

    print(f"\nListo. Resultados guardados en:")
    print(f"  Datos crudos (todas las corridas): {raw_csv_path}")
    print(f"  Resumen (promedio/mediana/std):     {summary_csv_path}")
    print(f"  Resumen en formato tabla:           {summary_txt_path}")


if __name__ == "__main__":
    main()