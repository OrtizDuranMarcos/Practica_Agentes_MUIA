import os
import sys
import json
import asyncio
from dotenv import load_dotenv

# Importaciones ADK y librerías auxiliares
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.tools import AgentTool

# Asegurarse de tener metrics_w_example.py y debug_plugin.py en la misma carpeta
import metrics_w_example as metrics_lib
from debug_plugin import UQAMDebugPlugin

# Cargar variables de entorno
load_dotenv()

# Configuración de reintento
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],
)

def cargar_textos(ruta_json="PARTE_2_U-QAM_Agent/textos.json"):
    """Carga los textos desde el archivo JSON."""
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {ruta_json}")
        return {}

# --- LÓGICA U-QAM (MÉTODO DEDUCTIVO) ---
def calculate_uqam_deductive(text: str) -> dict:
    """
    Calcula el U-QAM Score usando el MÉTODO DEDUCTIVO.
    Puntuación Base: 100. Se aplican penalizaciones por desviaciones.
    """
    try:
        m = metrics_lib.compute_metrics(text)
    except Exception as e:
        return {"error": f"Error al calcular métricas: {str(e)}", "score": 0}

    score = 100.0
    penalties = []

    # 1. Longitud Media de Oración (LMO)
    # Óptimo: 16-23. 
    # Rangos: 12-16 (Claro), 23-30 (Denso), >30 (Pesado), <12 
    if 16 <= m.lmo <= 23:
        pass # Óptimo
    elif 12 <= m.lmo < 16:
        score -= 5
        penalties.append(f"LMO Ligeramente bajo ({m.lmo:.1f}): -5")
    elif 23 < m.lmo <= 30:
        score -= 5
        penalties.append(f"LMO Denso ({m.lmo:.1f}): -5")
    else: # < 12 o > 30
        score -= 15
        penalties.append(f"LMO Extremo ({m.lmo:.1f}): -15")

    # 2. Variabilidad (CV)
    # Óptimo: 0.50 - 1.00
    if 0.50 <= m.cv_sentence_len <= 1.00:
        pass # Natural
    elif m.cv_sentence_len < 0.50:
        if m.cv_sentence_len < 0.30: # < 0.30 es mecánico, < 0.50 es bajo
            p = 15
        else:
            p = 5
        score -= p
        penalties.append(f"CV Bajo/Mecánico ({m.cv_sentence_len:.2f}): -{p}")
    else: # > 1.00
        if m.cv_sentence_len > 1.20:
            p = 15
        else:
            p = 5
        score -= p
        penalties.append(f"CV Alto/Caótico ({m.cv_sentence_len:.2f}): -{p}")

    # 3. Normalidad (Z-Score)
    # Rango típico: -1 a +1
    if abs(m.z_normality) > 1.0:
        # Penalización progresiva: 5 puntos por cada unidad de desvío
        p = min(20, 5 * (abs(m.z_normality) - 1.0))
        score -= p
        penalties.append(f"Z-Score fuera de rango ({m.z_normality:.2f}): -{p:.1f}")

    # 4. INFLESZ (Legibilidad)
    # Académico/Especializado: 40-64 (Aceptable). < 40 Muy difícil. > 80 Muy fácil (infantil).
    if m.flesch_szigriszt < 55:
        if m.flesch_szigriszt < 40:
            p = 20
        else:
            p = 10
        score -= p
        penalties.append(f"INFLESZ Muy difícil ({m.flesch_szigriszt:.1f}): -{p}")
    elif m.flesch_szigriszt > 80:
        if m.flesch_szigriszt > 100:
            p = 20
        else:
            p = 10
        score -= p
        penalties.append(f"INFLESZ Demasiado simple ({m.flesch_szigriszt:.1f}): -{p}")
    
    # 5. Voz Pasiva
    # < 10% Claro. 10-20% Aceptable. > 20% Burocrático
    if m.passive_ratio > 20.0:
        score -= 15
        penalties.append(f"Exceso Pasiva ({m.passive_ratio:.1f}%): -15")
    elif 10.0 < m.passive_ratio <= 20.0:
        score -= 5
        penalties.append(f"Pasiva Elevada ({m.passive_ratio:.1f}%): -5")

    final_score = max(0, round(score, 1))

    return {
        "method": "Deductive (Penalty-based)",
        "u_qam_score": final_score,
        "metrics": {
            "lmo": round(m.lmo, 2),
            "cv": round(m.cv_sentence_len, 2),
            "z_score": round(m.z_normality, 2),
            "inflesz": round(m.flesch_szigriszt, 2),
            "passive_pct": round(m.passive_ratio, 2)
        },
        "details": penalties
    }

# --- DEFINICIÓN DEL AGENTE ---
uqam_deductive_agent = LlmAgent(
    name="UQAM_Deductive_Evaluator",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""Eres un evaluador de calidad académica utilizando el sistema U-QAM.
    
    TU OBJETIVO:
    Evaluar textos basándote ESTRICTAMENTE en los datos devueltos por la herramienta `calculate_uqam_deductive`.
    
    PASOS:
    1. Recibe el texto.
    2. Usa la herramienta para obtener el score y las penalizaciones.
    3. Genera un reporte que explique:
       - El Score Final.
       - Qué penalizaciones se aplicaron y por qué (basado en el output de la herramienta).
       - Una conclusión sobre la calidad del texto (Excelente >90, Bueno >75, Mejorable >60, Pobre <60).
    """,
    tools=[calculate_uqam_deductive]
)

# --- EJECUCIÓN ---
async def run_deductive():
    runner = InMemoryRunner(agent=uqam_deductive_agent, plugins=[UQAMDebugPlugin()])
    textos = cargar_textos()
    
    if not textos:
        print("No se cargaron textos. Verifica 'textos.json'.")
        return

    print("\n--- INICIANDO EVALUACIÓN (MÉTODO DEDUCTIVO) ---")
    for key, data in textos.items():
        titulo = data['titulo']
        contenido = data['contenido']
        
        # Validación simple de longitud para el usuario
        words = len(contenido.split())
        print(f"\nProcesando: {titulo} ({words} palabras)...")
        if words < 100:
             print("ADVERTENCIA: El texto parece muy corto. Recuerda usar textos de 800-1000 palabras.")

        prompt = f"Evalúa el siguiente texto con U-QAM:\n\n{contenido}" # Limitamos caracteres por seguridad
        await runner.run_debug(prompt)

if __name__ == "__main__":
    asyncio.run(run_deductive())