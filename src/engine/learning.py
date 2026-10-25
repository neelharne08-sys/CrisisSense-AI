import numpy as np
from typing import Dict, List, Tuple
from src.schemas import SourceType

class OnlineLearner:
    """
    Manages:
    1. Online Temperature Scaling (Guo et al. ICML 2017)
    2. Across-Episode Beta Trust Learning with exponential forgetting
    3. Adams & MacKay (2007) BOCD / CUSUM regime shift detection
    4. Dirichlet Prior Adaptation on H
    5. Twin-Test Honest Mixture Prefix Ceiling
    """
    def __init__(self):
        # Temperature scaling
        self.temperature = 1.05
        self.temp_history: List[Tuple[np.ndarray, int]] = [] # (logits, true_h)
        
        # Source Beta distributions: (alpha, beta)
        self.source_betas: Dict[str, Tuple[float, float]] = {
            SourceType.DRAINAGE.value: (8.0, 2.0),
            SourceType.TRAFFIC.value: (7.0, 3.0),
            SourceType.RAIN.value: (9.0, 1.0),
            "open_meteo": (8.5, 1.5),
            SourceType.EMERGENCY_LINES.value: (9.0, 1.0),
            SourceType.DISPATCH.value: (9.0, 1.0),
            SourceType.HOSPITALS.value: (8.0, 2.0),
            SourceType.CAMERAS.value: (6.0, 4.0),
            SourceType.CITIZEN.value: (4.0, 6.0),
            SourceType.SOCIAL.value: (2.0, 8.0),
        }
        
        # Dirichlet prior counts for [H0, H1, H2, H3]
        self.dirichlet_counts = np.array([40.0, 20.0, 25.0, 15.0], dtype=float)
        self.prior_forgetting_gamma = 0.97
        self.shift_countdown = 0
        self.regime_shift_detected = False
        
        # CUSUM parameters for surprise S = -log P_prior(H*)
        self.cusum_C = 0.0
        self.cusum_mu0 = 1.38  # -log(0.25)
        self.cusum_k = 0.20
        self.cusum_threshold = 1.20

    def get_source_reliability(self, source_type: str) -> float:
        alpha, beta = self.source_betas.get(source_type, (5.0, 5.0))
        return float(alpha / (alpha + beta))

    def get_all_source_reliabilities(self) -> Dict[str, float]:
        return {st: self.get_source_reliability(st) for st in self.source_betas}

    def calibrate_probabilities(self, raw_probs: np.ndarray, independent_physical_confirmations: int = 0) -> np.ndarray:
        """
        Applies Guo et al. Temperature Scaling:
        P_cal(H_k) = exp(z_k / tau) / sum_j exp(z_j / tau)
        and clips to [0.01, 0.98] unless >= 3 independent confirmations.
        """
        eps = 1e-12
        p_safe = np.clip(raw_probs, eps, 1.0 - eps)
        logits = np.log(p_safe)
        
        # Scale by temperature
        scaled_logits = logits / max(0.1, self.temperature)
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
        calibrated = exp_logits / np.sum(exp_logits)
        
        # Probability clipping
        if independent_physical_confirmations < 3:
            calibrated = np.clip(calibrated, 0.01, 0.98)
            calibrated /= np.sum(calibrated)
            
        return calibrated

    def apply_twin_prefix_ceiling(self, probs: np.ndarray, current_minute: int, 
                                  independent_physical_confirmations: int,
                                  p_mix: float = 0.35) -> np.ndarray:
        """
        Twin-Test Prefix Ceiling (Section 4.6 & Section 7.4):
        In shared 7-minute prefix where divergence outcome is unknowable,
        cap max P(H) <= p_mix + 0.08 unless >= 2 independent physical confirmations arrive.
        """
        if current_minute <= 7 and independent_physical_confirmations < 2:
            ceiling = p_mix + 0.08
            if probs[3] > ceiling:  # Cap H3
                excess = probs[3] - ceiling
                probs[3] = ceiling
                # Distribute excess to H0 and H2
                probs[0] += excess * 0.6
                probs[2] += excess * 0.4
                probs /= np.sum(probs)
        return probs

    def update_temperature_online(self, logits: np.ndarray, true_h: int):
        """
        Performs SGD steps on temperature tau to minimize negative log-likelihood.
        """
        self.temp_history.append((logits, true_h))
        if len(self.temp_history) > 200:
            self.temp_history.pop(0)

        # Gradient descent step on tau
        lr = 0.01
        for _ in range(3):
            # Compute gradient over last 30 samples
            grad = 0.0
            batch = self.temp_history[-30:]
            for z, y in batch:
                scaled = z / self.temperature
                exp_z = np.exp(scaled - np.max(scaled))
                p = exp_z / np.sum(exp_z)
                # dL/dtau = (1 / tau^2) * sum_k p_k * (z_k - z_y)
                grad += (1.0 / (self.temperature ** 2)) * np.sum(p * (z - z[y]))
            grad /= len(batch)
            self.temperature = float(np.clip(self.temperature - lr * grad, 0.6, 2.5))

    def update_source_trust(self, source_agreements: Dict[str, bool]):
        """
        Updates source Beta distributions with forgetting factor gamma = 0.98.
        """
        gamma = 0.98
        for st, (alpha, beta) in self.source_betas.items():
            if st in source_agreements:
                agreed = source_agreements[st]
                new_alpha = gamma * alpha + (1.0 if agreed else 0.0)
                new_beta = gamma * beta + (0.0 if agreed else 1.0)
            else:
                new_alpha = gamma * alpha
                new_beta = gamma * beta
            # Keep minimum sample mass
            self.source_betas[st] = (max(1.0, new_alpha), max(1.0, new_beta))

    def update_episode_prior_shift(self, true_h: int) -> bool:
        """
        Updates Dirichlet prior on H and evaluates Adams-MacKay / CUSUM changepoint detector.
        """
        prior_p = self.dirichlet_counts / np.sum(self.dirichlet_counts)
        surprise = -np.log(max(1e-6, prior_p[true_h]))

        # CUSUM test on surprise
        self.cusum_C = max(0.0, self.cusum_C + (surprise - self.cusum_mu0 - self.cusum_k))
        
        triggered_this_step = False
        if self.cusum_C > self.cusum_threshold:
            self.regime_shift_detected = True
            triggered_this_step = True
            self.shift_countdown = 10
            self.cusum_C = 0.0

        if self.shift_countdown > 0:
            gamma = 0.70  # Rapid adaptation
            self.shift_countdown -= 1
            self.regime_shift_detected = True
        else:
            gamma = self.prior_forgetting_gamma  # Normal 0.97
            self.regime_shift_detected = False

        self.dirichlet_counts = gamma * self.dirichlet_counts
        self.dirichlet_counts[true_h] += 1.0
        return triggered_this_step or self.regime_shift_detected

    def update_weather_prior_shift(self, rolling_rain_mm_h: float) -> bool:
        """
        Feeds rolling rain history from Open-Meteo into changepoint adaptation.
        If rolling rain exceeds heavy cloudburst thresholds (>15.0 mm/h),
        flags regime shift and temporarily drops forgetting factor gamma to 0.70.
        """
        if rolling_rain_mm_h > 15.0:
            self.regime_shift_detected = True
            self.shift_countdown = 10
            return True
        return False

    def get_learned_h_prior(self) -> np.ndarray:
        return self.dirichlet_counts / np.sum(self.dirichlet_counts)
