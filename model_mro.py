import numpy as np
from scipy.integrate import solve_ivp

# ===========================
#   Modèle MRO
# ===========================

def MRO_equations(t: float, Y: list, m: float, gamma: float, k: float) -> list:
    x, dxdt = Y
    dxdtt = -(gamma / m) * dxdt - (k / m) * x
    return [dxdt, dxdtt]


def simulate_mro(
    m: float = 1.0,
    gamma: float = 0.15,
    k: float = 1.0,
    x0: float = 1.0,
    v0: float = 0.0,
    t_start: float = 0.0,
    t_end: float = 30.0,
    t_points: int = 3000,
) -> tuple:
    t_eval = np.linspace(t_start, t_end, t_points)
    sol = solve_ivp(
        MRO_equations,
        [t_start, t_end],
        [x0, v0],
        args=(m, gamma, k),
        t_eval=t_eval,
        method="RK45",
    )
    t = sol.t
    x = sol.y[0]
    v = sol.y[1]
    return t, x, v

def compute_mro_series(
    m: float,
    gamma: float,
    k: float,
    x0: float,
    v0: float,
    t_end: float,
    t_start: float = 0.0,
    t_points: int = 3000,
) -> tuple:
    t, x, v = simulate_mro(
        m=m,
        gamma=gamma,
        k=k,
        x0=x0,
        v0=v0,
        t_start=t_start,
        t_end=t_end,
        t_points=t_points,
    )
    a = -(gamma / m) * v - (k / m) * x
    ek = 0.5 * m * (v ** 2)
    ep = 0.5 * k * (x ** 2)
    et = ek + ep
    return t, x, v, a, ek, ep, et


def heatmap_max_amp(
    gammas,
    ks,
    m=1.0,
    x0=1.0,
    v0=0.0,
    t_end=30.0,
    t_points=2000,
):
    data = np.zeros((len(gammas), len(ks)))
    for i, g in enumerate(gammas):
        for j, kk in enumerate(ks):
            t, x, _ = simulate_mro(
                m=m,
                gamma=g,
                k=kk,
                x0=x0,
                v0=v0,
                t_start=0,
                t_end=t_end,
                t_points=t_points,
            )
            data[i, j] = np.max(np.abs(x))
    return data
