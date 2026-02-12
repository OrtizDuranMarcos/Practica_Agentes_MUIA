import re
import math
from dataclasses import dataclass
from typing import List

# -------------------------
# Utilidades básicas
# -------------------------

VOWELS = "aeiouáéíóúüAEIOUÁÉÍÓÚÜ"


def split_sentences(text: str) -> List[str]:
    """
    Divide un texto en oraciones
    """
    # Normalizar saltos de línea
    text = re.sub(r'\s+', ' ', text.strip())
    # Dividir por signos de puntuación fuertes
    raw_sentences = re.split(r'(?<=[\.\?\!])\s+', text)
    # Limpiar vacíos
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences


def tokenize_words(sentence: str) -> List[str]:
    """
    Extrae palabras (tokens alfabéticos) de una oración.
    """
    return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", sentence)


def count_syllables_es(word: str) -> int:
    """
    Conteo aproximado de sílabas en español:
    - Cuenta grupos de vocales como una sílaba.
    - Asegura mínimo 1 sílaba por palabra.
    Es una heurística, no un silabeador perfecto.
    """
    word = word.lower()
    # Sustituir 'y' vocálica por 'i' para simplificar
    word = re.sub(r"y$", "i", word)

    groups = re.findall(f"[{VOWELS}]+", word)
    syllables = len(groups)
    return max(1, syllables)


def is_passive_sentence(sentence: str) -> bool:
    """
    Heurística para detectar si una oración
    contiene una construcción pasiva perifrástica:
    'ser' + participio (-ado/-ido/-to/-so/-cho).
    """
    s = sentence.lower()
    # Formas frecuentes de 'ser'
    ser_forms = r"(es|son|fue|fueron|ha sido|han sido|será|serán|sea|sean|serían|será|serían)"
    # Participio regular o algunos irregulares comunes
    participle = r"[a-záéíóúüñ]+(ado|ada|ados|adas|ido|ida|idos|idas|to|ta|tos|tas|so|sa|sos|sas)\b"

    pattern = rf"\b{ser_forms}\s+{participle}"
    return re.search(pattern, s) is not None


# -------------------------
# Métricas de legibilidad
# -------------------------

@dataclass
class ReadabilityMetrics:
    num_sentences: int
    num_words: int
    num_syllables: int
    sentence_lengths: List[int]
    lmo: float                     # Longitud media de oración
    std_sentence_len: float        # Desviación típica
    cv_sentence_len: float         # Coef. de variación
    z_normality: float             # z-score respecto a media=20, sigma=5
    flesch_szigriszt: float        # Índice de Flesch-Szigriszt (INFLESZ)
    passive_ratio: float           # % oraciones con pasiva


def compute_metrics(text: str) -> ReadabilityMetrics:
    sentences = split_sentences(text)
    if not sentences:
        raise ValueError("El texto está vacío o no contiene oraciones reconocibles.")

    sentence_lengths = []
    total_words = 0
    total_syllables = 0
    passive_sentences = 0

    for s in sentences:
        words = tokenize_words(s)
        n_words = len(words)
        if n_words == 0:
            continue

        sentence_lengths.append(n_words)
        total_words += n_words

        for w in words:
            total_syllables += count_syllables_es(w)

        if is_passive_sentence(s):
            passive_sentences += 1

    num_sentences = len(sentence_lengths)
    if num_sentences == 0:
        raise ValueError("No se han podido obtener longitudes de oración.")

    # Longitud media, desviación típica y CV
    lmo = total_words / num_sentences
    mean_len = lmo
    var = sum((l - mean_len) ** 2 for l in sentence_lengths) / num_sentences
    std = math.sqrt(var)
    cv = std / mean_len if mean_len != 0 else 0.0

    # z-score de "normalidad" suponiendo media 20, sigma 5 (ajustable)
    mu_ref = 20.0
    sigma_ref = 5.0
    z = (lmo - mu_ref) / sigma_ref

    # Índice Flesch-Szigriszt (IFSZ / INFLESZ)
    # Fórmula original:
    #   IFSZ = 206.835 - 62.3 * (sílabas/palabra) - 1.015 * (palabras/oración)
    syll_per_word = total_syllables / total_words
    words_per_sentence = total_words / num_sentences
    flesch_sz = 206.835 - 62.3 * syll_per_word - 1.015 * words_per_sentence

    # % de oraciones con pasiva
    passive_ratio = 100.0 * passive_sentences / num_sentences

    return ReadabilityMetrics(
        num_sentences=num_sentences,
        num_words=total_words,
        num_syllables=total_syllables,
        sentence_lengths=sentence_lengths,
        lmo=lmo,
        std_sentence_len=std,
        cv_sentence_len=cv,
        z_normality=z,
        flesch_szigriszt=flesch_sz,
        passive_ratio=passive_ratio,
    )


# -------------------------
# Ejemplo de uso
# -------------------------

if __name__ == "__main__":
    
    sample_text = """
    El caso que se nos plantea tiene como base diferentes problemas de gran envergadura
    de manera individual, pero en su conjunto es problema de índole mayor. Según datos
    del PMI, los proyectos de desarrollo de software en formato waterfall presentan
    altos porcentajes de retrasos, sobrecostes y retrabajos, mientras que los enfoques
    ágiles reducen parcialmente estos riesgos. En el proyecto MedSys Online ya se han
    materializado varios de estos factores de riesgo.
    """

    metrics = compute_metrics(sample_text)
    
    print("Nº oraciones:", metrics.num_sentences)
    print("Nº palabras:", metrics.num_words)
    print("LMO (palabras/oración):", round(metrics.lmo, 2))
    print("Desv. típica:", round(metrics.std_sentence_len, 2))
    print("CV longitud oraciones:", round(metrics.cv_sentence_len, 3))
    print("z-normalidad:", round(metrics.z_normality, 2))
    print("Flesch-Szigriszt:", round(metrics.flesch_szigriszt, 2))
    print("% oraciones con pasiva:", round(metrics.passive_ratio, 2))
