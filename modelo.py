"""Modelo de la exposición: lógica, conteo, Poisson, binomial y grafos.

Los tiempos salen de la matriz del prototipo. El grafo de vecindad se queda
con los 3 vecinos más cercanos de cada nodo y Dijkstra arma la matriz D.
La ruta solo acepta una visita si el viaje, el servicio y el regreso a la
sede caben en la ventana H - R.
"""

import math
import random

NOMBRES = [
    "Sede",
    "Suba",
    "Chapinero",
    "Usaquén",
    "Centro",
    "Teusaquillo",
]

# Minutos de viaje directo. La fila es el origen y la columna el destino.
TIEMPOS = [
    [0, 25, 30, 40, 20, 15],
    [28, 0, 15, 35, 25, 20],
    [32, 18, 0, 22, 30, 25],
    [45, 38, 20, 0, 35, 40],
    [22, 24, 32, 33, 0, 12],
    [16, 21, 24, 38, 14, 0],
]

# Esquema para la pantalla. No es un mapa a escala.
POSICIONES = [
    {"x": 150, "y": 268},
    {"x": 188, "y": 78},
    {"x": 430, "y": 168},
    {"x": 560, "y": 64},
    {"x": 318, "y": 352},
    {"x": 262, "y": 196},
]

VISITAS = [
    {"nodo": 1, "zona": "Suba", "urgente": False, "sistema": "Cámaras"},
    {"nodo": 2, "zona": "Chapinero", "urgente": False, "sistema": "Alarma"},
    {"nodo": 3, "zona": "Usaquén", "urgente": False, "sistema": "Acceso"},
    {"nodo": 4, "zona": "Centro", "urgente": True, "sistema": "Cámaras"},
    {"nodo": 5, "zona": "Teusaquillo", "urgente": False, "sistema": "Alarma"},
]

TECNICOS = [
    {
        "id": "mariana",
        "nombre": "Mariana López",
        "certificado": True,
        "zonas": ["Suba", "Chapinero", "Usaquén", "Centro", "Teusaquillo"],
        "nota": "Certificada en las cinco zonas del día. Con ella sale el ejemplo de la diapositiva.",
    },
    {
        "id": "elena",
        "nombre": "Elena Vargas",
        "certificado": True,
        "zonas": ["Suba"],
        "nota": "Certificada solo en Suba. Entra a otra zona únicamente si la orden es urgente.",
    },
    {
        "id": "camilo",
        "nombre": "Camilo Duarte",
        "certificado": True,
        "zonas": ["Chapinero"],
        "nota": "Certificado solo en Chapinero.",
    },
    {
        "id": "andres",
        "nombre": "Andrés Cely",
        "certificado": False,
        "zonas": ["Centro", "Teusaquillo"],
        "nota": "Conoce Centro y Teusaquillo, pero no tiene la certificación vigente.",
    },
]

AUTORES = [
    "Juan Camilo Cartagena",
    "Julián David Alvarado",
    "José Esteban Leal",
    "Danilo Alejandro García",
]


def tecnico_por_id(tecnico_id):
    for tecnico in TECNICOS:
        if tecnico["id"] == tecnico_id:
            return tecnico
    raise KeyError(tecnico_id)


def evaluar(tecnico, visita):
    """CR1: p y (q o r). También deja la forma distribuida, que vale lo mismo."""
    p = bool(tecnico["certificado"])
    q = visita["zona"] in tecnico["zonas"]
    r = bool(visita["urgente"])
    directa = p and (q or r)
    distribuida = (p and q) or (p and r)
    return {
        "p": p,
        "q": q,
        "r": r,
        "sale": directa,
        "equivalente": distribuida,
    }


def tabla_verdad():
    filas = []
    for p in (False, True):
        for q in (False, True):
            for r in (False, True):
                filas.append(
                    {
                        "p": p,
                        "q": q,
                        "r": r,
                        "sale": p and (q or r),
                        "equivalente": (p and q) or (p and r),
                    }
                )
    return filas


def reserva_poisson(lam, umbral, tope=40):
    """Menor k tal que P(X <= k) >= umbral. X ~ Poisson(lam)."""
    if lam <= 0:
        raise ValueError("lambda debe ser mayor que 0")
    acum = 0.0
    filas = []
    elegido = None
    for k in range(tope + 1):
        prob = math.exp(-lam) * (lam ** k) / math.factorial(k)
        acum += prob
        filas.append({"k": k, "prob": prob, "acum": acum})
        if elegido is None and acum >= umbral:
            elegido = k
    if elegido is None:
        elegido = tope
    return elegido, filas


def inventario_binomial(n, p_repuesto, umbral):
    """Carga m tal que P(Y <= m) >= umbral. Y ~ Binomial(n, p_repuesto)."""
    if n < 0:
        raise ValueError("N no puede ser negativo")
    if not 0 <= p_repuesto <= 1:
        raise ValueError("la probabilidad del repuesto debe estar entre 0 y 1")
    filas = []
    acum = 0.0
    for k in range(n + 1):
        prob = math.comb(n, k) * (p_repuesto ** k) * ((1 - p_repuesto) ** (n - k))
        acum = min(1.0, acum + prob)
        filas.append({"k": k, "prob": prob, "acum": acum})
    carga = n
    cobertura = 1.0 if not filas else filas[-1]["acum"]
    for fila in filas:
        if fila["acum"] >= umbral:
            carga = fila["k"]
            cobertura = fila["acum"]
            break
    return {
        "n": n,
        "p": p_repuesto,
        "esperanza": round(n * p_repuesto, 4),
        "carga": carga,
        "cobertura": cobertura,
        "filas": filas,
    }


def construir_vecindad(tiempos, vecinos):
    cantidad = len(tiempos)
    if vecinos < 1:
        raise ValueError("cada nodo necesita al menos un vecino")
    adyacencia = [[] for _ in range(cantidad)]
    arcos = []
    for origen in range(cantidad):
        candidatos = [
            (tiempos[origen][destino], destino)
            for destino in range(cantidad)
            if destino != origen
        ]
        candidatos.sort()
        for minutos, destino in candidatos[:vecinos]:
            adyacencia[origen].append((destino, minutos))
            arcos.append({"desde": origen, "hasta": destino, "minutos": minutos})
    return adyacencia, arcos


def dijkstra(adyacencia, origen):
    cantidad = len(adyacencia)
    dist = [math.inf] * cantidad
    previo = [-1] * cantidad
    usado = [False] * cantidad
    dist[origen] = 0
    for _ in range(cantidad):
        actual = None
        mejor = math.inf
        for nodo in range(cantidad):
            if not usado[nodo] and dist[nodo] < mejor:
                mejor = dist[nodo]
                actual = nodo
        if actual is None or mejor == math.inf:
            break
        usado[actual] = True
        for destino, peso in adyacencia[actual]:
            propuesta = dist[actual] + peso
            if propuesta < dist[destino]:
                dist[destino] = propuesta
                previo[destino] = actual
    return dist, previo


def camino_de(previo, origen, destino):
    if origen == destino:
        return [origen]
    if previo[destino] == -1:
        return None
    reverso = []
    nodo = destino
    while nodo != -1:
        reverso.append(nodo)
        if nodo == origen:
            break
        nodo = previo[nodo]
    else:
        return None
    reverso.reverse()
    if reverso[0] != origen:
        return None
    return reverso


def matriz_dijkstra(adyacencia):
    cantidad = len(adyacencia)
    distancias = [[None] * cantidad for _ in range(cantidad)]
    previos = []
    for origen in range(cantidad):
        dist, previo = dijkstra(adyacencia, origen)
        previos.append(previo)
        for destino in range(cantidad):
            if dist[destino] != math.inf:
                distancias[origen][destino] = int(dist[destino])
    return distancias, previos


def _unir(tramos):
    recorrido = []
    for tramo in tramos:
        if not recorrido:
            recorrido.extend(tramo)
        else:
            recorrido.extend(tramo[1:])
    return recorrido


def planear_ruta(distancias, previos, elegibles, servicio, tope):
    """Vecino más cercano. El candidato entra solo si también cabe el regreso."""
    actual = 0
    pendientes = set(elegibles)
    ruta = [0]
    tiempo = 0
    pasos = []
    tramos = []

    while pendientes:
        alcanzables = [
            nodo for nodo in pendientes if distancias[actual][nodo] is not None
        ]
        if not alcanzables:
            break
        siguiente = min(alcanzables, key=lambda nodo: distancias[actual][nodo])
        viaje = distancias[actual][siguiente]
        regreso = distancias[siguiente][0]
        if regreso is None:
            pasos.append(
                {
                    "decision": "se_detiene",
                    "desde": actual,
                    "hasta": siguiente,
                    "viaje": viaje,
                    "motivo": "No hay camino de regreso a la sede.",
                }
            )
            break
        con_regreso = tiempo + viaje + servicio + regreso
        tramo = camino_de(previos[actual], actual, siguiente)
        if con_regreso <= tope:
            tiempo += viaje + servicio
            ruta.append(siguiente)
            pendientes.remove(siguiente)
            tramos.append(tramo)
            pasos.append(
                {
                    "decision": "entra",
                    "desde": actual,
                    "hasta": siguiente,
                    "viaje": viaje,
                    "servicio": servicio,
                    "acumulado": tiempo,
                    "con_regreso": con_regreso,
                    "camino": tramo,
                }
            )
            actual = siguiente
        else:
            pasos.append(
                {
                    "decision": "se_detiene",
                    "desde": actual,
                    "hasta": siguiente,
                    "viaje": viaje,
                    "servicio": servicio,
                    "con_regreso": con_regreso,
                    "tope": tope,
                    "camino": tramo,
                    "motivo": (
                        f"{NOMBRES[siguiente]} es el más cercano, pero con el servicio "
                        f"y el regreso suma {con_regreso} min y la ventana es {tope} min."
                    ),
                }
            )
            break

    if actual != 0:
        regreso = distancias[actual][0]
        tramo = camino_de(previos[actual], actual, 0)
        tiempo += regreso
        ruta.append(0)
        tramos.append(tramo)
        regreso_info = {"minutos": regreso, "camino": tramo}
    else:
        regreso_info = {"minutos": 0, "camino": [0]}

    return {
        "ruta": ruta,
        "nombres": [NOMBRES[nodo] for nodo in ruta],
        "tiempo": tiempo,
        "pasos": pasos,
        "regreso": regreso_info,
        "recorrido": _unir(tramos) if tramos else [0],
        "omitidas": sorted(pendientes),
    }


def muestra_poisson(lam, rng, tope=40):
    umbral = rng.random()
    acum = 0.0
    for k in range(tope + 1):
        acum += math.exp(-lam) * (lam ** k) / math.factorial(k)
        if umbral <= acum:
            return k
    return tope


def planear(
    tecnico_id="mariana",
    lam=3.0,
    c=45,
    umbral=0.90,
    jornada=480,
    servicio=40,
    vecinos=3,
    p_repuesto=0.30,
    semilla=None,
):
    if not 0 < umbral < 1:
        raise ValueError("la cobertura debe estar entre 0 y 1")
    if c <= 0 or jornada <= 0 or servicio <= 0:
        raise ValueError("los tiempos deben ser mayores que 0")

    tecnico = tecnico_por_id(tecnico_id)
    logica = []
    elegibles = []
    for visita in VISITAS:
        decision = evaluar(tecnico, visita)
        fila = {
            "nodo": visita["nodo"],
            "nombre": NOMBRES[visita["nodo"]],
            "zona": visita["zona"],
            "sistema": visita["sistema"],
            "urgente": visita["urgente"],
            **decision,
        }
        logica.append(fila)
        if decision["sale"]:
            elegibles.append(visita["nodo"])

    k, filas_poisson = reserva_poisson(lam, umbral)
    reserva = k * c
    ventana = jornada - reserva
    if ventana < 0:
        ventana = 0

    adyacencia, arcos = construir_vecindad(TIEMPOS, min(vecinos, len(NOMBRES) - 1))
    distancias, previos = matriz_dijkstra(adyacencia)
    ruta = planear_ruta(distancias, previos, elegibles, servicio, ventana)
    visitas_ruta = max(0, len(ruta["ruta"]) - 2)
    binomial = inventario_binomial(visitas_ruta, p_repuesto, umbral)

    equipo = []
    for persona in TECNICOS:
        habilitadas = sum(1 for visita in VISITAS if evaluar(persona, visita)["sale"])
        equipo.append(
            {
                "id": persona["id"],
                "nombre": persona["nombre"],
                "certificado": persona["certificado"],
                "zonas": list(persona["zonas"]),
                "nota": persona["nota"],
                "habilitadas": habilitadas,
                "seleccionado": persona["id"] == tecnico["id"],
            }
        )

    n_demo = len(VISITAS)
    dia = None
    if semilla is not None:
        rng = random.Random(semilla)
        fallas = muestra_poisson(lam, rng)
        usados = sum(1 for _ in range(visitas_ruta) if rng.random() < p_repuesto)
        dia = {
            "semilla": semilla,
            "fallas": fallas,
            "cabe_en_reserva": fallas <= k,
            "repuestos": usados,
            "cabe_en_carga": usados <= binomial["carga"],
        }

    return {
        "autores": AUTORES,
        "tecnico": {
            "id": tecnico["id"],
            "nombre": tecnico["nombre"],
            "certificado": tecnico["certificado"],
            "zonas": list(tecnico["zonas"]),
            "nota": tecnico["nota"],
        },
        "equipo": equipo,
        "logica": logica,
        "verdad": tabla_verdad(),
        "conteo": {
            "visitas": n_demo,
            "rutas": math.factorial(n_demo),
            "rutas_10": math.factorial(10),
            "arcos_completos": (n_demo + 1) * n_demo,
            "arcos_vecindad": len(arcos),
            "arcos_10": 11 * 10,
            "vecinos": min(vecinos, len(NOMBRES) - 1),
        },
        "poisson": {
            "lam": lam,
            "c": c,
            "umbral": umbral,
            "k": k,
            "reserva": reserva,
            "filas": filas_poisson[: k + 2],
        },
        "jornada": jornada,
        "ventana": ventana,
        "servicio": servicio,
        "binomial": binomial,
        "nodos": [
            {"id": i, "nombre": NOMBRES[i], **POSICIONES[i], "sede": i == 0}
            for i in range(len(NOMBRES))
        ],
        "tiempos": TIEMPOS,
        "arcos": arcos,
        "distancias": distancias,
        "ruta": ruta,
        "tiempo_dia": ruta["tiempo"] + reserva,
        "cumple": ruta["tiempo"] <= ventana and ruta["tiempo"] + reserva <= jornada,
        "dia": dia,
    }


def verificar():
    """El caso de la diapositiva: k = 5, R = 225 y esa secuencia de visitas."""
    resultado = planear()
    poisson = resultado["poisson"]
    assert poisson["k"] == 5
    assert poisson["reserva"] == 225
    assert resultado["ventana"] == 255
    assert round(poisson["filas"][4]["acum"] * 100, 1) == 81.5
    assert round(poisson["filas"][5]["acum"] * 100, 1) == 91.6
    assert resultado["ruta"]["nombres"] == [
        "Sede",
        "Teusaquillo",
        "Centro",
        "Suba",
        "Sede",
    ]
    assert resultado["ruta"]["tiempo"] == 209
    assert resultado["tiempo_dia"] == 434
    assert resultado["cumple"] is True
    assert resultado["conteo"]["rutas_10"] == 3628800
    assert resultado["conteo"]["arcos_vecindad"] == 18
    assert resultado["binomial"]["n"] == 3
    assert resultado["binomial"]["esperanza"] == 0.9
    assert resultado["binomial"]["carga"] == 2
    for persona in TECNICOS:
        for visita in VISITAS:
            decision = evaluar(persona, visita)
            assert decision["sale"] == decision["equivalente"]
    assert evaluar(tecnico_por_id("andres"), VISITAS[0])["sale"] is False
    assert evaluar(tecnico_por_id("elena"), VISITAS[3])["sale"] is True
    assert evaluar(tecnico_por_id("elena"), VISITAS[1])["sale"] is False
    return resultado


def miles(valor):
    return f"{valor:,}".replace(",", ".")


def informe(resultado):
    ruta = " -> ".join(resultado["ruta"]["nombres"])
    poisson = resultado["poisson"]
    binomial = resultado["binomial"]
    lineas = [
        "SIMULADOR DE RUTAS  ·  MATEMATICA DISCRETA",
        ", ".join(resultado["autores"]),
        "",
        f"Tecnico: {resultado['tecnico']['nombre']}",
        "Regla: sale solo si esta certificado y (el cliente esta en su zona o la orden es urgente).",
        "",
        "[Conteo]",
        f"Con {resultado['conteo']['visitas']} visitas hay {miles(resultado['conteo']['rutas'])} recorridos.",
        f"Con 10 visitas serian {miles(resultado['conteo']['rutas_10'])} recorridos. Por eso no se prueban todos.",
        f"Vecindad de {resultado['conteo']['vecinos']}: {resultado['conteo']['arcos_vecindad']} arcos, en vez de {resultado['conteo']['arcos_completos']}.",
        "",
        "[Poisson]",
        f"Lambda = {poisson['lam']} fallas/dia. Reserva al {poisson['umbral'] * 100:.0f} %: k = {poisson['k']}.",
        f"k = 4 llega a {poisson['filas'][4]['acum'] * 100:.1f} % y no alcanza.",
        f"k = 5 llega a {poisson['filas'][5]['acum'] * 100:.1f} %.",
        f"Reserva Poisson (90%): {poisson['k']} fallas ({poisson['reserva']} min)",
        f"Ventana preventiva: {resultado['ventana']} min disponibles",
        "",
        "[Ruta]",
        ruta,
        f"Tiempo de visitas y desplazamientos: {resultado['ruta']['tiempo']} min.",
        f"Dia completo, con la reserva: {resultado['tiempo_dia']} min de {resultado['jornada']}.",
        "Cumple la jornada de 480 min." if resultado["cumple"] else "No cabe en la jornada.",
        "",
        "[Repuestos]",
        f"N = {binomial['n']} visitas en la ruta. p = {binomial['p']}.",
        f"Esperados E[Y] = {binomial['esperanza']}. Se cargan {binomial['carga']} para cubrir el {binomial['cobertura'] * 100:.1f} %.",
    ]
    return "\n".join(lineas)
