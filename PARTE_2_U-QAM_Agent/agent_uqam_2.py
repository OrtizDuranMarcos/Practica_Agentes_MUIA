import os
import sys
import json
import asyncio
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool
import metrics_w_example as metrics_lib
from debug_plugin import UQAMDebugPlugin

load_dotenv()

retry_config = types.HttpRetryOptions(
    attempts=5, exp_base=7, initial_delay=1, http_status_codes=[429, 500, 503, 504],
)

def cargar_textos(ruta_json="PARTE_2_U-QAM_Agent/textos.json"):
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# --- FUNCIONES DE PUNTUACIÓN PARCIAL (SCORING FUNCTIONS) ---

def score_range(value, optimal_min, optimal_max, tolerance_low, tolerance_high):
    """
    Función genérica de puntuación trapezoidal.
    - Dentro de [optimal_min, optimal_max] -> 100 pts
    - Cae linealmente hasta 0 en los límites de tolerancia.
    """
    if optimal_min <= value <= optimal_max:
        return 100.0
    
    if value < optimal_min:
        if value <= tolerance_low: return 0.0
        # Regla de tres simple para la caída inferior
        return 100 * (value - tolerance_low) / (optimal_min - tolerance_low)
    
    if value > optimal_max:
        if value >= tolerance_high: return 0.0
        # Regla de tres simple para la caída superior
        return 100 * (tolerance_high - value) / (tolerance_high - optimal_max)
    
    return 0.0

# --- LÓGICA U-QAM (MÉTODO PONDERADO) ---
def calculate_uqam_weighted(text: str) -> dict:
    """
    Calcula el U-QAM Score usando MEDIA PONDERADA.
    Cada métrica se evalúa de 0 a 100 según su proximidad al rango óptimo.
    Luego se ponderan para el score final.
    """
    try:
        m = metrics_lib.compute_metrics(text)
    except Exception as e:
        return {"error": str(e), "score": 0}

    # 1. Score LMO (Peso 25%)
    # Óptimo: 16-23. Tolerancia: 10-35 (Se le da un rango mayor al que proporciona la tabla, dando un máximo y un mínimo)
    s_lmo = score_range(m.lmo, 16, 23, 10, 35)
    
    # 2. Score CV (Peso 20%)
    # Óptimo: 0.5-1.0. Tolerancia: 0.3-1.3
    s_cv = score_range(m.cv_sentence_len, 0.5, 1.0, 0.3, 1.3)
    
    # 3. Score Z-Normalidad (Peso 15%)
    # Óptimo: -1 a 1. Tolerancia: -3 a 3
    s_z = score_range(m.z_normality, -1, 1, -3, 3)
    
    # 4. Score INFLESZ (Peso 25%)
    # Académico Óptimo: 45-65
    s_inflesz = score_range(m.flesch_szigriszt, 45, 65, 35, 85)
    
    # 5. Score Pasiva (Peso 15%)
    # Óptimo: 0-10%. 
    if m.passive_ratio <= 10:
        s_passive = 100.0
    elif m.passive_ratio >= 30:
        s_passive = 0.0
    else:
        s_passive = 100 * (30 - m.passive_ratio) / (30 - 10)

    # CÁLCULO FINAL PONDERADO
    # Definición de pesos (Suman 1.0)
    w_lmo = 0.25
    w_inflesz = 0.25
    w_cv = 0.20
    w_passive = 0.15
    w_z = 0.15

    final_score = (s_lmo * w_lmo) + (s_inflesz * w_inflesz) + (s_cv * w_cv) + (s_passive * w_passive) + (s_z * w_z)

    return {
        "method": "Weighted Average",
        "u_qam_score": round(final_score, 1),
        "breakdown": {
            "LMO": {"val": round(m.lmo, 1), "score": round(s_lmo, 1), "weight": "25%"},
            "INFLESZ": {"val": round(m.flesch_szigriszt, 1), "score": round(s_inflesz, 1), "weight": "25%"},
            "CV": {"val": round(m.cv_sentence_len, 2), "score": round(s_cv, 1), "weight": "20%"},
            "Passive": {"val": round(m.passive_ratio, 1), "score": round(s_passive, 1), "weight": "15%"},
            "Z-Score": {"val": round(m.z_normality, 2), "score": round(s_z, 1), "weight": "15%"}
        }
    }

# --- DEFINICIÓN DEL AGENTE ---
uqam_weighted_agent = LlmAgent(
    name="UQAM_Weighted_Evaluator",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""Eres un analista de textos académicos.
    Utilizas la métrica U-QAM en su versión PONDERADA (Weighted).
    
    TU TAREA:
    1. Analizar el texto usando `calculate_uqam_weighted`.
    2. Interpretar los resultados. A diferencia del método deductivo, aquí cada métrica tiene un puntaje de calidad individual (0-100).
    3. Identificar qué dimensión (LMO, INFLESZ, etc.) bajó el promedio general.
    4. Dar recomendaciones para subir el puntaje en las dimensiones más débiles.
    """,
    tools=[calculate_uqam_weighted]
)

# --- EJECUCIÓN ---
async def run_weighted():
    runner = InMemoryRunner(agent=uqam_weighted_agent, plugins=[UQAMDebugPlugin()])
    textos = cargar_textos()
    
    if not textos:
        print("No se cargaron textos.")
        return

    print("\n--- INICIANDO EVALUACIÓN (MÉTODO PONDERADO) ---")
    for key, data in textos.items():
        titulo = data['titulo']
        contenido = data['contenido']
        
        print(f"\nProcesando: {titulo}...")
        prompt = f"Analiza la calidad de este texto:\n\n{contenido[:5000]}"
        await runner.run_debug(prompt)

if __name__ == "__main__":
    asyncio.run(run_weighted())