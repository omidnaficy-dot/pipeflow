"""PipeFlow core: Darcy-Weisbach head loss (no UI dependencies)."""
import math
from dataclasses import dataclass
from scipy.optimize import brentq

G = 9.81
RHO = 1000.0
NU = 1.0e-6
RE_LAM, RE_TURB = 2300.0, 4000.0


class PipeError(ValueError):
    def __init__(self, code, msg):
        super().__init__(f"{code}: {msg}")
        self.code = code


def reynolds(V, D, nu=NU):
    return V * D / nu


def regime(Re):
    return "laminar" if Re < RE_LAM else ("transitional" if Re <= RE_TURB else "turbulent")


def colebrook(Re, rel_rough, f0=0.02, tol=1e-8, max_iter=100):
    f = f0
    for _ in range(max_iter):
        fn = (-2 * math.log10(rel_rough / 3.7 + 2.51 / (Re * math.sqrt(f)))) ** -2
        if abs(fn - f) < tol:
            return fn
        f = fn
    raise PipeError("E006", "Colebrook did not converge")


def haaland(Re, rel_rough):
    return (-1.8 * math.log10((rel_rough / 3.7) ** 1.11 + 6.9 / Re)) ** -2


def friction_factor(Re, rel_rough):
    if Re < RE_LAM:
        return 64 / Re
    return colebrook(Re, rel_rough)  # transitional: flagged by regime(), uses Colebrook


@dataclass
class Result:
    V: float; Re: float; regime: str; f: float; hf: float; dP: float


def _check(D, L, eps=0.0, nu=NU, rho=RHO):
    if D <= 0: raise PipeError("E001", "D must be > 0")
    if L <= 0: raise PipeError("E002", "L must be > 0")
    if eps < 0 or eps >= D: raise PipeError("E003", "invalid roughness")
    if nu <= 0 or rho <= 0: raise PipeError("E005", "invalid fluid properties")


def head_loss(V, D, L, eps=0.0, nu=NU, rho=RHO, f=None):
    _check(D, L, eps, nu, rho)
    if V <= 0: raise PipeError("E004", "V must be > 0")
    Re = reynolds(V, D, nu)
    ff = f if f is not None else friction_factor(Re, eps / D)
    hf = ff * L / D * V * V / (2 * G)
    return Result(V, Re, regime(Re), ff, hf, rho * G * hf)


def from_flow(Q, D, L, eps=0.0, **kw):
    if Q <= 0: raise PipeError("E004", "Q must be > 0")
    return head_loss(Q / (math.pi * D * D / 4), D, L, eps, **kw)


def length_for_head(hf, V, D, eps=0.0, nu=NU):
    Re = reynolds(V, D, nu)
    f = friction_factor(Re, eps / D)
    return hf * D * 2 * G / (f * V * V)


def velocity_for_head(hf, D, L, eps=0.0, nu=NU):
    _check(D, L, eps, nu)
    g = lambda V: head_loss(V, D, L, eps, nu).hf - hf
    return brentq(g, 1e-6, 100, xtol=1e-12)
