"""
Excepciones propias de PASCo y el enum Mode.
"""
from enum import Enum


class RepeatedCounterexampleError(Exception):
    """
    Se lanza cuando VeriSol/Corral devuelve un contraejemplo concreto ya
    excluido (idéntico a uno anterior en `concrete_cexamples`) *antes* de
    haber agotado las N iteraciones permitidas del loop MUST/MAY.
    """
    pass

class CouldNotExtractCounterexampleError(Exception):
    """
    Se lanza cuando no se puede extraer el contraejemplo
    """
    pass

class Mode(Enum):
    epa = "epa"
    states = "states"

