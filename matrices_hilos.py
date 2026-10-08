"""
MULTIPLICACION DE MATRICES CON HILOS  -  HPC
=============================================
Version 1 (fila x columna):
    Cada hilo recibe UNA fila de A y UNA columna de B y calcula UNA celda de C.
Version 2 (dos filas x dos columnas):
    Cada hilo recibe DOS filas de A y DOS columnas de B y calcula un bloque 2x2 de C.

Los hilos se lanzan por lotes: 2 a la vez, luego 4, 8 y 16.
    lote = crear N hilos -> start() a todos -> join() a todos -> siguiente lote
Se mide el tiempo total de cada caso y el speed-up contra la version secuencial:
    speed-up = T_secuencial / T_con_hilos

Ejecutar:  python matrices_hilos.py            (matriz 100x100 por defecto)
           python matrices_hilos.py 60         (matriz 60x60, debe ser par)
"""
import csv
import random
import statistics
import sys
import threading
import time

import matplotlib
matplotlib.use("Agg")          # guarda las graficas en PNG sin abrir ventana
import matplotlib.pyplot as plt

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100   # tamano de las matrices N x N
HILOS = [2, 4, 8, 16]                                 # hilos lanzados "cada vez"
REPETICIONES = 3                                      # se toma la mediana de 3 corridas


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------
def crear_matriz(n, semilla):
    rnd = random.Random(semilla)
    return [[rnd.randint(0, 9) for _ in range(n)] for _ in range(n)]


def transponer(M):
    """Las columnas de B se vuelven filas de Bt: Bt[j] es la columna j de B."""
    return [list(col) for col in zip(*M)]


def matriz_vacia(n):
    return [[0] * n for _ in range(n)]


# ---------------------------------------------------------------------------
# PUNTO 1: funcion que toma una fila y una columna y las multiplica
# ---------------------------------------------------------------------------
def multiplicar_fila_columna(fila, columna):
    resultado = 0
    for a, b in zip(fila, columna):
        resultado += a * b
    return resultado


# ADVERTENCIA: version con dos filas y dos columnas (bloque 2x2)
def multiplicar_2filas_2columnas(fila1, fila2, col1, col2):
    return (multiplicar_fila_columna(fila1, col1), multiplicar_fila_columna(fila1, col2),
            multiplicar_fila_columna(fila2, col1), multiplicar_fila_columna(fila2, col2))


# ---------------------------------------------------------------------------
# PUNTO 2: lo que ejecuta cada hilo
# Un hilo no puede "retornar" un valor, asi que escribe su resultado en C.
# No hace falta Lock: cada hilo escribe en celdas DISTINTAS de C, nunca la misma.
# ---------------------------------------------------------------------------
def tarea_v1(A, Bt, C, i, j):
    C[i][j] = multiplicar_fila_columna(A[i], Bt[j])


def tarea_v2(A, Bt, C, i, j):
    (C[i][j], C[i][j + 1],
     C[i + 1][j], C[i + 1][j + 1]) = multiplicar_2filas_2columnas(A[i], A[i + 1], Bt[j], Bt[j + 1])


def lista_tareas(version, n):
    """Devuelve las coordenadas (i, j) que debe calcular cada hilo."""
    paso = 1 if version == 1 else 2
    return [(i, j) for i in range(0, n, paso) for j in range(0, n, paso)]


# ---------------------------------------------------------------------------
# PUNTO 3: ejecucion lanzando num_hilos hilos cada vez
# ---------------------------------------------------------------------------
def multiplicar_con_hilos(A, Bt, version, num_hilos):
    n = len(A)
    C = matriz_vacia(n)
    funcion = tarea_v1 if version == 1 else tarea_v2
    tareas = lista_tareas(version, n)

    for inicio in range(0, len(tareas), num_hilos):
        lote = [threading.Thread(target=funcion, args=(A, Bt, C, i, j))
                for i, j in tareas[inicio:inicio + num_hilos]]
        for hilo in lote:
            hilo.start()          # arrancan los num_hilos hilos del lote
        for hilo in lote:
            hilo.join()           # se espera a que TODOS terminen antes del siguiente lote
    return C, len(tareas)


def multiplicar_secuencial(A, Bt, version):
    """Lo mismo pero sin hilos: es la linea base para el speed-up."""
    n = len(A)
    C = matriz_vacia(n)
    funcion = tarea_v1 if version == 1 else tarea_v2
    for i, j in lista_tareas(version, n):
        funcion(A, Bt, C, i, j)
    return C


def medir(funcion, *args):
    """PUNTO 4: tiempo total (mediana de REPETICIONES corridas) con perf_counter."""
    tiempos = []
    resultado = None
    for _ in range(REPETICIONES):
        t0 = time.perf_counter()
        resultado = funcion(*args)
        tiempos.append(time.perf_counter() - t0)
    return statistics.median(tiempos), resultado


# ---------------------------------------------------------------------------
# PUNTO 5: graficas
# ---------------------------------------------------------------------------
AZUL, NARANJA, TINTA, TINTA_SUAVE, GRILLA = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a63", "#e6e5df"


def graficar(resultados, t_seq):
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRILLA, "axes.labelcolor": TINTA,
                         "xtick.color": TINTA_SUAVE, "ytick.color": TINTA_SUAVE})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    x = list(range(len(HILOS)))
    ancho = 0.38

    for ax, clave, titulo, ylabel in [
        (ax1, "tiempo", f"Tiempo total ({N}x{N})", "segundos"),
        (ax2, "speedup", "Aceleración (speed-up)", "T secuencial / T con hilos"),
    ]:
        for k, (version, color, nombre) in enumerate([(1, AZUL, "V1: fila × columna"),
                                                      (2, NARANJA, "V2: 2 filas × 2 columnas")]):
            valores = [r[clave] for r in resultados if r["version"] == version]
            pos = [p + (k - 0.5) * ancho for p in x]
            barras = ax.bar(pos, valores, ancho - 0.04, color=color, label=nombre)
            ax.bar_label(barras, fmt="%.2f", fontsize=8, color=TINTA_SUAVE, padding=2)
        ax.set_xticks(x, [f"{h} hilos" for h in HILOS])
        ax.set_title(titulo, color=TINTA, loc="left", fontweight="bold")
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=GRILLA)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)

    for version, color, estilo in [(1, AZUL, "--"), (2, NARANJA, ":")]:
        ax1.axhline(t_seq[version], color=color, linestyle=estilo, linewidth=1.5)
    ax1.set_xlabel(f"líneas punteadas abajo = tiempo secuencial "
                   f"(V1 {t_seq[1]:.3f} s, V2 {t_seq[2]:.3f} s)", color=TINTA_SUAVE, fontsize=8)
    ax2.axhline(1, color=TINTA_SUAVE, linestyle="--", linewidth=1)
    ax2.annotate("speed-up = 1 (igual que secuencial)", (-0.45, 1), color=TINTA_SUAVE,
                 fontsize=8, va="bottom")
    manejadores, etiquetas = ax1.get_legend_handles_labels()
    fig.legend(manejadores, etiquetas, frameon=False, loc="lower center", ncol=2)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig("graficas_speedup.png", dpi=130)
    print("Grafica guardada en graficas_speedup.png")


# ---------------------------------------------------------------------------
def main():
    if N % 2:
        sys.exit("N debe ser par para la version 2 (bloques 2x2)")
    print(f"Matrices {N}x{N} | {REPETICIONES} repeticiones por caso (se usa la mediana)\n")
    A, B = crear_matriz(N, 1), crear_matriz(N, 2)
    Bt = transponer(B)

    t_seq, C_ref = {}, None
    for version in (1, 2):
        t_seq[version], C_ref = medir(multiplicar_secuencial, A, Bt, version)
        print(f"V{version} secuencial: {t_seq[version]:.4f} s")

    resultados = []
    print(f"\n{'Version':<9}{'Hilos/lote':>11}{'Hilos creados':>15}{'Tiempo (s)':>12}{'Speed-up':>10}")
    for version in (1, 2):
        for h in HILOS:
            t, (C, creados) = medir(multiplicar_con_hilos, A, Bt, version, h)
            assert C == C_ref, "El resultado con hilos no coincide con el secuencial"
            speedup = t_seq[version] / t
            resultados.append({"version": version, "hilos": h, "hilos_creados": creados,
                               "tiempo": t, "speedup": speedup})
            print(f"V{version:<8}{h:>11}{creados:>15}{t:>12.4f}{speedup:>10.3f}")

    with open("resultados.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=resultados[0].keys())
        w.writeheader()
        w.writerows(resultados)
    print("\nResultados guardados en resultados.csv (todas las C verificadas contra la secuencial)")
    graficar(resultados, t_seq)


if __name__ == "__main__":
    main()
