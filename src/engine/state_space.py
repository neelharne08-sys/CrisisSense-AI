import numpy as np
from typing import Tuple, Dict

HYPOTHESIS_NAMES = ["H0_Noise", "H1_SensorFailure", "H2_IsolatedIncident", "H3_CascadingCrisis"]
NUISANCE_NAMES = ["R_Rain", "F_Flu", "G1_Gateway1", "G2_Gateway2", "U_Rumor"]

class StateSpace:
    """
    Exact 128-state space factoring:
    H (4) x R (2) x F (2) x G1 (2) x G2 (2) x U (2) = 128 discrete states.
    """
    def __init__(self, lambda_R: float = 0.03, lambda_F: float = 0.02, 
                 lambda_G1: float = 0.01, lambda_G2: float = 0.01, lambda_U: float = 0.03):
        self.num_states = 128
        self.lambda_R = lambda_R
        self.lambda_F = lambda_F
        self.lambda_G1 = lambda_G1
        self.lambda_G2 = lambda_G2
        self.lambda_U = lambda_U
        
        # Precompute index tables
        self.idx_to_tuple = []
        for h in range(4):
            for r in range(2):
                for f in range(2):
                    for g1 in range(2):
                        for g2 in range(2):
                            for u in range(2):
                                self.idx_to_tuple.append((h, r, f, g1, g2, u))
        
        # Marginal indicator masks (size 128)
        self.h_masks = [np.array([s[0] == k for s in self.idx_to_tuple], dtype=bool) for k in range(4)]
        self.r_mask = np.array([s[1] == 1 for s in self.idx_to_tuple], dtype=bool)
        self.f_mask = np.array([s[2] == 1 for s in self.idx_to_tuple], dtype=bool)
        self.g1_mask = np.array([s[3] == 1 for s in self.idx_to_tuple], dtype=bool)
        self.g2_mask = np.array([s[4] == 1 for s in self.idx_to_tuple], dtype=bool)
        self.u_mask = np.array([s[5] == 1 for s in self.idx_to_tuple], dtype=bool)
        
        self.T = self._build_transition_matrix()

    def state_to_idx(self, h: int, r: int, f: int, g1: int, g2: int, u: int) -> int:
        return h * 32 + r * 16 + f * 8 + g1 * 4 + g2 * 2 + u * 1

    def idx_to_state(self, idx: int) -> Tuple[int, int, int, int, int, int]:
        return self.idx_to_tuple[idx]

    def _build_transition_matrix(self) -> np.ndarray:
        """
        Builds the 128x128 joint transition matrix T via Kronecker product of factor matrices.
        Columns sum to 1: T[j, i] = P(s_t = j | s_{t-1} = i).
        """
        # T_H (4x4): sticky diagonal, H2 -> H3 escalation
        T_H = np.array([
            # from H0,    H1,    H2,    H3
            [0.970, 0.015, 0.010, 0.005],  # to H0
            [0.010, 0.970, 0.010, 0.005],  # to H1
            [0.015, 0.010, 0.940, 0.010],  # to H2
            [0.005, 0.005, 0.040, 0.980],  # to H3 (escalates from H2 with p=0.04)
        ], dtype=float)
        # Normalize columns
        T_H /= T_H.sum(axis=0, keepdims=True)

        def make_binary_T(persistence: float, birth_rate: float) -> np.ndarray:
            # col 0: from 0 -> [1 - birth, birth]
            # col 1: from 1 -> [1 - persistence, persistence]
            return np.array([
                [1.0 - birth_rate, 1.0 - persistence],
                [birth_rate, persistence]
            ], dtype=float)

        T_R = make_binary_T(0.95, self.lambda_R)
        T_F = make_binary_T(0.95, self.lambda_F)
        T_G1 = make_binary_T(0.95, self.lambda_G1)
        T_G2 = make_binary_T(0.95, self.lambda_G2)
        T_U = make_binary_T(0.95, self.lambda_U)

        # Joint transition via Kronecker product
        T = np.kron(T_H, np.kron(T_R, np.kron(T_F, np.kron(T_G1, np.kron(T_G2, T_U)))))
        # Ensure column stochastic
        T /= T.sum(axis=0, keepdims=True)
        return T

    def marginalize_H(self, belief: np.ndarray) -> np.ndarray:
        """Returns P(H_k) for k in [0, 1, 2, 3]. Shape: (4,)"""
        return np.array([np.sum(belief[self.h_masks[k]]) for k in range(4)])

    def marginalize_nuisances(self, belief: np.ndarray) -> Dict[str, float]:
        """Returns marginal probabilities for R, F, G1, G2, U."""
        return {
            "R": float(np.sum(belief[self.r_mask])),
            "F": float(np.sum(belief[self.f_mask])),
            "G1": float(np.sum(belief[self.g1_mask])),
            "G2": float(np.sum(belief[self.g2_mask])),
            "U": float(np.sum(belief[self.u_mask]))
        }
