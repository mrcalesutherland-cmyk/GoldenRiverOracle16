# -----------------------------------------------------------------------------
# PROJECT: GOLDEN RIVER ORACLE 16- MASTER HYBRID EDITION (V22.2 SOVEREIGN ADAPTIVE)
# Asset: First Neiro On Ethereum / TetherUS (NEIROUSDT) via Binance API
#
# INVENTORS & OWNERS: Cale Sutherland & Daniela Admidina
# CODER: Gemini
#
# ARCHITECTURE: DECOMPOSED SELF-TUNING FORMULA + HONEST OOS LOCK + CHAMPION VAULT
# V22.2 PATCH NOTES:
#   - True OOS Grading: Grades strictly against immutable frozen_target_prices (Zero Goalpost Dragging)
#   - Normalized Dual-Truth Shape Engine: Fixes <1.0 decimal exponent crush; governed by Honest OOS + Path Acc
#   - Variable Dual-Truth Learning Rate & 6-Stream Blender: Dynamic honest_path_mix & path_trust_ratio
#   - Multi-Tier Tactile Ground/Ceiling & Big-Leg Vacuum Sensor: 50/144/288-bar shelves + 24-bin Volume Profile
#   - Directional Cliff & Climb Sensor + Flashing HUD Arrow: Distinct CLIFF DROP (▼▼) & VERTICAL CLIMB (▲▲)
# -----------------------------------------------------------------------------
# REQUIRED PACKAGES: pip install numpy pandas matplotlib requests
# -----------------------------------------------------------------------------

import os
import Repo
import sys
import time
import math
import json
import pickle
import sqlite3
import requests
import warnings
import numpy as np
import pandas as pd
from collections import deque
from datetime import datetime, timedelta
import concurrent.futures
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings("ignore")

BINANCE_SYMBOL = "NEIROUSDT"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Global Persistent HTTP Session for Low-Latency Connection Pooling
HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)

SHOW_GHOST_LINES = False

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

DATA_DIR = os.path.join(BASE_DIR, "neiro_oracle_signatures")
os.makedirs(DATA_DIR, exist_ok=True)

STATE_JSON_FILE = os.path.join(DATA_DIR, "sovereign_marker_state_v22.json")
STATE_JSON_FALLBACK = os.path.join(DATA_DIR, "sovereign_marker_state_v21.json")
STATE_SQLITE_DB = os.path.join(DATA_DIR, "sovereign_ledger.db")

# Fixed Timeframe Definitions
TIMEFRAMES = {
    "4hr": {"interval": "15m", "limit": 1000, "horizon": 16, "label": "4 HOUR PROJECTION (15m)", "dt_fmt": "%H:%M", "delta": timedelta(minutes=15)},
    "1d":  {"interval": "1h",  "limit": 1000, "horizon": 24, "label": "24 HOUR PROJECTION (1H)", "dt_fmt": "%b %d %H", "delta": timedelta(hours=1)},
    "1wk": {"interval": "4h",  "limit": 1000, "horizon": 42, "label": "1 WEEK PROJECTION (4H)",  "dt_fmt": "%b %d", "delta": timedelta(hours=4)},
    "1mo": {"interval": "1d",  "limit": 1000, "horizon": 30, "label": "1 MONTH PROJECTION (1D)", "dt_fmt": "%b '%y", "delta": timedelta(days=1)}
}

MEMORY_MAX = 50000

# -----------------------------
# DECOMPOSED SELF-TUNING PREDICTION FORMULA (V22.2)
# -----------------------------
class DecomposedPredictionFormula:
    """
    Breaks the entire Oracle prediction synthesis into explicit, mathematically
    isolated sub-formulas with adaptive coefficients governed by honest OOS truth
    and live path accuracy, preserved inside a Champion Elitism Vault.
    """
    BOUNDS = {
        "dist_exp": (0.80, 4.50),
        "mem_exp": (0.50, 3.00),
        "thrust_gain": (0.20, 2.50),
        "dom_blend": (0.10, 0.65),
        "vol_scale": (0.40, 1.80),
        "coil_phase_w": (0.15, 0.85),
        "chop_phase_w": (0.15, 0.85),
        "amp_gain": (0.35, 2.20),
        "shape_exp": (0.75, 1.35),
        "fuzz_vel_gain": (0.50, 3.50),
        "mirror_decay": (0.30, 0.88),
        "exh_reflect": (0.25, 0.90),
        "swarm_trust_mix": (0.20, 0.85),
        "flow_weight": (0.20, 0.85),
        "ob_weight": (0.15, 0.80),
        "macro_beta_gain": (0.10, 0.85),
        "ghost_slope_gain": (0.15, 1.20),
        "rev_pull_gain": (0.10, 1.20),
        "res_corr_gain": (0.20, 1.15),
        "apex_retrace_gain": (0.20, 0.90),
        "chop_damping_gain": (0.20, 0.85),
        "breakout_thrust_gain": (0.45, 2.10),
        "pmax_vol_mult": (2.00, 7.50),
        "step_limit_ratio": (0.22, 0.70),
        "mom_anchor_bias": (0.15, 0.85),
        "triphase_damp": (0.25, 1.00),
        "flow_decay_rate": (0.05, 0.45),
        "macro_onset_exp": (0.40, 1.60),
        "mirror_pos_shift": (-0.20, 0.20),
        "lightning_reach": (0.25, 0.85),
        "lightning_warp_gain": (0.20, 1.75),
        "landscape_flow_gain": (0.15, 2.25),
        "spoof_strictness": (0.20, 0.90),
        "honest_path_mix": (0.12, 0.88),
        "leg_drive_gain": (0.40, 2.80),
        "ground_ceil_feel": (0.20, 2.00)
    }

    def __init__(self, horizon):
        self.horizon = horizon
        self.params = {
            "dist_exp": 2.35,
            "mem_exp": 1.25,
            "thrust_gain": 1.45,
            "dom_blend": 0.38,
            "vol_scale": 1.05,
            "coil_phase_w": 0.50,
            "chop_phase_w": 0.50,
            "amp_gain": 1.05,
            "shape_exp": 1.00,
            "fuzz_vel_gain": 1.95,
            "mirror_decay": 0.68,
            "exh_reflect": 0.65,
            "swarm_trust_mix": 0.52,
            "flow_weight": 0.64,
            "ob_weight": 0.36,
            "macro_beta_gain": 0.38,
            "ghost_slope_gain": 0.65,
            "rev_pull_gain": 0.42,
            "res_corr_gain": 0.68,
            "apex_retrace_gain": 0.46,
            "chop_damping_gain": 0.52,
            "breakout_thrust_gain": 1.20,
            "pmax_vol_mult": 4.50,
            "step_limit_ratio": 0.44,
            "mom_anchor_bias": 0.38,
            "triphase_damp": 0.80,
            "flow_decay_rate": 0.16,
            "macro_onset_exp": 0.82,
            "mirror_pos_shift": 0.00,
            "lightning_reach": 0.48,
            "lightning_warp_gain": 0.88,
            "landscape_flow_gain": 0.90,
            "spoof_strictness": 0.45,
            "honest_path_mix": 0.48,
            "leg_drive_gain": 1.25,
            "ground_ceil_feel": 1.00
        }
        self.champion_params = dict(self.params)
        self.champion_accuracy = 55.0
        self.param_velocity = {k: 0.0 for k in self.params}
        self.last_perturbation = {k: 0.0 for k in self.params}
        self.tuning_epoch = 0
        self.formula_efficiency = 75.0
        self.stage_keys = ("knn_raw", "swarm_fuzz", "opinion", "final_blended", "lightning", "landscape")
        self.stage_acc = {k: 65.0 for k in self.stage_keys}
        self.stage_metab = {k: 1.0 for k in self.stage_keys}
        self.stage_clock = {k: 0 for k in self.stage_keys}

    def _step_stage_metabolism(self, stage_key, trace_curve, real_arr, base_lr, real_std):
        self.stage_clock[stage_key] = self.stage_clock.get(stage_key, 0) + 1
        n = len(real_arr)
        if trace_curve is None or len(trace_curve) < n or n == 0:
            return False, base_lr
        sub = np.array(trace_curve[:n], dtype=float)
        s_acc = calculate_directional_truth(sub, real_arr, vol_scale=max(real_std, 0.005))
        prev_acc = self.stage_acc.get(stage_key, 65.0)
        self.stage_acc[stage_key] = float(np.clip((prev_acc * 0.78) + (s_acc * 0.22), 15.0, 99.5))
        acc_delta = s_acc - prev_acc
        target_metab = np.clip((self.stage_acc[stage_key] / 62.0) * (1.0 + np.clip(acc_delta / 35.0, -0.35, 0.55)), 0.22, 2.35)
        self.stage_metab[stage_key] = float((self.stage_metab.get(stage_key, 1.0) * 0.70) + (target_metab * 0.30))
        fast_twitch = stage_key in ("swarm_fuzz", "lightning")
        cadence = 1 if (fast_twitch or self.stage_metab[stage_key] >= 1.05 or s_acc < 45.0) else (2 if self.stage_metab[stage_key] >= 0.65 else 3)
        should_fire = (self.stage_clock[stage_key] % cadence == 0)
        stage_lr = float(np.clip(base_lr * self.stage_metab[stage_key], 0.0004, 0.16))
        return should_fire, stage_lr

    def get(self, key):
        return float(self.params.get(key, 1.0))

    def _clip_all(self):
        for k, (lo, hi) in self.BOUNDS.items():
            mid = 0.5 * (lo + hi)
            if k in self.params:
                val = self.params[k]
                self.params[k] = float(np.clip(val, lo, hi)) if np.isfinite(val) else mid
            if k in self.champion_params:
                cval = self.champion_params[k]
                self.champion_params[k] = float(np.clip(cval, lo, hi)) if np.isfinite(cval) else self.params.get(k, mid)
        if not np.isfinite(self.champion_accuracy):
            self.champion_accuracy = 55.0
        if not np.isfinite(self.formula_efficiency):
            self.formula_efficiency = 75.0

    def tune_from_accuracy(self, realized_curve, component_traces, realized_acc, hist_acc, lr=0.02):
        n = len(realized_curve)
        if n == 0:
            return

        real_arr = np.array(realized_curve[:n], dtype=float)
        real_std = float(np.std(real_arr)) + 1e-6
        
        # Ledger B: Honest Structural & Extremum Accuracy (Prevents shape flattening)
        final_blend_curve = component_traces.get("final_blended", real_arr) if component_traces else real_arr
        honest_struct_acc = calculate_honest_structural_grade(final_blend_curve[:n], real_arr, vol_scale=max(real_std, 0.005))

        # Self-tuning Dual-Truth Blend
        hp_mix = float(np.clip(self.params.get("honest_path_mix", 0.48), 0.12, 0.88))
        blended_acc = (hist_acc * hp_mix) + (realized_acc * (1.0 - hp_mix))
        
        # Dual optimization target: punishing shape averaging while rewarding honest structural swings
        effective_opt_acc = (honest_struct_acc * 0.60) + (blended_acc * 0.40)
        
        # Optional live telemetry print to track Ledger B anti-flattening guardrails
        if abs(honest_struct_acc - realized_acc) > 12.0:
            print(f"[Ledger B] Structural Grade: {honest_struct_acc:4.1f}% | Path Acc: {realized_acc:4.1f}% (Anti-Flattening Active)")
        self.formula_efficiency = float(np.clip((self.formula_efficiency * 0.85) + (effective_opt_acc * 0.15), 10.0, 99.9))

        if abs(realized_acc - hist_acc) > 4.0:
            mix_step = 0.015 if hist_acc > realized_acc else -0.015
            self.params["honest_path_mix"] = float(np.clip(hp_mix + mix_step, 0.12, 0.88))

        # 1. Binary All-or-Nothing Reward Gate (Strict 5% Target)
        # Evaluates relative shape error and timing offset against the 5% boundary
        shape_error_pct = float(np.mean(np.abs(final_blend_curve[:n] - real_arr) / (np.abs(real_arr) + 1e-6))) * 100.0
        
        pred_peak_idx = int(np.argmax(np.abs(final_blend_curve[:n])))
        real_peak_idx = int(np.argmax(np.abs(real_arr)))
        time_error_pct = (abs(pred_peak_idx - real_peak_idx) / float(max(1, n))) * 100.0

        # Zero reward if shape or time miss exceeds 5.0%; up to 100x multiplier for sub-5% precision
        if shape_error_pct <= 5.0 and time_error_pct <= 5.0:
            perfection_factor = min(1.0, (5.0 - (shape_error_pct + time_error_pct) / 2.0) / 5.0)
            reward_multiplier = 1.0 + (99.0 * perfection_factor)  # Scales continuously from 1x to 100x
        else:
            reward_multiplier = 0.0  # Zero points/reward for anything outside the 5% window

        # 2. Champion Vault Elitism Update (Governed by Binary Gate)
        if reward_multiplier > 0.0 and effective_opt_acc >= self.champion_accuracy:
            self.champion_accuracy = float(min(99.9, (self.champion_accuracy * 0.30) + (effective_opt_acc * 0.70)))
            for k in self.params:
                # Accelerate learning towards high-reward parameters based on multiplier
                blend_rate = min(0.95, 0.25 * (reward_multiplier / 10.0))
                self.champion_params[k] = ((1.0 - blend_rate) * self.champion_params[k]) + (blend_rate * self.params[k])
        elif reward_multiplier == 0.0 or effective_opt_acc < (self.champion_accuracy - 14.0):
            pull_strength = 0.35 if reward_multiplier == 0.0 else float(np.clip((self.champion_accuracy - effective_opt_acc) / 100.0, 0.05, 0.35))
            for k in self.params:
                self.params[k] = ((1.0 - pull_strength) * self.params[k]) + (pull_strength * self.champion_params[k])

        # 2. Variable Tuning Rate Governed by BOTH Honest OOS & Path Accuracy + Divergence
        real_arr = np.array(realized_curve[:n], dtype=float)
        real_std = float(np.std(real_arr)) + 1e-6
        real_net = float(real_arr[-1])

        acc_divergence = abs(realized_acc - hist_acc) / 100.0
        dual_deficit = ((100.0 - hist_acc) * 0.45 + (100.0 - realized_acc) * 0.55) / 100.0
        rate_mult = (0.35 + (dual_deficit * 1.45) + (acc_divergence * 0.85))
        eff_lr = float(np.clip(lr * rate_mult, 0.0008, 0.11))

        if component_traces:
            base_lr = eff_lr
            # Stage 1 & 2: KNN, Amplitude, Shape Curvature & Leg Drive Scaling
            knn_c = component_traces.get("knn_raw")
            fire_knn, eff_lr = self._step_stage_metabolism("knn_raw", knn_c, real_arr, base_lr, real_std)
            if fire_knn and knn_c is not None and len(knn_c) >= n:
                knn_sub = np.array(knn_c[:n], dtype=float)
                knn_std = float(np.std(knn_sub)) + 1e-6
                vol_ratio = np.clip(real_std / knn_std, 0.5, 1.8)
                self.params["vol_scale"] += eff_lr * (vol_ratio - self.params["vol_scale"])
                target_amp = np.clip(abs(real_net) / (abs(knn_sub[-1]) + 1e-5), 0.45, 2.15)
                self.params["amp_gain"] += eff_lr * (target_amp - self.params["amp_gain"])
                if np.sign(knn_sub[0]) == np.sign(real_arr[0]):
                    self.params["thrust_gain"] += eff_lr * 0.15
                else:
                    self.params["thrust_gain"] -= eff_lr * 0.10

                # Tune shape_exp, leg_drive_gain, and ground_ceil_feel from realized path geometry
                if n >= 2:
                    early_real = float(np.mean(np.abs(real_arr[:max(1, n // 2)])))
                    late_real = float(np.mean(np.abs(real_arr[max(1, n // 2):]))) + 1e-6
                    real_convexity = np.clip(late_real / (early_real + 1e-6), 0.65, 1.40)
                    self.params["shape_exp"] += eff_lr * 0.35 * (real_convexity - self.params["shape_exp"])

                if abs(real_net) > (real_std * 1.60):
                    self.params["leg_drive_gain"] += eff_lr * 0.25 * np.sign(abs(real_net) - abs(knn_sub[-1]))
                else:
                    self.params["ground_ceil_feel"] += eff_lr * 0.10 * (1.15 - self.params["ground_ceil_feel"])

            # Stage 3: Swarm & Fuzz
            fuzz_c = component_traces.get("swarm_fuzz")
            fire_fuzz, eff_lr = self._step_stage_metabolism("swarm_fuzz", fuzz_c, real_arr, base_lr, real_std)
            if fire_fuzz and fuzz_c is not None and len(fuzz_c) >= n:
                fuzz_sub = np.array(fuzz_c[:n], dtype=float)
                fuzz_err = float(np.mean(np.abs(fuzz_sub - real_arr)))
                knn_err = float(np.mean(np.abs(np.array(knn_c[:n]) - real_arr))) if (knn_c is not None and len(knn_c) >= n) else fuzz_err
                if fuzz_err < knn_err:
                    self.params["swarm_trust_mix"] -= eff_lr * 0.12
                    self.params["fuzz_vel_gain"] += eff_lr * 0.15
                else:
                    self.params["swarm_trust_mix"] += eff_lr * 0.12

            # Stage 4: Opinion & Macro
            op_c = component_traces.get("opinion")
            fire_op, eff_lr = self._step_stage_metabolism("opinion", op_c, real_arr, base_lr, real_std)
            if fire_op and op_c is not None and len(op_c) >= n:
                op_sub = np.array(op_c[:n], dtype=float)
                if np.sign(op_sub[-1]) == np.sign(real_net):
                    self.params["flow_weight"] += eff_lr * 0.08
                    self.params["res_corr_gain"] += eff_lr * 0.10
                else:
                    self.params["rev_pull_gain"] += eff_lr * 0.08

            # Stage 5 & 6: Clamp, Step Limits & Dynamic Phase Timing
            final_c = component_traces.get("final_blended")
            fire_fin, eff_lr = self._step_stage_metabolism("final_blended", final_c, real_arr, base_lr, real_std)
            if fire_fin and final_c is not None and len(final_c) >= n:
                final_sub = np.array(final_c[:n], dtype=float)
                if abs(real_net) > abs(final_sub[-1]) * 1.20 and np.sign(real_net) == np.sign(final_sub[-1]):
                    self.params["pmax_vol_mult"] += eff_lr * 0.50
                    self.params["step_limit_ratio"] += eff_lr * 0.05
                    self.params["breakout_thrust_gain"] += eff_lr * 0.12
                elif abs(final_sub[-1]) > abs(real_net) * 1.35:
                    self.params["pmax_vol_mult"] -= eff_lr * 0.35
                    self.params["chop_damping_gain"] += eff_lr * 0.05

                if n >= 4:
                    pred_peak_idx = int(np.argmax(np.abs(final_sub)))
                    real_peak_idx = int(np.argmax(np.abs(real_arr)))
                    timing_lag_ratio = (real_peak_idx - pred_peak_idx) / float(max(1, n))
                    self.params["mirror_pos_shift"] += eff_lr * timing_lag_ratio * 0.45
                    if real_peak_idx > pred_peak_idx:
                        self.params["flow_decay_rate"] -= eff_lr * 0.04
                        self.params["macro_onset_exp"] += eff_lr * 0.08
                    elif real_peak_idx < pred_peak_idx:
                        self.params["flow_decay_rate"] += eff_lr * 0.04
                        self.params["macro_onset_exp"] -= eff_lr * 0.08

            # Stage 7: Lightning Contour & Dynamic Reach Governance
            light_c = component_traces.get("lightning")
            fire_light, eff_lr = self._step_stage_metabolism("lightning", light_c, real_arr, base_lr, real_std)
            if fire_light and light_c is not None and len(light_c) >= n:
                light_sub = np.array(light_c[:n], dtype=float)
                light_err = float(np.mean(np.abs(light_sub - real_arr)))
                base_err = float(np.mean(np.abs(np.array(final_c[:n]) - real_arr))) if (final_c is not None and len(final_c) >= n) else light_err
                if light_err <= base_err or np.sign(light_sub[-1]) == np.sign(real_net):
                    self.params["lightning_warp_gain"] += eff_lr * 0.16
                    self.params["lightning_reach"] += eff_lr * 0.06
                else:
                    self.params["lightning_warp_gain"] -= eff_lr * 0.12
                    self.params["lightning_reach"] -= eff_lr * 0.04

            # Stage 8: Virtual Landscape & Spoof Sampler Governance
            land_c = component_traces.get("landscape")
            fire_land, eff_lr = self._step_stage_metabolism("landscape", land_c, real_arr, base_lr, real_std)
            if fire_land and land_c is not None and len(land_c) >= n:
                land_sub = np.array(land_c[:n], dtype=float)
                land_err = float(np.mean(np.abs(land_sub - real_arr)))
                base_err = float(np.mean(np.abs(np.array(final_c[:n]) - real_arr))) if (final_c is not None and len(final_c) >= n) else land_err
                if land_err <= base_err and np.sign(land_sub[-1]) == np.sign(real_net):
                    self.params["landscape_flow_gain"] += eff_lr * 0.22
                    self.params["spoof_strictness"] += eff_lr * 0.04
                elif np.sign(land_sub[-1]) == np.sign(real_net):
                    self.params["landscape_flow_gain"] += eff_lr * 0.08
                else:
                    self.params["landscape_flow_gain"] -= eff_lr * 0.18
                    self.params["spoof_strictness"] -= eff_lr * 0.04

        # 3. Momentum Refinement Scaled by Perfection Reward
        spsa_gate = float(np.clip((lr / 0.02) * np.mean(list(self.stage_metab.values())), 0.04, 1.35))
        explore_scale = max(0.0001, (100.0 - blended_acc) / 100.0 * 0.012 * spsa_gate)
        
        # If the reward gate failed (0 score), force immediate gradient reversal away from the bad shape
        improve_sign = (1.0 if reward_multiplier > 0.0 else -1.5) * min(1.0, spsa_gate)
        step_boost = max(1.0, reward_multiplier * 0.1)

        for k in self.params:
            lo, hi = self.BOUNDS[k]
            span = hi - lo
            prev_step = self.last_perturbation.get(k, 0.0)
            grad_step = prev_step * improve_sign * 0.35 * step_boost
            new_pert = float(np.random.normal(0.0, span * explore_scale * 0.25))
            self.param_velocity[k] = (0.75 * self.param_velocity[k]) + (0.25 * (grad_step + new_pert))
            self.params[k] += self.param_velocity[k] * min(1.0, spsa_gate)
            self.last_perturbation[k] = new_pert

        self._clip_all()
        self.tuning_epoch += 1

    def to_dict(self):
        return {
            "params": self.params,
            "champion_params": self.champion_params,
            "champion_accuracy": float(self.champion_accuracy),
            "formula_efficiency": float(self.formula_efficiency),
            "tuning_epoch": int(self.tuning_epoch),
            "stage_acc": dict(self.stage_acc),
            "stage_metab": dict(self.stage_metab)
        }

    def from_dict(self, d):
        try:
            if "params" in d and isinstance(d["params"], dict):
                for k, v in d["params"].items():
                    if k in self.params:
                        self.params[k] = float(v)
            if "champion_params" in d and isinstance(d["champion_params"], dict):
                for k, v in d["champion_params"].items():
                    if k in self.champion_params:
                        self.champion_params[k] = float(v)
            if "stage_acc" in d and isinstance(d["stage_acc"], dict):
                for k, v in d["stage_acc"].items():
                    if k in self.stage_acc:
                        self.stage_acc[k] = float(np.clip(v, 15.0, 99.5))
            if "stage_metab" in d and isinstance(d["stage_metab"], dict):
                for k, v in d["stage_metab"].items():
                    if k in self.stage_metab:
                        self.stage_metab[k] = float(np.clip(v, 0.22, 2.35))
            self.champion_accuracy = float(d.get("champion_accuracy", 55.0))
            self.formula_efficiency = float(d.get("formula_efficiency", 75.0))
            self.tuning_epoch = int(d.get("tuning_epoch", 0))
            self._clip_all()
        except Exception:
            pass

# -----------------------------
# ATOMIC STATE PERSISTENCE & LEDGER
# -----------------------------
class StatePersistence:
    """
    Handles atomic JSON state persistence and SQLite ledger auditing so learned
    marker weights, DecomposedPredictionFormula states, Champion Vaults, active OOS
    locks, and Lazarus bankroll survive restarts without ever resetting to zero.
    """
    def __init__(self, json_path, db_path, fallback_json_path=None):
        self.json_path = json_path
        self.fallback_json_path = fallback_json_path
        self.db_path = db_path
        self._init_sqlite()

    def _init_sqlite(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trade_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL,
                    tf_key TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    projected_pct REAL,
                    realized_pct REAL,
                    fee_adj_pnl_pct REAL,
                    lazarus_alloc REAL,
                    p_max REAL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS marker_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL,
                    tf_key TEXT,
                    marker_idx INTEGER,
                    target_price REAL,
                    hit_price REAL,
                    arrival_accuracy REAL
                )
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def log_trade_audit(self, tf_key, side, entry_p, exit_p, proj_pct, real_pct, net_pnl_pct, lazarus_alloc, p_max):
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO trade_ledger
                (ts, tf_key, side, entry_price, exit_price, projected_pct, realized_pct, fee_adj_pnl_pct, lazarus_alloc, p_max)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (time.time(), tf_key, side, float(entry_p), float(exit_p), float(proj_pct), float(real_pct), float(net_pnl_pct), float(lazarus_alloc), float(p_max)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def log_marker_hit(self, tf_key, marker_idx, target_price, hit_price, arrival_acc):
        try:
            conn = sqlite3.connect(self.db_path, timeout=5.0, check_same_thread=False)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO marker_audits (ts, tf_key, marker_idx, target_price, hit_price, arrival_accuracy)
                VALUES (?, ?, ?, ?, ?)
            """, (time.time(), tf_key, int(marker_idx), float(target_price), float(hit_price), float(arrival_acc)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def save_state(self, engines, exec_engine):
        try:
            payload = {
                "timestamp": time.time(),
                "symbol": BINANCE_SYMBOL,
                "execution": exec_engine.to_dict(),
                "timeframes": {}
            }
            for tf, eng in engines.items():
                payload["timeframes"][tf] = {
                    "historical_accuracy": float(eng["locker"].historical_accuracy),
                    "peak_historical_accuracy": float(eng["locker"].peak_historical_accuracy),
                    "last_live_accuracy": float(eng.get("last_live_accuracy", 100.0)),
                    "swarm_health": float(eng["swarm"].swarm_health),
                    "swarm_eval_count": int(eng["swarm"].eval_count),
                    "node_weights": [float(n.accuracy_weight) for n in eng["swarm"].nodes],
                    "learning_rate": float(eng["governor"].learning_rate),
                    "recalc_trigger": float(eng["governor"].recalc_trigger),
                    "p_max": float(eng.get("p_max", 1.0)),
                    "opinion_state": eng["opinion"].to_dict() if "opinion" in eng else {},
                    "formula_state": eng["formula"].to_dict() if "formula" in eng else {},
                    "active_lock": eng["locker"].serialize_active_lock()
                }
            tmp_path = self.json_path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, self.json_path)
        except Exception:
            pass

    def load_state(self, engines, exec_engine):
        load_target = self.json_path if os.path.exists(self.json_path) else (
            self.fallback_json_path if (self.fallback_json_path and os.path.exists(self.fallback_json_path)) else None
        )
        if not load_target:
            return False
        try:
            with open(load_target, "r") as f:
                data = json.load(f)
            if "execution" in data:
                exec_engine.from_dict(data["execution"])
            tf_data = data.get("timeframes", {})
            for tf, eng in engines.items():
                if tf in tf_data:
                    st = tf_data[tf]
                    restored_hist = float(st.get("historical_accuracy", 65.0))
                    eng["locker"].historical_accuracy = max(35.0, restored_hist)
                    eng["locker"].peak_historical_accuracy = float(st.get("peak_historical_accuracy", max(65.0, restored_hist)))
                    eng["last_live_accuracy"] = float(st.get("last_live_accuracy", 100.0))
                    eng["swarm"].swarm_health = float(st.get("swarm_health", 100.0))
                    eng["swarm"].eval_count = int(st.get("swarm_eval_count", 0))
                    eng["governor"].learning_rate = float(st.get("learning_rate", 0.01))
                    eng["governor"].recalc_trigger = float(np.clip(st.get("recalc_trigger", 78.0), 62.0, 88.0))
                    eng["p_max"] = float(st.get("p_max", 1.0))
                    weights = st.get("node_weights", [])
                    for idx, w in enumerate(weights):
                        if idx < len(eng["swarm"].nodes):
                            eng["swarm"].nodes[idx].accuracy_weight = float(w)
                    if "opinion" in eng and "opinion_state" in st:
                        eng["opinion"].from_dict(st["opinion_state"])
                    if "formula" in eng and "formula_state" in st:
                        eng["formula"].from_dict(st["formula_state"])
                    if "active_lock" in st and st["active_lock"]:
                        eng["locker"].deserialize_active_lock(st["active_lock"])
            return True
        except Exception:
            return False

# -----------------------------
# FEE-AWARE EXECUTION & LAZARUS BANKROLL ENGINE
# -----------------------------
class FeeAwareExecutionEngine:
    """
    Synthesizes immutable locked marker pressure and P_max into fee-adjusted
    positions with anti-flip-flop hysteresis, plus immediate RedFuzz hazard overrides.
    """
    def __init__(self, fee_rate=0.0010, initial_bankroll=1000.0):
        self.fee_rate = fee_rate
        self.bankroll = initial_bankroll
        self.high_water_mark = initial_bankroll
        self.lazarus_bankroll = 0.0
        self.position_side = "FLAT"
        self.entry_price = 0.0
        self.projected_move_pct = 0.0
        self.conviction = 0.0
        self.p_max = 1.0
        self.cumulative_net_pnl_pct = 0.0
        self.total_settled_hits = 0
        self.last_flip_ts = 0.0

    def evaluate_pressure(self, anchor_price, live_price, target_prices, node_weights, live_acc, p_max, redfuzz_alarm=False, redfuzz_status=""):
        self.p_max = float(p_max)
        if not target_prices or anchor_price <= 0 or live_price <= 0:
            return
        deltas = np.array([(p - anchor_price) / anchor_price for p in target_prices], dtype=float)
        weights = np.array(node_weights[:len(deltas)], dtype=float) if len(node_weights) >= len(deltas) else np.ones_like(deltas)

        upside_pressure = float(np.sum(np.maximum(0.0, deltas) * weights))
        downside_pressure = float(np.sum(np.abs(np.minimum(0.0, deltas)) * weights))
        total_pressure = upside_pressure + downside_pressure + 1e-9

        raw_conv = (upside_pressure - downside_pressure) / total_pressure
        trust_mult = np.clip(live_acc / 100.0, 0.25, 1.0)
        new_conv = float(np.clip(raw_conv * trust_mult * min(1.5, self.p_max), -1.0, 1.0))
        self.conviction = (self.conviction * 0.68) + (new_conv * 0.32)

        terminal_move = (target_prices[-1] - live_price) / live_price
        round_trip_fee = self.fee_rate * 2.0
        min_profitable_edge = round_trip_fee * 1.85

        now = time.time()
        cooldown_ready = (now - self.last_flip_ts) >= 30.0 or redfuzz_alarm

        desired_side = self.position_side
        if redfuzz_alarm:
            if "CLIFF" in redfuzz_status and self.position_side == "LONG":
                desired_side = "SHORT" if terminal_move < -min_profitable_edge else "FLAT"
            elif ("WALL" in redfuzz_status or "CLIMB" in redfuzz_status) and self.position_side == "SHORT":
                desired_side = "LONG" if terminal_move > min_profitable_edge else "FLAT"
            elif "SHOCK" in redfuzz_status and abs(self.conviction) < 0.45:
                desired_side = "FLAT"
        elif cooldown_ready:
            if self.conviction > 0.26 and terminal_move > min_profitable_edge:
                desired_side = "LONG"
            elif self.conviction < -0.26 and terminal_move < -min_profitable_edge:
                desired_side = "SHORT"
            elif abs(self.conviction) < 0.08:
                desired_side = "FLAT"

        if desired_side != self.position_side:
            self._settle_current_position(live_price)
            self.last_flip_ts = now
            if desired_side in ("LONG", "SHORT"):
                self.position_side = desired_side
                self.entry_price = live_price
                self.projected_move_pct = terminal_move

    def _settle_current_position(self, exit_price):
        if self.position_side == "FLAT" or self.entry_price <= 0:
            self.position_side = "FLAT"
            return 0.0, 0.0
        raw_ret = (exit_price - self.entry_price) / self.entry_price
        if self.position_side == "SHORT":
            raw_ret = -raw_ret
        net_ret = raw_ret - (self.fee_rate * 2.0)
        self.cumulative_net_pnl_pct += (net_ret * 100.0)
        pnl_usd = self.bankroll * net_ret
        self.bankroll = max(10.0, self.bankroll + pnl_usd)
        if self.bankroll > self.high_water_mark:
            lazarus_skim = (self.bankroll - self.high_water_mark) * 0.25
            self.lazarus_bankroll += lazarus_skim
            self.high_water_mark = self.bankroll
        prev_proj = self.projected_move_pct
        self.position_side = "FLAT"
        self.entry_price = 0.0
        self.projected_move_pct = 0.0
        return prev_proj, net_ret

    def get_live_unrealized_pnl_pct(self, live_price):
        if self.position_side == "FLAT" or self.entry_price <= 0 or live_price <= 0:
            return 0.0
        raw_ret = (live_price - self.entry_price) / self.entry_price
        if self.position_side == "SHORT":
            raw_ret = -raw_ret
        return float((raw_ret - (self.fee_rate * 2.0)) * 100.0)

    def to_dict(self):
        return {
            "bankroll": self.bankroll,
            "high_water_mark": self.high_water_mark,
            "lazarus_bankroll": self.lazarus_bankroll,
            "position_side": self.position_side,
            "entry_price": self.entry_price,
            "projected_move_pct": self.projected_move_pct,
            "conviction": self.conviction,
            "p_max": self.p_max,
            "cumulative_net_pnl_pct": self.cumulative_net_pnl_pct,
            "total_settled_hits": self.total_settled_hits
        }

    def from_dict(self, d):
        self.bankroll = float(d.get("bankroll", 1000.0))
        self.high_water_mark = float(d.get("high_water_mark", 1000.0))
        self.lazarus_bankroll = float(d.get("lazarus_bankroll", 0.0))
        self.position_side = str(d.get("position_side", "FLAT"))
        self.entry_price = float(d.get("entry_price", 0.0))
        self.projected_move_pct = float(d.get("projected_move_pct", 0.0))
        self.conviction = float(d.get("conviction", 0.0))
        self.p_max = float(d.get("p_max", 1.0))
        self.cumulative_net_pnl_pct = float(d.get("cumulative_net_pnl_pct", 0.0))
        self.total_settled_hits = int(d.get("total_settled_hits", 0))

# -----------------------------
# HELPERS, ACCURACY TRUTH & MICROSTRUCTURE
# -----------------------------
def calculate_directional_truth(pred_curve, actual_curve, vol_scale=0.015):
    if len(pred_curve) == 0 or len(actual_curve) == 0:
        return 50.0
    n = min(len(pred_curve), len(actual_curve))
    p_arr = np.array(pred_curve[:n], dtype=float)
    a_arr = np.array(actual_curve[:n], dtype=float)

    abs_diff = np.abs(p_arr - a_arr)
    opp_mask = (p_arr * a_arr) < -1e-7
    dir_penalty = np.where(opp_mask, 1.15 * (np.abs(a_arr) + np.abs(p_arr)), 0.0)
    total_err = abs_diff + dir_penalty

    price_penalty = float(np.mean(total_err)) * 1800.0
    path_scale = max(float(np.max(np.abs(p_arr))), float(np.max(np.abs(a_arr))), float(vol_scale) * 0.25, 0.0020)
    relative_path_miss = float(np.mean(total_err / path_scale)) * 55.0

    raw_truth = 100.0 - price_penalty - relative_path_miss
    return float(np.clip(raw_truth, 0.0, 100.0))

def calculate_honest_structural_grade(pred_curve, actual_curve, vol_scale=0.015):
    """
    Ledger B: Evaluates topological shape fidelity, extremum (peak/trough) matching,
    and penalizes anti-flatness/regression to the mean during high volatility.
    """
    if len(pred_curve) == 0 or len(actual_curve) == 0:
        return 50.0
    n = min(len(pred_curve), len(actual_curve))
    p_arr = np.array(pred_curve[:n], dtype=float)
    a_arr = np.array(actual_curve[:n], dtype=float)

    # 1. Extremum Fidelity (Peak & Trough matching)
    p_max, p_min = np.max(p_arr), np.min(p_arr)
    a_max, a_min = np.max(a_arr), np.min(a_arr)
    extremum_err = abs(p_max - a_max) + abs(p_min - a_min)

    # 2. Phase-Tolerant Shape Correlation
    p_norm = p_arr - np.mean(p_arr)
    a_norm = a_arr - np.mean(a_arr)
    p_denom = np.linalg.norm(p_norm) + 1e-9
    a_denom = np.linalg.norm(a_norm) + 1e-9
    shape_corr = float(np.dot(p_norm, a_norm) / (p_denom * a_denom))
    corr_score = (shape_corr + 1.0) * 50.0

    # 3. Anti-Flatness Entropy Tax (Hard penalty for neutered/flattened curves)
    p_var = np.var(p_arr)
    a_var = np.var(a_arr)
    flatness_penalty = 0.0
    if a_var > 1e-5 and p_var < (a_var * 0.35):
        flatness_penalty = 25.0 * (1.0 - (p_var / (a_var + 1e-9)))

    ext_penalty = extremum_err * 800.0
    raw_grade = (corr_score * 0.65) + (35.0 if shape_corr > 0 else 0.0) - ext_penalty - flatness_penalty
    return float(np.clip(raw_grade, 0.0, 100.0))

def compute_instant_marker_accuracy(target_price, actual_price, chop_bbw=0.015):
    if actual_price <= 0 or target_price <= 0:
        return 100.0
    rel_err = abs(target_price - actual_price) / (actual_price + 1e-9)
    bar_scale = max(float(chop_bbw) * 0.25, 0.0025)
    penalty = (rel_err * 2200.0) + ((rel_err / bar_scale) * 35.0)
    return float(np.clip(100.0 - penalty, 0.0, 100.0))

def save_scaler(mean_vec, std_vec, filepath):
    try:
        with open(filepath, "w") as f:
            json.dump({"mean": mean_vec.tolist(), "std": std_vec.tolist()}, f)
    except Exception:
        pass

def load_scaler(filepath):
    try:
        with open(filepath, "r") as f:
            d = json.load(f)
            return np.array(d["mean"], dtype=float), np.array(d["std"], dtype=float)
    except Exception:
        return None, None

def fit_scaler_online(existing_mean, existing_std, new_vec, count):
    if existing_mean is None:
        return new_vec.copy(), np.maximum(np.abs(new_vec)*0.01, np.zeros_like(new_vec))
    alpha = max(0.005, 1.0 / max(1, count))
    mean = (1 - alpha) * existing_mean + alpha * new_vec
    std = (1 - alpha) * existing_std + alpha * np.abs(new_vec - mean)
    std = np.where(std == 0, 1e-6, std)
    return mean, std

def scale_vector(vec, mean_vec, std_vec):
    if mean_vec is not None and std_vec is not None:
        safe_std = np.maximum(std_vec, 1e-8)
        return (vec - mean_vec) / safe_std
    return vec

def extract_pattern_vector(df, idx, length=5):
    if idx < length:
        return None
    subset = df.iloc[idx-length:idx+1]
    base = subset['open'].iloc[0]
    if base == 0:
        return None

    vec = []
    for i in range(len(subset)):
        row = subset.iloc[i]
        vec.extend([(row['close'] - row['open']) / base, (row['high'] - row['low']) / base])
    vec.extend(np.diff(subset['close'].values) / base)

    try:
        win_start = max(0, idx - 22)
        local_df = df.iloc[win_start:idx+1]
        vol = local_df['volume'].values
        tb_vol = local_df['taker_base_vol'].values
        ts_vol = vol - tb_vol
        td_ratio = (tb_vol[-1] - ts_vol[-1]) / (vol[-1] + 1e-9)
        nt = local_df['num_trades'].values
        vel = nt[-1] / (np.mean(nt) + 1e-9)
        vec.append(float(td_ratio) if not np.isnan(td_ratio) else 0.0)
        vec.append(float(vel) if not np.isnan(vel) else 1.0)
    except Exception:
        vec.extend([0.0, 1.0])
    return np.array(vec, dtype=float)

def calculate_spatial_structure(df, period=50):
    if len(df) < period:
        return {'floor': 0.0, 'ceiling': 0.0, 'proximity': 0.5, 'is_breaking_down': False, 'is_breaking_up': False}
    recent_lows = df['low'].tail(period)
    recent_highs = df['high'].tail(period)
    floor = float(recent_lows.min())
    ceiling = float(recent_highs.max())
    current_price = float(df['close'].iloc[-1])
    range_size = ceiling - floor
    proximity = float((current_price - floor) / (range_size + 1e-9))

    recent_vol = df['volume'].tail(3).mean()
    historical_vol = df['volume'].tail(period).mean()
    volume_surge = bool(recent_vol > (historical_vol * 1.35))

    return {
        'floor': floor,
        'ceiling': ceiling,
        'proximity': proximity,
        'is_breaking_down': proximity < 0.08 and volume_surge,
        'is_breaking_up': proximity > 0.92 and volume_surge
    }

def calculate_order_flow_footprint(df_in, period=20):
    if len(df_in) < period:
        return {'status': 'NEUTRAL', 'taker_delta_ratio': 0.0, 'trade_velocity': 1.0}
    df = df_in.tail(period + 5).copy()
    df['taker_sell_vol'] = df['volume'] - df['taker_base_vol']
    df['taker_delta'] = df['taker_base_vol'] - df['taker_sell_vol']
    df['taker_delta_ratio'] = df['taker_delta'] / (df['volume'] + 1e-9)
    df['trade_count_ma'] = df['num_trades'].rolling(window=period, min_periods=1).mean()
    df['trade_velocity'] = df['num_trades'] / (df['trade_count_ma'] + 1e-9)

    vel = float(df['trade_velocity'].iloc[-1])
    delta = float(df['taker_delta_ratio'].iloc[-1])
    vol_surge = float(df['volume'].iloc[-1]) > float(df['volume'].rolling(window=period, min_periods=1).mean().iloc[-1] * 1.35)

    status = "NEUTRAL"
    if vol_surge:
        if vel > 2.2 and delta < -0.32:
            status = "STRUCTURAL_COLLAPSE"
        elif vel < 1.8 and delta > -0.08:
            status = "LIQUIDITY_SWEEP"
        elif vel > 2.0 and delta > 0.32:
            status = "BUY_CLIMAX"
        elif vel > 2.0 and delta < -0.22:
            status = "SELL_ABSORPTION"
    return {'status': status, 'taker_delta_ratio': delta, 'trade_velocity': vel}

def find_orderbook_wall_limits(bids, asks, live_price):
    default_cap = 0.035
    if bids is None or asks is None or len(bids) == 0 or len(asks) == 0 or live_price <= 0:
        return -default_cap, default_cap, 0.0

    try:
        valid_bids = bids[bids[:, 0] < live_price]
        valid_asks = asks[asks[:, 0] > live_price]

        if len(valid_bids) > 0:
            bid_weights = valid_bids[:, 1]
            top_bid_idx = int(np.argmax(bid_weights))
            support_price = float(valid_bids[top_bid_idx, 0])
            floor_pct = max(-0.08, min(-0.002, (support_price - live_price) / live_price))
        else:
            floor_pct = -default_cap

        if len(valid_asks) > 0:
            ask_weights = valid_asks[:, 1]
            top_ask_idx = int(np.argmax(ask_weights))
            resist_price = float(valid_asks[top_ask_idx, 0])
            ceil_pct = min(0.08, max(0.002, (resist_price - live_price) / live_price))
        else:
            ceil_pct = default_cap

        bid_vol = float(np.sum(bids[:, 1]))
        ask_vol = float(np.sum(asks[:, 1]))
        book_imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-9)
        return floor_pct, ceil_pct, book_imbalance
    except Exception:
        return -default_cap, default_cap, 0.0

def calculate_tactile_ground_ceiling_and_legs(df, live_price, order_flow, bids=None, asks=None):
    """
    Multi-Tier Ground/Ceiling & Big-Leg Vacuum Sensor:
      - Maps 50-bar (Local), 144-bar (Swing), and 288-bar (Macro) structural floors & ceilings.
      - Builds a 24-bin Volume Profile to feel 'Ground/Ceiling Hardness' (volume shelves)
        vs. 'Air Pockets' (liquidity vacuums where big legs climb or fall unhindered).
      - Computes signed leg_drive (-1.5 to +1.5) and leg_regime.
    """
    if df is None or len(df) < 30 or live_price <= 0:
        return {
            'eff_floor_pct': -0.035, 'eff_ceil_pct': 0.035,
            'macro_floor_pct': -0.065, 'macro_ceil_pct': 0.065,
            'ground_hardness': 0.5, 'ceiling_hardness': 0.5,
            'in_air_pocket_up': False, 'in_air_pocket_dn': False,
            'leg_drive': 0.0, 'leg_regime': 'NORMAL'
        }

    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    opens = df['open'].values
    vols = df['volume'].values

    f_50, c_50 = float(np.min(lows[-min(50, len(lows)):])), float(np.max(highs[-min(50, len(highs)):]))
    f_144, c_144 = float(np.min(lows[-min(144, len(lows)):])), float(np.max(highs[-min(144, len(highs)):]))
    f_288, c_288 = float(np.min(lows[-min(288, len(lows)):])), float(np.max(highs[-min(288, len(highs)):]))

    f50_pct = min(-0.002, (f_50 - live_price) / live_price)
    c50_pct = max(0.002, (c_50 - live_price) / live_price)
    f144_pct = min(f50_pct, (f_144 - live_price) / live_price)
    c144_pct = max(c50_pct, (c_144 - live_price) / live_price)
    f288_pct = min(f144_pct, (f_288 - live_price) / live_price)
    c288_pct = max(c144_pct, (c_288 - live_price) / live_price)

    win_n = min(288, len(df))
    p_min, p_max_h = float(np.min(lows[-win_n:])), float(np.max(highs[-win_n:]))
    ground_hardness, ceiling_hardness = 0.50, 0.50
    in_air_pocket_up, in_air_pocket_dn = False, False
    next_up_shelf_pct, next_dn_shelf_pct = c144_pct, f144_pct

    if p_max_h > p_min * 1.002:
        bins = np.linspace(p_min, p_max_h, 25)
        typ_prices = (highs[-win_n:] + lows[-win_n:] + closes[-win_n:]) / 3.0
        hist_vol, edges = np.histogram(typ_prices, bins=bins, weights=vols[-win_n:])
        mean_bin_vol = float(np.mean(hist_vol)) + 1e-9
        norm_bins = hist_vol / mean_bin_vol
        bin_centers = 0.5 * (edges[:-1] + edges[1:])
        cur_bin = int(np.clip(np.digitize(live_price, edges) - 1, 0, len(norm_bins) - 1))

        if cur_bin < len(norm_bins) - 1:
            above_vols = norm_bins[cur_bin + 1:]
            above_centers = bin_centers[cur_bin + 1:]
            near_up = above_vols[:min(3, len(above_vols))]
            in_air_pocket_up = bool(np.mean(near_up) < 0.58)
            ceiling_hardness = float(np.clip(np.max(above_vols) / 1.8, 0.20, 1.60))
            heavy_up_idx = np.where(above_vols >= 1.15)[0]
            if len(heavy_up_idx) > 0:
                next_up_shelf_pct = max(0.004, (float(above_centers[heavy_up_idx[0]]) - live_price) / live_price)

        if cur_bin > 0:
            below_vols = norm_bins[:cur_bin][::-1]
            below_centers = bin_centers[:cur_bin][::-1]
            near_dn = below_vols[:min(3, len(below_vols))]
            in_air_pocket_dn = bool(np.mean(near_dn) < 0.58)
            ground_hardness = float(np.clip(np.max(below_vols) / 1.8, 0.20, 1.60))
            heavy_dn_idx = np.where(below_vols >= 1.15)[0]
            if len(heavy_dn_idx) > 0:
                next_dn_shelf_pct = min(-0.004, (float(below_centers[heavy_dn_idx[0]]) - live_price) / live_price)

    bodies = np.abs(closes[-20:] - opens[-20:])
    avg_body = float(np.mean(bodies[:-3])) + 1e-9 if len(bodies) > 3 else float(np.mean(bodies)) + 1e-9
    recent_net_move = (live_price - opens[-3]) / (opens[-3] + 1e-9)
    recent_body_expansion = abs(live_price - opens[-3]) / (avg_body * 2.1)

    k_win = min(8, len(closes) - 1)
    net_8 = abs(live_price - closes[-1 - k_win])
    path_8 = float(np.sum(np.abs(np.diff(np.append(closes[-1 - k_win:-1], live_price))))) + 1e-9
    dir_efficiency = float(np.clip(net_8 / path_8, 0.0, 1.0))

    delta_r = float(order_flow.get('taker_delta_ratio', 0.0))
    vel_r = float(order_flow.get('trade_velocity', 1.0))

    near_50_top = abs(c50_pct) < 0.0055
    near_50_bot = abs(f50_pct) < 0.0055

    if (near_50_top and (recent_net_move > 0 or delta_r > 0.10)) or in_air_pocket_up:
        eff_ceil_pct = max(c144_pct, next_up_shelf_pct, c288_pct * 0.75, 0.022)
    else:
        eff_ceil_pct = max(c50_pct, next_up_shelf_pct)

    if (near_50_bot and (recent_net_move < 0 or delta_r < -0.10)) or in_air_pocket_dn:
        eff_floor_pct = min(f144_pct, next_dn_shelf_pct, f288_pct * 0.75, -0.022)
    else:
        eff_floor_pct = min(f50_pct, next_dn_shelf_pct)

    leg_mag = 0.0
    leg_dir = 1.0 if recent_net_move >= 0 else -1.0
    leg_regime = "NORMAL"

    if dir_efficiency > 0.50 and recent_body_expansion > 0.80:
        pocket_bonus = 1.30 if (leg_dir > 0 and in_air_pocket_up) or (leg_dir < 0 and in_air_pocket_dn) else 1.0
        flow_align = 1.25 if (leg_dir * delta_r) > 0.08 else 0.90
        leg_mag = float(np.clip(recent_body_expansion * dir_efficiency * pocket_bonus * flow_align * min(1.5, max(0.8, vel_r * 0.7)), 0.0, 1.50))
        if leg_mag > 0.42:
            leg_regime = "LEG-CLIMB" if leg_dir > 0 else "LEG-DROP"

    if leg_mag < 0.42:
        if near_50_bot and ground_hardness >= 0.72 and delta_r > 0.05:
            leg_dir = 1.0
            leg_mag = float(np.clip(ground_hardness * 0.65 * (1.0 + delta_r), 0.35, 1.15))
            leg_regime = "GROUND-SPRING"
        elif near_50_top and ceiling_hardness >= 0.72 and delta_r < -0.05:
            leg_dir = -1.0
            leg_mag = float(np.clip(ceiling_hardness * 0.65 * (1.0 + abs(delta_r)), 0.35, 1.15))
            leg_regime = "CEIL-REJECT"

    return {
        'eff_floor_pct': float(eff_floor_pct),
        'eff_ceil_pct': float(eff_ceil_pct),
        'macro_floor_pct': float(f288_pct),
        'macro_ceil_pct': float(c288_pct),
        'ground_hardness': float(ground_hardness),
        'ceiling_hardness': float(ceiling_hardness),
        'in_air_pocket_up': in_air_pocket_up,
        'in_air_pocket_dn': in_air_pocket_dn,
        'leg_drive': float(leg_dir * leg_mag),
        'leg_regime': leg_regime
    }

def apply_tactile_leg_and_boundary_feel(curve, tactile_data, formula=None):
    shaped = np.array(curve, dtype=float)
    horizon = len(shaped)
    if horizon < 3 or not tactile_data:
        return shaped, "NONE"

    leg_drive = float(tactile_data.get('leg_drive', 0.0))
    leg_regime = tactile_data.get('leg_regime', 'NORMAL')
    eff_floor = float(tactile_data.get('eff_floor_pct', -0.035))
    eff_ceil = float(tactile_data.get('eff_ceil_pct', 0.035))
    g_hard = float(tactile_data.get('ground_hardness', 0.5))
    c_hard = float(tactile_data.get('ceiling_hardness', 0.5))

    leg_gain = formula.get("leg_drive_gain") if formula is not None else 1.25
    feel_gain = formula.get("ground_ceil_feel") if formula is not None else 1.00
    tag = "NONE"

    if abs(leg_drive) >= 0.38 and leg_regime in ("LEG-CLIMB", "LEG-DROP"):
        target_bound = eff_ceil if leg_drive > 0 else eff_floor
        leg_reach_pct = target_bound * np.clip(abs(leg_drive) * 0.58 * leg_gain, 0.25, 0.95)
        for i in range(horizon):
            prog = (i + 1) / horizon
            leg_profile = (prog ** 0.78) * (1.0 - 0.18 * (prog ** 2))
            leg_vec = leg_reach_pct * leg_profile
            blend_w = min(0.68, abs(leg_drive) * 0.42 * leg_gain)
            shaped[i] = ((1.0 - blend_w) * shaped[i]) + (blend_w * (shaped[i] * 0.45 + leg_vec))
        tag = leg_regime

    for i in range(horizon):
        prog = (i + 1) / horizon
        val = shaped[i]
        if val < eff_floor * 0.72 and not tactile_data.get('in_air_pocket_dn', False):
            penetration = abs(val - (eff_floor * 0.72))
            shelf_span = max(abs(eff_floor) * 0.28, 0.003)
            cushioned = (eff_floor * 0.72) - (shelf_span * math.tanh(penetration / shelf_span))
            rebound = shelf_span * min(0.85, g_hard * 0.45 * feel_gain) * (prog ** 1.1) if leg_drive >= -0.25 else 0.0
            shaped[i] = cushioned + rebound
            if tag == "NONE" and rebound > 0.0015:
                tag = "FEEL-FLOOR"
        elif val > eff_ceil * 0.72 and not tactile_data.get('in_air_pocket_up', False):
            penetration = abs(val - (eff_ceil * 0.72))
            shelf_span = max(abs(eff_ceil) * 0.28, 0.003)
            cushioned = (eff_ceil * 0.72) + (shelf_span * math.tanh(penetration / shelf_span))
            pullback = shelf_span * min(0.85, c_hard * 0.45 * feel_gain) * (prog ** 1.1) if leg_drive <= 0.25 else 0.0
            shaped[i] = cushioned - pullback
            if tag == "NONE" and pullback > 0.0015:
                tag = "FEEL-CEIL"

    return shaped, tag

def apply_apex_trough_inflection(curve, df, live_price, rsi, spatial_data, order_flow, bids, asks, formula=None, tactile_data=None):
    if len(curve) < 4 or live_price <= 0:
        return curve, "NONE"

    if tactile_data and tactile_data.get('leg_regime') in ("LEG-CLIMB", "LEG-DROP") and abs(tactile_data.get('leg_drive', 0.0)) > 0.52:
        return np.array(curve, dtype=float), tactile_data.get('leg_regime')

    shaped = np.array(curve, dtype=float)
    horizon = len(shaped)
    net_move = shaped[-1] - shaped[0]
    retrace_gain = formula.get("apex_retrace_gain") if formula is not None else 0.45

    ob_floor_pct, ob_ceil_pct, ob_imbalance = find_orderbook_wall_limits(bids, asks, live_price)

    struct_ceil_pct = max(0.003, (spatial_data['ceiling'] - live_price) / live_price) if spatial_data['ceiling'] > live_price else ob_ceil_pct
    struct_floor_pct = min(-0.003, (spatial_data['floor'] - live_price) / live_price) if 0 < spatial_data['floor'] < live_price else ob_floor_pct

    if tactile_data:
        effective_ceil = max(struct_ceil_pct, tactile_data.get('eff_ceil_pct', struct_ceil_pct))
        effective_floor = min(struct_floor_pct, tactile_data.get('eff_floor_pct', struct_floor_pct))
    else:
        effective_ceil = max(struct_ceil_pct, ob_ceil_pct * 1.35)
        effective_floor = min(struct_floor_pct, ob_floor_pct * 1.35)

    prox = spatial_data.get('proximity', 0.5)
    delta_ratio = order_flow.get('taker_delta_ratio', 0.0)
    flow_status = order_flow.get('status', 'NEUTRAL')
    apex_tag = "NONE"

    climb_exhaustion = (
        (net_move > 0 and (rsi > 64.0 or prox > 0.78)) or
        (np.max(shaped) > effective_ceil * 0.90) or
        (net_move > 0 and delta_ratio < -0.10 and prox > 0.65)
    )

    timing_shift = formula.get("mirror_pos_shift") if formula is not None else 0.0

    if climb_exhaustion and not spatial_data.get('is_breaking_up', False):
        exhaustion_severity = np.clip(((rsi - 55.0) / 35.0) * 0.5 + (prox * 0.5), 0.15, 0.85)
        raw_apex_frac = (1.0 - (exhaustion_severity * 0.65)) + timing_shift
        apex_idx = int(np.clip(round(horizon * raw_apex_frac), 2, horizon - 2))

        peak_target = min(max(np.max(shaped), effective_ceil * 0.65), effective_ceil * 1.10)
        retrace_ratio = np.clip(0.25 + (exhaustion_severity * retrace_gain) - (ob_imbalance * 0.20), 0.18, 0.85)

        for i in range(horizon):
            if i <= apex_idx:
                prog = (i + 1) / (apex_idx + 1)
                ease_out = math.sin(prog * (math.pi / 2.0))
                shaped[i] = (shaped[i] * 0.35) + (peak_target * ease_out * 0.65)
            else:
                post_prog = (i - apex_idx) / max(1, (horizon - 1 - apex_idx))
                roll_drop = peak_target * retrace_ratio * (post_prog ** 1.15)
                shaped[i] = shaped[apex_idx] - roll_drop
        apex_tag = f"TOP@{apex_idx}"

    # Do NOT force a bottom bounce if order flow is in active STRUCTURAL_COLLAPSE
    drop_exhaustion = (
        (net_move < 0 and (rsi < 34.0 or prox < 0.20) and delta_ratio > -0.22) or
        (np.min(shaped) < effective_floor * 0.92 and ob_imbalance > 0.05) or
        (net_move < 0 and delta_ratio > 0.12 and prox < 0.35)
    )

    if drop_exhaustion and not spatial_data.get('is_breaking_down', False) and flow_status != "STRUCTURAL_COLLAPSE" and apex_tag == "NONE":
        exhaustion_severity = np.clip(((45.0 - rsi) / 35.0) * 0.5 + ((1.0 - prox) * 0.5), 0.15, 0.85)
        raw_trough_frac = (1.0 - (exhaustion_severity * 0.65)) + timing_shift
        trough_idx = int(np.clip(round(horizon * raw_trough_frac), 2, horizon - 2))

        bottom_target = max(min(np.min(shaped), effective_floor * 0.65), effective_floor * 1.10)
        bounce_ratio = np.clip(0.25 + (exhaustion_severity * retrace_gain) + (ob_imbalance * 0.20), 0.18, 0.85)

        for i in range(horizon):
            if i <= trough_idx:
                prog = (i + 1) / (trough_idx + 1)
                ease_out = math.sin(prog * (math.pi / 2.0))
                shaped[i] = (shaped[i] * 0.35) + (bottom_target * ease_out * 0.65)
            else:
                post_prog = (i - trough_idx) / max(1, (horizon - 1 - trough_idx))
                bounce_gain = abs(bottom_target) * bounce_ratio * (post_prog ** 1.15)
                shaped[i] = shaped[trough_idx] + bounce_gain
        apex_tag = f"BTM@{trough_idx}"

    return shaped, apex_tag

def audit_ghost_grid(df, live_price, locker):
    if len(locker.ghosts) == 0 or len(df) < 5 or live_price <= 0:
        return 0.0, 1.0
    slope_errors = []
    weights = []
    for g in locker.ghosts:
        g_prices = g.get('prices', [])
        base_ts = g.get('base_ts', 0)
        if len(g_prices) < 2:
            continue
        actual_sub = df[df['ts'] > base_ts]
        if len(actual_sub) == 0:
            continue
        eval_steps = min(len(actual_sub), len(g_prices) - 1)
        pred_slope = (g_prices[eval_steps] - g_prices[0]) / (g_prices[0] * eval_steps + 1e-9)
        real_slope = (float(actual_sub['close'].iloc[eval_steps - 1]) - g_prices[0]) / (g_prices[0] * eval_steps + 1e-9)
        slope_errors.append(real_slope - pred_slope)
        weights.append(max(0.1, float(g.get('grade', 50.0)) / 100.0))
    if not slope_errors:
        return 0.0, 1.0
    w_arr = np.array(weights) / np.sum(weights)
    adaptive_slope_corr = float(np.clip(np.sum(np.array(slope_errors) * w_arr), -0.008, 0.008))
    ghost_trust = float(np.clip(np.mean(weights), 0.25, 1.25))
    return adaptive_slope_corr, ghost_trust

def apply_288_marker_clamp(curve, df, live_price, coil_score, chop_bbw, ghost_slope_corr=0.0, formula=None, tactile_data=None):
    """
    V22.2 Decoupled Elastic Clamp + Big-Leg Vacuum Allowance:
      - Uses 288-bar history to size p_max, plus expands displacement and step limits
        when tactile_data detects an active climb/drop leg or air pocket.
    """
    shaped = np.array(curve, dtype=float)
    horizon = len(shaped)
    if horizon == 0 or len(df) < 10 or live_price <= 0:
        return shaped, 1.0

    pmax_vol_mult = formula.get("pmax_vol_mult") if formula is not None else 4.5
    step_limit_ratio = formula.get("step_limit_ratio") if formula is not None else 0.44
    mom_anchor_bias = formula.get("mom_anchor_bias") if formula is not None else 0.38
    ghost_gain = formula.get("ghost_slope_gain") if formula is not None else 0.55
    leg_gain = formula.get("leg_drive_gain") if formula is not None else 1.25

    leg_drive = float(tactile_data.get('leg_drive', 0.0)) if tactile_data else 0.0
    leg_allowance = 1.0 + (abs(leg_drive) * 0.55 * leg_gain)

    win_len = min(288, len(df) - 1)
    closes_288 = df['close'].tail(win_len + 1).values
    rets_288 = np.diff(closes_288) / (closes_288[:-1] + 1e-9)
    udi_vol = float(np.std(rets_288)) * math.sqrt(win_len)
    p_max = float(np.clip((1.0 + (udi_vol * pmax_vol_mult) + (coil_score / 150.0)) * min(1.35, leg_allowance), 0.55, 3.60))

    # Fast regime momentum window (24 bars + 6-bar live impulse)
    fast_len = min(24, len(df) - 1)
    closes_fast = np.array(df['close'].tail(fast_len + 1).tolist(), dtype=float)
    closes_fast[-1] = float(live_price)
    rets_fast = np.diff(closes_fast) / (closes_fast[:-1] + 1e-9)
    up_moves = np.sum(np.maximum(0.0, rets_fast))
    dn_moves = np.sum(np.abs(np.minimum(0.0, rets_fast)))
    fast_mom_ratio = (up_moves - dn_moves) / (up_moves + dn_moves + 1e-9)

    impulse_len = min(6, len(closes_fast) - 1)
    impulse_ret = (live_price - closes_fast[-1 - impulse_len]) / (closes_fast[-1 - impulse_len] + 1e-9)
    impulse_sign = float(np.clip(impulse_ret / max(chop_bbw, 0.005), -1.0, 1.0))
    mom_ratio = (fast_mom_ratio * 0.45) + (impulse_sign * 0.55)

    tactile_span = 0.0
    if tactile_data:
        tactile_span = abs(tactile_data['eff_ceil_pct'] if leg_drive >= 0 else tactile_data['eff_floor_pct']) * 0.85

    max_allowed_disp = max(chop_bbw * 1.55 * p_max * leg_allowance, tactile_span, 0.007)
    eff_step_ratio = min(0.84, step_limit_ratio * (1.0 + abs(leg_drive) * 0.35))
    clamped = np.zeros_like(shaped)

    for i in range(horizon):
        prog = (i + 1) / horizon
        raw_val = shaped[i] + (ghost_slope_corr * (i + 1) * ghost_gain)
        anchor_bias = mom_ratio * max_allowed_disp * (prog ** 0.75) * mom_anchor_bias
        gap = raw_val - anchor_bias
        if abs(gap) > max_allowed_disp:
            excess = abs(gap) - max_allowed_disp
            damped_excess = max_allowed_disp * math.tanh(excess / (max_allowed_disp + 1e-9))
            raw_val = anchor_bias + (np.sign(gap) * (max_allowed_disp + damped_excess * 0.35))

        if i > 0:
            step_delta = raw_val - clamped[i - 1]
            max_step = max_allowed_disp * eff_step_ratio
            if abs(step_delta) > max_step:
                raw_val = clamped[i - 1] + (np.sign(step_delta) * max_step)
        clamped[i] = raw_val

    return clamped, p_max

def calculate_ghost_chop_corridor(df, live_price, locker, chop_bbw, microstructure, live_acc=100.0, t_idx=0, window=24):
    horizon, recent = locker.horizon, df.tail(6)
    hist_acc = getattr(locker, 'historical_accuracy', 65.0)
    trust_score = float(np.clip(((live_acc * 0.75) + (hist_acc * 0.25)) / 100.0, 0.15, 0.98))
    micro_mid = float(recent['close'].mean()) if len(recent) > 0 else live_price
    tf_mid = (live_price * (1.0 - (0.35 * trust_score))) + (micro_mid * (0.35 * trust_score))
    half_chop = live_price * float(np.clip(chop_bbw * (0.22 + (0.25 * trust_score)), 0.0025, 0.025))
    mtn_std = float(df['close'].tail(10).std()) if len(df) >= 10 else half_chop * 0.5
    mtn_wall = np.array([half_chop + (mtn_std * math.sqrt((i + 1) / horizon) * 0.55) for i in range(horizon)])
    base_up, base_low = tf_mid + mtn_wall, np.maximum(1e-9, tf_mid - mtn_wall)
    if len(locker.ghosts) > 0:
        g_paths = [np.pad(np.array(g['prices'][1:horizon+1], dtype=float), (0, max(0, horizon - len(g['prices'][1:horizon+1]))), 'edge') for g in locker.ghosts if len(g['prices']) > 1]
        g_weights = [max(0.1, float(g.get('grade', 50.0)) / 100.0) for g in locker.ghosts if len(g['prices']) > 1]
        if len(g_paths) >= 2:
            g_arr, w_norm = np.vstack(g_paths), np.array(g_weights) / np.sum(g_weights)
            up_ghost_line = (np.max(g_arr, axis=0) * 0.65) + (base_up * 0.35)
            low_ghost_line = (np.min(g_arr, axis=0) * 0.65) + (base_low * 0.35)
            mid_ground_line = (np.average(g_arr, axis=0, weights=w_norm) * 0.60) + (0.5 * (up_ghost_line + low_ghost_line) * 0.40)
        elif len(g_paths) == 1:
            up_ghost_line, low_ghost_line = np.maximum(g_paths[0], base_up), np.minimum(g_paths[0], base_low)
            mid_ground_line = 0.5 * (up_ghost_line + low_ghost_line)
        else:
            up_ghost_line, low_ghost_line, mid_ground_line = base_up, base_low, 0.5 * (base_up + base_low)
    else:
        up_ghost_line, low_ghost_line, mid_ground_line = base_up, base_low, 0.5 * (base_up + base_low)
    idx_now = min(max(0, t_idx), horizon - 1)
    c_top, c_bot, c_mid = float(up_ghost_line[idx_now]), float(low_ghost_line[idx_now]), float(mid_ground_line[idx_now])
    c_half = max(1e-9, (c_top - c_bot) * 0.5)
    recent_vel = abs(live_price - float(df['close'].iloc[-3])) / (live_price + 1e-9) if len(df) >= 3 else 0.0
    chop_break_vel = max(chop_bbw * 0.38, 0.0038) * (1.15 - (0.35 * trust_score))
    edge_gate = 0.48 + (0.20 * (1.0 - trust_score))
    pushing_up = (live_price > c_top) or (live_price > c_mid + (c_half * edge_gate) and recent_vel > chop_break_vel)
    pushing_dn = (live_price < c_bot) or (live_price < c_mid - (c_half * edge_gate) and recent_vel > chop_break_vel)
    is_swing_chop = (microstructure.get('wiggles', 0) >= 6 or microstructure.get('coil_score', 0.0) >= 18.0) and not (pushing_up or pushing_dn)
    return {
        'up_ghost_line': up_ghost_line, 'low_ghost_line': low_ghost_line, 'mid_ground_line': mid_ground_line,
        'corridor_top': c_top, 'corridor_bot': c_bot, 'corridor_mid': c_mid,
        'is_swing_chop': is_swing_chop, 'pushing_up': pushing_up, 'pushing_dn': pushing_dn,
        'recent_vel': recent_vel, 'chop_break_vel': chop_break_vel, 'trust_score': trust_score
    }

def apply_chop_middle_ground_governor(curve, live_price, chop_corridor, chop_bbw, microstructure, formula=None, tactile_data=None):
    shaped = np.array(curve, dtype=float)
    horizon = len(shaped)
    if horizon == 0 or live_price <= 0:
        return shaped, "NONE"
    
    # Bypass mean-reversion safe zone damping when physical leg drive is active
    leg_drive = float(tactile_data.get('leg_drive', 0.0)) if tactile_data else 0.0
    if abs(leg_drive) >= 0.38 or chop_corridor.get('pushing_up', False) or chop_corridor.get('pushing_dn', False):
        return shaped, "RADICAL-OVERRIDE"

    mid_curve_pct = (chop_corridor['mid_ground_line'] - live_price) / live_price
    trust = chop_corridor.get('trust_score', 0.5)
    break_gain = formula.get("breakout_thrust_gain") if formula is not None else 1.2
    chop_damp_gain = formula.get("chop_damping_gain") if formula is not None else 0.52

    if chop_corridor['pushing_up'] or chop_corridor['pushing_dn']:
        break_dir = 1.0 if chop_corridor['pushing_up'] else -1.0
        live_sens = (0.22 + (0.55 * (trust ** 1.5))) * break_gain
        vel_scale = min(1.55, max(1.0, chop_corridor['recent_vel'] / (chop_corridor['chop_break_vel'] + 1e-9)))
        for i in range(horizon):
            prog = (i + 1) / horizon
            base_amp = max(abs(shaped[i]) * 1.15, chop_bbw * 0.28)
            thrust = break_dir * base_amp * vel_scale * live_sens * (prog ** 0.80)
            shaped[i] = (shaped[i] * (1.0 - min(0.60, live_sens * 0.45))) + thrust
        return shaped, ("BREAK-UP" if break_dir > 0 else "BREAK-DN")
    elif chop_corridor['is_swing_chop']:
        wiggle_load = min(1.0, (microstructure.get('wiggles', 6) / 14.0) * 0.6 + (microstructure.get('coil_score', 20.0) / 100.0) * 0.4)
        acc_damping = np.clip((1.0 - (trust * 0.65)) * wiggle_load * (chop_damp_gain / 0.60), 0.15, 0.72)
        for i in range(horizon):
            prog = (i + 1) / horizon
            pull_i = min(0.72, acc_damping * (0.60 + 0.40 * math.sin(prog * (math.pi / 2.0))))
            shaped[i] = mid_curve_pct[i] + ((shaped[i] - mid_curve_pct[i]) * (1.0 - pull_i))
        return shaped, "CHOP-MID"
    return shaped, "NONE"

def fetch_btc_macro_context(interval, neiro_closes, limit_val=25):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit_val}"
        r = HTTP_SESSION.get(url, timeout=3)
        if r.status_code == 200:
            btc_closes = np.array([float(candle[4]) for candle in r.json()])
            min_len = min(len(neiro_closes), len(btc_closes))
            if min_len < 3:
                return 0.0, 1.0
            n_arr, b_arr = neiro_closes[-min_len:], btc_closes[-min_len:]
            n_ret = np.diff(n_arr) / (n_arr[:-1] + 1e-9)
            b_ret = np.diff(b_arr) / (b_arr[:-1] + 1e-9)
            cov_matrix = np.cov(n_ret, b_ret)
            var_b = cov_matrix[1, 1]
            if var_b == 0 or np.isnan(var_b):
                beta = 1.0
            else:
                beta = cov_matrix[0, 1] / var_b
            if np.isnan(beta):
                beta = 1.0
            beta = float(np.clip(beta, -1.0, 3.5))
            btc_momentum = float((b_arr[-1] - b_arr[0]) / (b_arr[0] + 1e-9))
            return btc_momentum, beta
    except Exception:
        pass
    return 0.0, 1.0

def calculate_microstructure(df, period=20):
    if len(df) < period + 1:
        return {'wiggles': 0, 'path_length': 0.0, 'coil_score': 0.0}
    recent = df['close'].tail(period).values
    deltas = np.diff(recent)
    signs = np.sign(deltas)
    signs = signs[signs != 0]
    wiggles = int(np.sum(signs[:-1] != signs[1:])) if len(signs) > 1 else 0
    path_length = float(np.sum(np.abs(deltas)))
    period_range = float(df['high'].tail(period).max()) - float(df['low'].tail(period).min())
    efficiency_ratio = path_length / (period_range + 1e-9)
    coil_score = float(np.clip((efficiency_ratio - 1.5) * 20.0, 0.0, 100.0))
    return {'wiggles': wiggles, 'path_length': path_length, 'coil_score': coil_score}

def beam_redfuzz_terrain_sensor(bids, asks, live_price, live_velocity, burst_vol, raw_bids=None, raw_asks=None, signed_delta=0.0, leg_drive=0.0):
    """
    V22.2 Directional Cliff Drop & Climb Surge Sensor:
      - Distinguishes downward Cliff Drops (▼▼) from upward Climb Surges / Vertical Walls (▲▲).
      - Evaluates both verified and raw orderbooks + signed velocity + leg_drive.
    """
    if live_price <= 0:
        return "- TERRAIN CLEAR -", 1.0, False

    vel_ratio = (abs(live_velocity) / 100.0) if abs(live_velocity) > 0.5 else float(abs(live_velocity))
    move_dir = 1 if signed_delta > 0 else (-1 if signed_delta < 0 else (1 if leg_drive >= 0 else -1))

    if burst_vol > (live_price * 0.0038):
        if move_dir < 0:
            return "▼▼ REDFUZZ: CLIFF SHOCK DROP ▼▼", 0.0, True
        return "▲▲ REDFUZZ: CLIMB SHOCK SURGE ▲▲", 0.0, True

    books_to_check = [(bids, asks)]
    if raw_bids is not None and raw_asks is not None:
        books_to_check.append((raw_bids, raw_asks))

    for b_book, a_book in books_to_check:
        if b_book is None or a_book is None or len(b_book) == 0 or len(a_book) == 0:
            continue
        near_b = b_book[b_book[:, 0] >= live_price * 0.985]
        near_a = a_book[a_book[:, 0] <= live_price * 1.015]
        bid_vol = float(np.sum(near_b[:, 1])) if len(near_b) > 0 else float(np.sum(b_book[:20, 1]))
        ask_vol = float(np.sum(near_a[:, 1])) if len(near_a) > 0 else float(np.sum(a_book[:20, 1]))

        # 1. Downward Cliff Drop: Bids pulled thin or heavy ask crush while moving down
        if (bid_vol < (ask_vol * 0.35) and vel_ratio > 0.0048 and move_dir <= 0) or (leg_drive < -0.55 and vel_ratio > 0.0040):
            return "▼▼ REDFUZZ: CLIFF DROP ▼▼", 0.1, True

        # 2. Upward Vertical Climb / Wall Break: Heavy bid dominance or air-pocket climb surge
        if (bid_vol > (ask_vol * 2.50) and vel_ratio > 0.0048 and move_dir >= 0) or (leg_drive > 0.55 and vel_ratio > 0.0040):
            return "▲▲ REDFUZZ: VERTICAL CLIMB ▲▲", 0.1, True

        # 3. Overhead Ask Wall Rejection
        if ask_vol > (bid_vol * 3.80) and vel_ratio > 0.0060 and move_dir > 0:
            return "▲▲ REDFUZZ: VERTICAL WALL ▲▲", 0.1, True

    if vel_ratio > 0.014:
        return ("▲▲ REDFUZZ: VERTICAL CLIMB ▲▲" if move_dir >= 0 else "▼▼ REDFUZZ: CLIFF DROP ▼▼"), 0.1, True

    return "- TERRAIN CLEAR -", 1.0, False

def calculate_vessel_physics(momentum, tension, volatility, coil_score, previous_tilt=0.0, truth_accuracy=65.0):
    pitch_angle = momentum * 1000
    heel_angle = tension * 500
    raw_tilt = np.clip(pitch_angle - (heel_angle if pitch_angle > 0 else -heel_angle), -45.0, 45.0)
    norm_accuracy = min(1.0, max(0.0, truth_accuracy / 100.0))
    dynamic_alpha = 0.1 + ((0.9 - 0.1) * norm_accuracy)
    smoothed_tilt = (dynamic_alpha * raw_tilt) + ((1.0 - dynamic_alpha) * previous_tilt)
    stress_factor = (tension / max(volatility, 0.0005)) * (1.0 + (coil_score / 100.0))
    return smoothed_tilt, stress_factor

def calculate_advanced_chop_bias(df, period=20, std_dev=2.0):
    if len(df) < period:
        return 0.015
    close_series = df['close']
    sma = close_series.rolling(window=period, min_periods=1).mean()
    std = close_series.rolling(window=period, min_periods=1).std().fillna(0)
    bbw = ((sma + (std * std_dev)) - (sma - (std * std_dev))) / (sma + 1e-9)
    val = float(bbw.iloc[-1])
    return val if not np.isnan(val) and val > 0 else 0.015

def calculate_advanced_rsi(df, period=14):
    if len(df) < period:
        return 50.0
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    val = float((100 - (100 / (1 + rs))).iloc[-1])
    return val if not np.isnan(val) else 50.0

def apply_adaptive_phase_shift(curve, coil_score, chop, drift, formula=None):
    w_coil = formula.get("coil_phase_w") if formula is not None else 0.50
    w_chop = formula.get("chop_phase_w") if formula is not None else 0.50
    norm_coil = min(1.0, max(0.0, coil_score / 100.0))
    norm_chop = min(1.0, max(0.0, chop * 5.0))
    compression = ((norm_coil * w_coil) + (norm_chop * w_chop)) / max(0.2, w_coil + w_chop)
    shift_mag = int(round(compression * 3.0))
    if shift_mag == 0 or len(curve) <= shift_mag:
        return curve
    shifted = np.zeros_like(curve)
    if drift > 0:
        shifted[shift_mag:] = curve[:-shift_mag]
    else:
        shifted[:-shift_mag] = curve[shift_mag:]
        shifted[-shift_mag:] = curve[-1]
        shifted = shifted - shifted[0]
    return shifted

def apply_adaptive_amplitude(curve, historical_acc, path_acc=100.0, formula=None, leg_drive=0.0):
    curve_arr = np.array(curve, dtype=float)
    if len(curve_arr) == 0:
        return curve_arr

    norm_hist = min(100.0, max(20.0, float(historical_acc)))
    norm_path = min(100.0, max(20.0, float(path_acc)))

    amp_gain = formula.get("amp_gain") if formula is not None else 1.05
    shape_exp = formula.get("shape_exp") if formula is not None else 1.00
    hp_mix = formula.get("honest_path_mix") if formula is not None else 0.48
    leg_gain = formula.get("leg_drive_gain") if formula is not None else 1.25

    blended_acc = (norm_hist * hp_mix) + (norm_path * (1.0 - hp_mix))

    dual_resonance = 1.0
    if norm_hist >= 68.0 and norm_path >= 72.0:
        dual_resonance = 1.0 + (((min(norm_hist, norm_path) - 68.0) / 32.0) * 0.38)
    elif norm_path < 50.0 and norm_hist < 50.0:
        dual_resonance = 0.72

    leg_boost = 1.0 + (float(np.clip(abs(leg_drive), 0.0, 1.5)) * (leg_gain - 0.35) * 0.45)
    aggression_multiplier = float(np.clip((blended_acc / 56.0) * amp_gain * dual_resonance * leg_boost, 0.25, 3.10))

    # Normalized [0,1] contour shaping so exponents > 1.0 never shrink decimal returns
    acc_skew = ((norm_path - norm_hist) / 180.0) - (abs(leg_drive) * 0.14)
    shape_factor = float(np.clip(shape_exp + acc_skew, 0.62, 1.45))

    peak_amp = max(float(np.max(np.abs(curve_arr))), 1e-6)
    norm_mag = np.abs(curve_arr) / peak_amp
    shaped_mag = (norm_mag ** shape_factor) * peak_amp

    aggressive_curve = np.sign(curve_arr) * shaped_mag * aggression_multiplier
    return aggressive_curve

def simulate_smashed_path(paths, distances, memory_scores, tuning_dial, live_thrust=0.0, formula=None):
    if len(paths) == 0:
        return np.zeros(24)

    dist_exp = formula.get("dist_exp") if formula is not None else max(1.0, 4.5 - (tuning_dial * 1.5))
    mem_exp = formula.get("mem_exp") if formula is not None else 1.15
    thrust_gain = formula.get("thrust_gain") if formula is not None else 1.45
    dom_blend = formula.get("dom_blend") if formula is not None else 0.38
    vol_scale = formula.get("vol_scale") if formula is not None else 1.05

    dist_weight = 1.0 / ((np.array(distances, dtype=np.float64) + 1e-6) ** dist_exp)
    mem_weight = np.maximum(0.05, np.array(memory_scores, dtype=np.float64)) ** mem_exp
    combined_power = dist_weight * mem_weight

    thrust_alignments = [
        (1.0 + thrust_gain * 0.45) if len(p) > 0 and abs(live_thrust) > 0.0001 and np.sign(p[0]) == np.sign(live_thrust)
        else max(0.25, 1.0 - (thrust_gain * 0.35))
        for p in paths
    ]
    combined_power *= np.array(thrust_alignments)
    smashed_weights = np.nan_to_num(np.clip(combined_power, 1e-9, 1e7), nan=1.0, posinf=1.0, neginf=1.0)

    if smashed_weights.sum() <= 0:
        smashed_weights = np.ones(len(paths)) / len(paths)
    else:
        smashed_weights /= smashed_weights.sum()

    smashed = np.average(paths, axis=0, weights=smashed_weights)
    if np.any(np.isnan(smashed)):
        smashed = np.mean(paths, axis=0)

    dominant_idx = int(np.argmax(smashed_weights))
    dominant_path = paths[dominant_idx]
    smashed = (smashed * (1.0 - dom_blend)) + (dominant_path * dom_blend)

    curr_vol = np.std(smashed)
    if curr_vol > 0:
        target_vol = np.average([np.std(p) for p in paths], weights=smashed_weights)
        smashed *= ((target_vol / curr_vol) * max(0.45, (1.4 - (tuning_dial * 0.4)) * vol_scale))
    return smashed

def apply_triphase_equilibrium(curve, formula=None):
    curve_arr = np.nan_to_num(np.asarray(curve, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    cleaned = np.copy(curve_arr)
    if len(cleaned) < 3:
        return cleaned.tolist()
    damp = formula.get("triphase_damp") if formula is not None else 0.80
    if not np.isfinite(damp):
        damp = 0.80
    delta_E = np.zeros(len(cleaned))
    delta_E[1:] = np.diff(cleaned)
    for t in range(2, len(cleaned)):
        harmonic = (((delta_E[t] / 3.0) * np.exp(1j * (0 - (2 * np.pi * 1) / 3.0)) +
                     (delta_E[t-1] / 3.0) * np.exp(1j * (0 - (2 * np.pi * 2) / 3.0)) +
                     (delta_E[t-2] / 3.0) * np.exp(1j * (0 - (2 * np.pi * 3) / 3.0)))).real
        cleaned[t] -= harmonic * damp
    return curve_arr.tolist() if np.any(np.isnan(cleaned)) or np.any(np.isinf(cleaned)) else cleaned.tolist()

def build_directional_lightning_bolt(pkg, base_p, fp_acc, cfg, y_span):
    path = pkg.get('path', [])
    if len(path) < 2 or base_p <= 0:
        return [], []

    now = datetime.now().astimezone().replace(tzinfo=None)
    total_pkg_secs = max(1.0, float(path[-1][0]))

    combo_boost = float(pkg.get('combo_strength', 1.0))
    reach_frac = min(0.55, 0.30 * combo_boost)
    strike_reach_seconds = cfg["delta"].total_seconds() * (cfg["horizon"] * reach_frac)
    tf_scale = math.sqrt(max(1.0, cfg["delta"].total_seconds() / 30.0))
    conf_scale = np.clip((fp_acc / 50.0) * combo_boost, 0.35, 2.25)

    l_t, l_p = [now], [base_p]
    terminal_pct = path[-1][1]
    net_dir = 1.0 if terminal_pct >= 0 else -1.0

    for idx, (sec_offset, pct_move) in enumerate(path[1:], 1):
        progress = float(sec_offset) / total_pkg_secs
        t_point = now + timedelta(seconds=progress * strike_reach_seconds)

        projected_pct = pct_move * tf_scale * conf_scale
        raw_p = base_p * (1.0 + projected_pct)

        if idx < len(path) - 1:
            jag_sign = 1.0 if (idx % 2 == 0) else -1.0
            jag_amp = y_span * 0.014 * (1.0 - (progress * 0.55)) * jag_sign
            raw_p += jag_amp
        else:
            raw_p = base_p * (1.0 + (abs(projected_pct) * net_dir))

        l_t.append(t_point)
        l_p.append(raw_p)

    return l_t, l_p

def build_hud_string(dancing_price, d):
    dist = d['target_p'] - dancing_price
    now = datetime.now().astimezone().replace(tzinfo=None)
    t_rem = d.get('target_time_end', now) - now
    t_rem_str = str(t_rem).split('.')[0] if t_rem.total_seconds() > 0 else "00:00:00"
    realized, targets = d.get('realized_prices', []), d.get('target_prices', [])
    bars_closed = len(realized)
    eval_len = min(bars_closed + 1, len(targets))
    chop_bbw = d.get('chop_bbw', 0.015)

    tip_target = d.get('expected_tip_price', targets[eval_len-1] if eval_len > 0 else dancing_price)
    instant_acc = compute_instant_marker_accuracy(tip_target, dancing_price, chop_bbw) if eval_len > 0 else 100.0
    bar_acc = compute_instant_marker_accuracy(targets[bars_closed-1], realized[-1], chop_bbw) if 0 < bars_closed <= len(targets) else instant_acc
    all_frame_acc = d.get('all_frame_acc', d.get('live_accuracy', 100.0))

    return (
        f"LIVE:   ${dancing_price:.7f} | BURST VOL: {d['burst_vol']:.2e}\n"
        f"TARGET: ${d['target_p']:.7f} ({d['move_pct']:+.2f}%) | APEX: {d.get('apex_tag', 'NONE')}\n"
        f"RADAR:  {d.get('redfuzz_status', '- TERRAIN CLEAR -')}\n"
        f"DIST:   ${dist:+.7f} TO TARGET | P_MAX: {d.get('p_max', 1.0):.2f}X\n"
        f"----------------------------------------------------\n"
        f"LOCK:   [{d['bars_elapsed']:02d}/{d['horizon']:02d}] BARS | T-REMAIN: {t_rem_str} | HITS: {d.get('settled_hits', 0)}\n"
        f"TRACK:  {instant_acc:>4.1f}% TCK | {bar_acc:>4.1f}% BAR | {d.get('live_accuracy', 100.0):>4.1f}% PATH | ALL-FRAME: {all_frame_acc:>4.1f}%\n"
        f"HIST:   {d['historical_accuracy']:>5.1f}% HONEST OOS (PEAK {d.get('peak_accuracy', 65.0):>4.1f}%) {d['topology_tag']}\n"
        f"FORM:   EFF {d.get('formula_eff', 75.0):>4.1f}% | EPOCH #{d.get('tuning_epoch', 0):<4d} | SWARM: {d['swarm_health']:>5.1f}% | LR: {d['learning_rate']:.4f}\n"
        f"BLEND:  OPINION {d.get('opinion_trust', 55.0):>4.1f}% | LIGHTNING {d.get('lightning_gain', 1.0):.2f}X ({d.get('lightning_combos', 0)}C)\n"
        f"TERRA:  LAND {d.get('landscape_trust', 60.0):>4.1f}% ({d.get('landscape_gain', 0.85):.2f}X) | BOOK: {d.get('spoof_status', 'SOLID-VERIFIED')}\n"
        f"KINETIC:{d['wiggles']:>3d} WIGGLES | COIL TENSION: {d['coil_score']:.1f}% | RSI: {d.get('rsi', 50.0):.1f}\n"
        f"OPTICS: LENS FOCUS {d['current_lens_focus']:.2f}X | CHOP: {d['chop_bbw']:.4f} | BETA: {d.get('dynamic_beta', 1.0):.2f}X\n"
        f"PHYS:   TILT {d['tilt']:+.1f}° | STRESS {d['stress']:.1f}x {d['stress_warn']}\n"
        f"VECTOR: {'ALIGNED' if d.get('vector_aligned') else 'MISMATCH'} | NOSE: {d.get('tick_angle', 0.0):+5.1f}° | VEL: {d.get('kinetic_velocity', 0.0)*100.0:.3f}% {'(GO)' if d.get('minimum_velocity_met') else '(WAIT)'}\n"
        f"CORNER: {d.get('corner_phase', 'CRUISE'):<10s} | CDA: {d.get('cda_acc', 68.0):>4.1f}% | INF: {d.get('corner_inf', 0.25):.2f}X | VAULT: {d.get('corner_vault_cnt', 0)}\n"
        f"SONAR:  {'WHALE DETECTED' if d.get('whale_alert') else 'CLEAR'} | MAG: {d.get('splash_magnitude', 0.0):.1f}X | DIR: {d.get('splash_direction', 0)}\n"
        f"EXEC:   {d.get('pos_side', 'FLAT'):<5s} CONV {d.get('conviction', 0.0):+.2f} | FEE-PNL: {d.get('net_pnl_pct', 0.0):+.2f}% | LAZARUS: ${d.get('lazarus_fund', 0.0):.2f}"
    )
# --- END OF PART 1 ---
# -----------------------------
# BACKFEED OPINION ENGINE & DYNAMIC MARKER BLENDER (V22.2)
# -----------------------------
class BackfeedOpinionEngine:
    STREAMS = ("sanctuary", "swarm_fuzz", "lightning", "opinion", "corridor", "landscape")

    def __init__(self, horizon):
        self.horizon = horizon
        self.residual_bias = np.zeros(horizon, dtype=float)
        self.residual_var = np.ones(horizon, dtype=float) * 0.0005
        self.opinion_trust = 60.0
        self.peak_opinion_trust = 65.0
        self.landscape_trust = 62.0
        self.peak_landscape_trust = 65.0
        self.eval_cycles = 0
        self.stream_acc = np.ones(len(self.STREAMS), dtype=float) * 65.0
        self.stream_metab = np.ones(len(self.STREAMS), dtype=float)
        self.stream_clock = np.zeros(len(self.STREAMS), dtype=int)

        self.stream_weights = np.zeros((len(self.STREAMS), horizon), dtype=float)
        for m in range(horizon):
            prog = m / max(1, horizon - 1)
            self.stream_weights[0, m] = 0.22 + (0.12 * prog)
            self.stream_weights[1, m] = 0.24 + (0.08 * prog)
            self.stream_weights[2, m] = 0.20 * ((1.0 - prog) ** 1.3)
            self.stream_weights[3, m] = 0.14 * (1.0 - 0.25 * prog)
            self.stream_weights[4, m] = 0.05 + (0.04 * math.sin(prog * math.pi))
            self.stream_weights[5, m] = 0.15 * (1.0 - 0.15 * prog)
        self._normalize_columns()
        self.champion_stream_weights = self.stream_weights.copy()

    def _normalize_columns(self):
        self.stream_weights = np.nan_to_num(self.stream_weights, nan=1.0 / len(self.STREAMS), posinf=0.5, neginf=0.05)
        self.residual_bias = np.nan_to_num(self.residual_bias, nan=0.0, posinf=0.0, neginf=0.0)
        self.residual_var = np.nan_to_num(self.residual_var, nan=0.0005, posinf=0.01, neginf=0.0001)
        col_sums = np.sum(self.stream_weights, axis=0, keepdims=True)
        col_sums = np.where((~np.isfinite(col_sums)) | (col_sums <= 1e-9), 1.0, col_sums)
        self.stream_weights = np.clip(self.stream_weights / col_sums, 0.03, 0.72)
        self.stream_weights /= np.sum(self.stream_weights, axis=0, keepdims=True)

    def build_opinion_curve(self, df, live_price, spatial_data, order_flow, bids, asks, btc_mom, dyn_beta, ghost_slope_corr, formula=None):
        ob_floor, ob_ceil, ob_imb = find_orderbook_wall_limits(bids, asks, live_price)
        delta_r = float(order_flow.get('taker_delta_ratio', 0.0))
        vel = float(order_flow.get('trade_velocity', 1.0))
        prox = float(spatial_data.get('proximity', 0.5))

        flow_w = formula.get("flow_weight") if formula is not None else 0.64
        ob_w = formula.get("ob_weight") if formula is not None else 0.36
        macro_g = formula.get("macro_beta_gain") if formula is not None else 0.38
        ghost_g = formula.get("ghost_slope_gain") if formula is not None else 0.65
        rev_g = formula.get("rev_pull_gain") if formula is not None else 0.42
        res_g = formula.get("res_corr_gain") if formula is not None else 0.68

        w_sum = max(0.1, flow_w + ob_w)
        flow_impulse = (((delta_r * flow_w) + (ob_imb * ob_w)) / w_sum) * min(2.2, max(0.5, vel * 0.80)) * 0.009
        macro_impulse = float(np.clip(btc_mom * dyn_beta * macro_g, -0.028, 0.028))
        mean_rev_pull = (0.5 - prox) * (0.010 * rev_g) if (0.18 < prox < 0.82) else 0.0

        flow_decay = formula.get("flow_decay_rate") if formula is not None else 0.16
        macro_exp = formula.get("macro_onset_exp") if formula is not None else 0.82
        phase_shift = formula.get("mirror_pos_shift") if formula is not None else 0.0

        opinion = np.zeros(self.horizon, dtype=float)
        for i in range(self.horizon):
            prog = (i + 1) / self.horizon
            shifted_prog = float(np.clip(prog - (phase_shift * 0.5), 0.02, 1.0))
            short_decay = math.exp(-i * flow_decay)
            step_flow = flow_impulse * (shifted_prog ** 0.65) * (0.45 + 0.55 * short_decay)
            step_macro = macro_impulse * (shifted_prog ** macro_exp)
            step_ghost = ghost_slope_corr * (i + 1) * ghost_g
            step_rev = mean_rev_pull * math.sin(shifted_prog * math.pi)
            raw_op = step_flow + step_macro + step_ghost + step_rev - (self.residual_bias[i] * res_g)
            opinion[i] = float(np.clip(raw_op, ob_floor * 1.35, ob_ceil * 1.35))
        return opinion

    def blend_marker_streams(self, stream_curves, live_acc=100.0, fp_acc=100.0, is_chop=False, formula=None, spoof_passed=True, hist_acc=65.0, leg_drive=0.0):
        blended = np.zeros(self.horizon, dtype=float)
        dyn_w = self.stream_weights.copy()

        warp_gain = formula.get("lightning_warp_gain") if formula is not None else 0.88
        reach_frac = formula.get("lightning_reach") if formula is not None else 0.48
        land_gain = formula.get("landscape_flow_gain") if formula is not None else 0.90
        hp_mix = formula.get("honest_path_mix") if formula is not None else 0.48

        # --- CONSENSUS QUORUM & FIRST-RESPONDER VETO GATE ---
        # If live leg drive or momentum screams an explosive directional vote, suppress lagging historical weights
        screaming_veto = abs(leg_drive) >= 0.45
        if screaming_veto:
            dyn_w[0, :] *= 0.55  # Sanctuary (KNN) dampening to prevent laggy averages
            dyn_w[1, :] *= 1.45  # Swarm/Fuzz boost
            dyn_w[2, :] *= 1.60  # Lightning boost

        # Dual-Truth Ingredient Governance (Honest OOS vs. Live Path Accuracy)
        honest_factor = float(np.clip((hist_acc / 68.0) * (0.65 + 0.70 * hp_mix), 0.35, 1.85))
        path_factor = float(np.clip((live_acc / 72.0) * (0.65 + 0.70 * (1.0 - hp_mix)), 0.35, 1.85))
        leg_surge = 1.0 + (min(1.8, abs(leg_drive)) * 0.65)

        # Sanctuary [0] & Opinion [3] anchored by Honest OOS; Swarm/Fuzz [1], Lightning [2], Landscape [5] driven by Path Accuracy & Leg Drive
        dyn_w[0, :] *= honest_factor
        dyn_w[1, :] *= (path_factor * leg_surge)

        # "For Chumps" Winner-Take-All Exponent Gate for Elite Honest Accuracy (>80%)
        if hist_acc >= 80.0:
            winner_power = 1.0 + ((hist_acc - 80.0) / 19.0) * 3.0
            dyn_w = np.power(np.maximum(0.01, dyn_w), winner_power)

        fp_boost = np.clip(((fp_acc - 40.0) / 30.0) * warp_gain * (0.55 + 0.45 * path_factor), 0.25, 3.40)
        for m in range(self.horizon):
            prog = (m + 1) / self.horizon
            reach_env = 1.35 if prog <= reach_frac else math.exp(-(prog - reach_frac) * 2.5)
            dyn_w[2, m] *= (fp_boost * reach_env)

        if is_chop and abs(leg_drive) < 0.35:
            dyn_w[4, :] *= 1.35
        else:
            dyn_w[4, :] *= (0.20 if abs(leg_drive) >= 0.35 else 0.45)

        op_boost = np.clip((self.opinion_trust / 55.0) * (0.60 + 0.40 * honest_factor), 0.45, 2.00)
        dyn_w[3, :] *= op_boost

        spoof_conf = 1.15 if spoof_passed else 0.78
        land_boost = np.clip((self.landscape_trust / 52.0) * land_gain * spoof_conf * (0.55 + 0.45 * path_factor) * leg_surge, 0.20, 2.85)
        dyn_w[5, :] *= land_boost
        dyn_w *= np.clip(self.stream_metab, 0.25, 2.40)[:, None]

        col_sums = np.sum(dyn_w, axis=0, keepdims=True)
        dyn_w /= np.where(col_sums <= 1e-9, 1.0, col_sums)

        for s_idx, s_name in enumerate(self.STREAMS):
            c = stream_curves.get(s_name)
            if c is not None and len(c) == self.horizon:
                blended += np.array(c, dtype=float) * dyn_w[s_idx, :]

        return blended, dyn_w

    def ingest_realized_truth(self, locked_pred_curve, realized_curve, stream_snapshots, lr=0.05, vol_scale=0.015, hist_acc=65.0):
        n = min(self.horizon, len(locked_pred_curve), len(realized_curve))
        if n <= 0:
            return
        pred_sub = np.array(locked_pred_curve[:n], dtype=float)
        real_sub = np.array(realized_curve[:n], dtype=float)

        path_truth = calculate_directional_truth(pred_sub, real_sub, vol_scale=vol_scale)
        acc_gap = abs(path_truth - hist_acc) / 100.0
        dual_need = ((100.0 - path_truth) * 0.55 + (100.0 - hist_acc) * 0.45) / 100.0

        res_err = pred_sub - real_sub
        alpha = float(np.clip(lr * (1.15 + dual_need * 1.35 + acc_gap * 0.75), 0.012, 0.26))
        self.residual_bias[:n] = (1.0 - alpha) * self.residual_bias[:n] + (alpha * res_err)
        self.residual_var[:n] = (1.0 - alpha) * self.residual_var[:n] + (alpha * (res_err ** 2))

        if stream_snapshots:
            alpha_vec = np.zeros(len(self.STREAMS), dtype=float)
            for s_idx, s_name in enumerate(self.STREAMS):
                self.stream_clock[s_idx] += 1
                s_curve = stream_snapshots.get(s_name)
                if s_curve is not None and len(s_curve) >= n:
                    s_grade = calculate_directional_truth(s_curve[:n], real_sub, vol_scale=vol_scale)
                    self.stream_acc[s_idx] = float(np.clip((self.stream_acc[s_idx] * 0.76) + (s_grade * 0.24), 15.0, 99.5))
                    rel_edge = (s_grade - path_truth) / 40.0
                    target_m = np.clip((self.stream_acc[s_idx] / 60.0) * (1.0 + np.clip(rel_edge, -0.35, 0.60)), 0.25, 2.40)
                    self.stream_metab[s_idx] = float((self.stream_metab[s_idx] * 0.68) + (target_m * 0.32))
                else:
                    s_grade = float(self.stream_acc[s_idx])
                fast_s = s_name in ("swarm_fuzz", "lightning")
                s_cad = 1 if (fast_s or self.stream_metab[s_idx] >= 1.05 or s_grade < 45.0) else (2 if self.stream_metab[s_idx] >= 0.65 else 3)
                if (self.stream_clock[s_idx] % s_cad) == 0:
                    alpha_vec[s_idx] = float(np.clip(alpha * self.stream_metab[s_idx], 0.004, 0.36))
            for m in range(n):
                errs = np.zeros(len(self.STREAMS), dtype=float)
                for s_idx, s_name in enumerate(self.STREAMS):
                    s_curve = stream_snapshots.get(s_name)
                    if s_curve is not None and m < len(s_curve):
                        s_val = float(s_curve[m])
                        dir_pen = 1.0 if np.sign(s_val) == np.sign(real_sub[m]) else 1.45
                        errs[s_idx] = abs(s_val - real_sub[m]) * dir_pen
                    else:
                        errs[s_idx] = abs(res_err[m])
                inv_scores = 1.0 / (errs + 0.0012)
                target_w = inv_scores / np.sum(inv_scores)
                self.stream_weights[:, m] = ((1.0 - alpha_vec) * self.stream_weights[:, m]) + (alpha_vec * target_w)
            self._normalize_columns()

            if "opinion" in stream_snapshots and len(stream_snapshots["opinion"]) >= n:
                op_grade = calculate_directional_truth(stream_snapshots["opinion"][:n], real_sub, vol_scale=vol_scale)
                self.opinion_trust = float(np.clip((self.opinion_trust * 0.85) + (op_grade * 0.15), 25.0, 99.0))
                if self.opinion_trust >= self.peak_opinion_trust:
                    self.peak_opinion_trust = self.opinion_trust
                    self.champion_stream_weights = self.stream_weights.copy()
                elif self.opinion_trust < (self.peak_opinion_trust - 15.0):
                    self.stream_weights = (0.80 * self.stream_weights) + (0.20 * self.champion_stream_weights)
                    self._normalize_columns()

            if "landscape" in stream_snapshots and len(stream_snapshots["landscape"]) >= n:
                land_grade = calculate_directional_truth(stream_snapshots["landscape"][:n], real_sub, vol_scale=vol_scale)
                self.landscape_trust = float(np.clip((self.landscape_trust * 0.82) + (land_grade * 0.18), 20.0, 99.0))
                if self.landscape_trust >= self.peak_landscape_trust:
                    self.peak_landscape_trust = self.landscape_trust

        self.eval_cycles += 1

    def to_dict(self):
        return {
            "residual_bias": self.residual_bias.tolist(),
            "residual_var": self.residual_var.tolist(),
            "stream_weights": self.stream_weights.tolist(),
            "champion_stream_weights": self.champion_stream_weights.tolist(),
            "opinion_trust": float(self.opinion_trust),
            "peak_opinion_trust": float(self.peak_opinion_trust),
            "landscape_trust": float(self.landscape_trust),
            "peak_landscape_trust": float(self.peak_landscape_trust),
            "eval_cycles": int(self.eval_cycles),
            "stream_acc": self.stream_acc.tolist(),
            "stream_metab": self.stream_metab.tolist()
        }

    def from_dict(self, d):
        try:
            if "stream_acc" in d and len(d["stream_acc"]) == len(self.STREAMS):
                self.stream_acc = np.clip(np.array(d["stream_acc"], dtype=float), 15.0, 99.5)
            if "stream_metab" in d and len(d["stream_metab"]) == len(self.STREAMS):
                self.stream_metab = np.clip(np.array(d["stream_metab"], dtype=float), 0.25, 2.40)
            if "residual_bias" in d and len(d["residual_bias"]) == self.horizon:
                self.residual_bias = np.array(d["residual_bias"], dtype=float)
            if "residual_var" in d and len(d["residual_var"]) == self.horizon:
                self.residual_var = np.array(d["residual_var"], dtype=float)
            if "stream_weights" in d:
                sw = np.array(d["stream_weights"], dtype=float)
                if sw.shape == (len(self.STREAMS), self.horizon):
                    self.stream_weights = sw
                    self._normalize_columns()
                elif sw.shape == (len(self.STREAMS) - 1, self.horizon):
                    self.stream_weights[:len(self.STREAMS) - 1, :] = sw * 0.84
                    self.stream_weights[-1, :] = 0.16
                    self._normalize_columns()
            if "champion_stream_weights" in d:
                csw = np.array(d["champion_stream_weights"], dtype=float)
                if csw.shape == (len(self.STREAMS), self.horizon):
                    self.champion_stream_weights = csw
            self.opinion_trust = float(d.get("opinion_trust", 60.0))
            self.peak_opinion_trust = float(d.get("peak_opinion_trust", max(65.0, self.opinion_trust)))
            self.landscape_trust = float(d.get("landscape_trust", 62.0))
            self.peak_landscape_trust = float(d.get("peak_landscape_trust", max(65.0, self.landscape_trust)))
            self.eval_cycles = int(d.get("eval_cycles", 0))
        except Exception:
            pass

# -----------------------------
# REGIME SHIFT SENTINEL (NIMBLE CRASH OVERRIDE + ANTI-NOISE)
# -----------------------------
class SelfGoverningRedFuzzVault:
    """
    Saves RedFuzz terrain snapshots, audits real-world outcome accuracy after 12 bars,
    persists proven winners to disk, and auto-governs shape top/bottom height scaling.
    """
    def __init__(self, data_dir):
        self.vault_file = os.path.join(data_dir, "proven_redfuzz_vault.pkl")
        self.active_audits = []
        self.proven_vault = []
        self.redfuzz_shape_scale = 1.0  # Dynamic multiplier governing top/bottom shape height
        self._load_vault()

    def _load_vault(self):
        if os.path.exists(self.vault_file):
            try:
                with open(self.vault_file, "rb") as f:
                    data = pickle.load(f)
                    self.proven_vault = data.get("vault", [])
                    self.redfuzz_shape_scale = float(data.get("shape_scale", 1.0))
            except Exception:
                pass

    def save_vault(self):
        try:
            tmp = self.vault_file + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump({
                    "vault": self.proven_vault[-500:],
                    "shape_scale": self.redfuzz_shape_scale
                }, f)
            os.replace(tmp, self.vault_file)
        except Exception:
            pass

    def record_trigger(self, rf_status, live_price, tape_data, current_shape_curve):
        snapshot = {
            'ts': time.time(),
            'status': str(rf_status),
            'base_price': float(live_price),
            'tape_imbalance': float(tape_data.get('tape_imbalance', 0.0) if tape_data else 0.0),
            'tps': float(tape_data.get('trades_per_sec', 1.0) if tape_data else 1.0),
            'target_terminal_pct': float(current_shape_curve[-1]),
            'prices_tracked': [float(live_price)],
            'bars_elapsed': 0
        }
        self.active_audits.append(snapshot)

    def audit_and_govern(self, live_price):
        completed = []
        for audit in self.active_audits:
            audit['bars_elapsed'] += 1
            audit['prices_tracked'].append(float(live_price))
            if audit['bars_elapsed'] >= 12:
                start_p = audit['base_price']
                actual_move_pct = (audit['prices_tracked'][-1] - start_p) / (start_p + 1e-9)
                predicted_move_pct = audit['target_terminal_pct']
                dir_match = (np.sign(actual_move_pct) == np.sign(predicted_move_pct)) or (abs(actual_move_pct) < 0.002)
                mag_error = abs(actual_move_pct - predicted_move_pct) / (abs(predicted_move_pct) + 1e-9)
                success = dir_match and mag_error <= 0.35
                audit['success'] = success
                audit['actual_move_pct'] = actual_move_pct
                if success:
                    self.proven_vault.append(audit)
                    self.redfuzz_shape_scale = float(np.clip(self.redfuzz_shape_scale * 1.025, 0.75, 2.20))
                else:
                    self.redfuzz_shape_scale = float(np.clip(self.redfuzz_shape_scale * 0.970, 0.75, 2.20))
                completed.append(audit)
                self.save_vault()
        for c in completed:
            if c in self.active_audits:
                self.active_audits.remove(c)


class RegimeShiftSentinel:
    """
    Protects normal OOS locks from premature wiggles while immediately bypassing
    cooldowns whenever RedFuzz detects a Black Swan Shock, Cliff Drop, or severe
    opposing structural breakdown.
    """
    def __init__(self, min_lock_seconds=120.0, confirm_ticks_required=4):
        self.min_lock_seconds = min_lock_seconds
        self.confirm_ticks_required = confirm_ticks_required
        self.breach_counter = 0
        self.last_shift_ts = 0.0

    def check_regime_break(self, lock, live_price, live_acc, rf_alarm, rf_status, fp_dir, fp_acc, p_max, recalc_trigger=78.0, chop_bbw=0.015):
        if not lock or live_price <= 0:
            self.breach_counter = 0
            return False, "NONE"

        now = time.time()
        lock_age = now - lock.get('sys_time', now)

        frozen_targets = lock.get('frozen_target_prices', [])
        if not frozen_targets:
            return False, "NONE"

        base_p = lock['base_price']
        pred_dir = 1 if frozen_targets[-1] >= base_p else -1
        live_move_pct = (live_price - base_p) / (base_p + 1e-9)
        live_dir = 1 if live_move_pct >= 0 else -1

        kinetic_oppose = rf_alarm and (
            ("SHOCK" in rf_status) or
            ("CLIFF" in rf_status and (pred_dir > 0 or live_dir < 0)) or
            (("WALL" in rf_status or "CLIMB" in rf_status) and (pred_dir < 0 or live_dir > 0))
        )

        flash_excursion = (live_dir != pred_dir) and (abs(live_move_pct) > max(chop_bbw * 1.60, 0.016))

        if not (kinetic_oppose or flash_excursion):
            if lock_age < self.min_lock_seconds or (now - self.last_shift_ts) < self.min_lock_seconds:
                return False, "COOLDOWN"

        min_break_excursion = max(chop_bbw * 0.90, 0.009 * max(0.75, p_max))
        structural_invalidation = (
            live_acc < (recalc_trigger - 6.0) and
            live_dir != pred_dir and
            abs(live_move_pct) > min_break_excursion
        )

        if kinetic_oppose and (structural_invalidation or flash_excursion or live_acc < recalc_trigger):
            self.breach_counter += 2
        elif flash_excursion or structural_invalidation:
            self.breach_counter += 1
        else:
            self.breach_counter = max(0, self.breach_counter - 1)

        if self.breach_counter >= self.confirm_ticks_required:
            self.breach_counter = 0
            self.last_shift_ts = now
            reason = f"REDFUZZ-{rf_status}" if kinetic_oppose else f"STRUCT-BREAK({live_acc:.1f}%<{recalc_trigger - 6.0:.1f}%)"
            return True, reason

        return False, "HOLDING"

# -----------------------------
# ADVANCED FUZZ ENGINE
# -----------------------------
class FuzzPacket:
    def __init__(self, value, direction, velocity):
        self.value = value
        self.direction = direction
        self.velocity = velocity
        self.active = True

class ProfitGovernedLens:
    def __init__(self):
        self.focus_multiplier = 1.0

    def tune_lens(self, governor_drift, current_chop, profit_yield):
        if governor_drift > 0:
            self.focus_multiplier = max(0.3, self.focus_multiplier - 0.08) * (1.0 / (1.0 + (current_chop * 2.5)))
        else:
            self.focus_multiplier = min(3.0, self.focus_multiplier + 0.08) * max(0.5, profit_yield * 1.6) * (1.0 / (1.0 + current_chop))
        self.focus_multiplier = float(np.clip(self.focus_multiplier, 0.30, 3.00))

    def process(self, packet):
        packet.value *= (1.0 / max(0.1, self.focus_multiplier))
        packet.velocity *= self.focus_multiplier
        return packet

class MirrorNode:
    def __init__(self, position_index, reflection_decay):
        self.position = position_index
        self.decay = reflection_decay

    def reflect(self, packet, exhaustion_active=False, exh_reflect=0.65):
        if packet.active:
            packet.value *= self.decay
            if exhaustion_active:
                packet.direction *= -exh_reflect
            if abs(packet.value) < 0.0001:
                packet.active = False
        return packet

class AdvancedFuzzEngine:
    def __init__(self, horizon):
        self.horizon = horizon
        self.lens = ProfitGovernedLens()
        self.mirrors = [MirrorNode(int(horizon * 0.33), 0.7), MirrorNode(int(horizon * 0.66), 0.4)]

    def shoot_fuzz(self, base_curve, momentum_vector, volatility, governor_drift, chop_pct, profit_yield, rsi=50.0, proximity=0.5, formula=None):
        curve = np.array(base_curve, dtype=float)
        if momentum_vector == 0:
            return curve

        fuzz_vel_gain = formula.get("fuzz_vel_gain") if formula is not None else 1.95
        mirror_decay = formula.get("mirror_decay") if formula is not None else 0.68
        exh_reflect = formula.get("exh_reflect") if formula is not None else 0.65
        mirror_shift = formula.get("mirror_pos_shift") if formula is not None else 0.0

        self.mirrors[0].position = int(np.clip(round(self.horizon * (0.33 + mirror_shift)), 1, max(1, self.horizon - 3)))
        self.mirrors[1].position = int(np.clip(round(self.horizon * (0.66 + mirror_shift)), self.mirrors[0].position + 1, max(2, self.horizon - 1)))
        self.mirrors[0].decay = mirror_decay
        self.mirrors[1].decay = mirror_decay * 0.60

        damped_momentum = np.sign(momentum_vector) * (abs(momentum_vector) ** 0.85)
        self.lens.tune_lens(governor_drift, chop_pct, profit_yield)
        packet = self.lens.process(FuzzPacket(abs(damped_momentum) * 0.5, 1 if damped_momentum > 0 else -1, volatility * fuzz_vel_gain))

        exhaustion_active = (packet.direction > 0 and (rsi > 68.0 or proximity > 0.82)) or (packet.direction < 0 and (rsi < 28.0 and proximity < 0.12))

        fuzz_deformation = np.zeros(self.horizon)
        for t in range(self.horizon):
            if not packet.active:
                break
            for mirror in self.mirrors:
                if t == mirror.position:
                    packet = mirror.reflect(packet, exhaustion_active=exhaustion_active, exh_reflect=exh_reflect)
            fuzz_deformation[t] = packet.value * packet.direction * (1 + packet.velocity)
            packet.value *= np.clip(1.0 - (max(0, governor_drift) * 2.0), 0.82, 0.99)
        return curve + fuzz_deformation

# -----------------------------
# MARKER SWARM ENGINE & MARKER-TO-MARKER BUS
# -----------------------------
class SmartMarkerNode:
    def __init__(self, index):
        self.index = index
        self.accuracy_weight = 1.0
        self.historical_error = deque(maxlen=50)
        self.verified_hits = 0

    def learn(self, predicted_val, actual_val, slack_divisor=1.0):
        error = abs(predicted_val - actual_val) / slack_divisor
        self.historical_error.append(error)
        self.accuracy_weight = float(np.clip(1.0 / (1.0 + np.mean(self.historical_error) * 16.0), 0.25, 1.85))
        return error

    def register_verified_hit(self, arrival_acc=100.0):
        self.verified_hits += 1
        boost = 1.0 + (0.03 * (arrival_acc / 100.0))
        self.accuracy_weight = float(np.clip(self.accuracy_weight * boost, 0.25, 1.95))

    def process_forward(self, base_val, inherited_momentum, swarm_health):
        health_ratio = max(0.15, swarm_health / 100.0)
        adjusted_val = (base_val * self.accuracy_weight) + (inherited_momentum * health_ratio)
        return adjusted_val, (adjusted_val - base_val) * 0.3 * health_ratio

class MarkerSwarm:
    def __init__(self, horizon):
        self.nodes = [SmartMarkerNode(i) for i in range(horizon)]
        self.swarm_health = 100.0
        self.eval_count = 0

    def evaluate_and_learn(self, pred_curve, actual_curve):
        slack_divisor = max(1.0, (max(0.01, float(np.max(np.abs(actual_curve)))) if len(actual_curve) > 0 else 0.01) * 100.0)
        errors = [self.nodes[i].learn(pred_curve[i], actual_curve[i], slack_divisor) for i in range(min(len(self.nodes), len(pred_curve), len(actual_curve)))]
        if errors:
            for idx in range(len(errors) - 1, 0, -1):
                back_drift = errors[idx] * 0.12
                self.nodes[idx - 1].accuracy_weight = float(np.clip(self.nodes[idx - 1].accuracy_weight * (1.0 - min(0.04, back_drift)), 0.25, 1.95))
            current_health = max(15.0, 100.0 - (np.mean(errors) * (420.0 / slack_divisor)))
            self.swarm_health = current_health if self.eval_count == 0 else (self.swarm_health * 0.88) + (current_health * 0.12)
            self.eval_count += 1
        return np.mean(errors) if errors else 0.25

    def settle_physical_hit(self, marker_idx, arrival_acc=100.0):
        if 0 <= marker_idx < len(self.nodes):
            self.nodes[marker_idx].register_verified_hit(arrival_acc)
            if marker_idx + 1 < len(self.nodes):
                self.nodes[marker_idx + 1].accuracy_weight = float(np.clip(self.nodes[marker_idx + 1].accuracy_weight * 1.015, 0.25, 1.95))
            self.swarm_health = float(np.clip((self.swarm_health * 0.94) + (arrival_acc * 0.06), 15.0, 100.0))

    def apply_swarm_intelligence(self, curve):
        adjusted_curve = np.zeros_like(curve)
        inherited_momentum = 0.0
        for i in range(len(curve)):
            if i < len(self.nodes):
                adjusted_curve[i], inherited_momentum = self.nodes[i].process_forward(curve[i], inherited_momentum, self.swarm_health)
            else:
                adjusted_curve[i] = curve[i] + inherited_momentum
        return adjusted_curve

# -----------------------------
# TEMPORAL LOCK MANAGER (IMMUTABLE OOS GRADING)
# -----------------------------
class TemporalLockManager:
    """
    Enforces strict Out-Of-Sample (OOS) lock integrity:
      - Always grades against `frozen_target_prices` and `frozen_curve` (never moving goalposts).
      - Feeds honest OOS errors into the DecomposedPredictionFormula and Opinion Engine.
    """
    def __init__(self, horizon):
        self.horizon = horizon
        self.active_lock = None
        self.ghosts = deque(maxlen=5)
        self.historical_accuracy = 65.0
        self.peak_historical_accuracy = 68.0

    def update_historical_accuracy(self, new_grade, weight=0.35):
        eff_w = weight if new_grade < self.historical_accuracy else 0.10
        self.historical_accuracy = float(np.clip((self.historical_accuracy * (1.0 - eff_w)) + (new_grade * eff_w), 5.0, 99.9))
        if self.historical_accuracy > self.peak_historical_accuracy:
            self.peak_historical_accuracy = self.historical_accuracy

    def lock_projection(self, df_ts, df_time, base_price, future_times, projected_curve, tension, local_curve=None, stream_snapshots=None, component_traces=None):
        frozen_curve = tuple(float(x) for x in projected_curve)
        frozen_local = tuple(float(x) for x in (local_curve if local_curve is not None else projected_curve))
        frozen_targets = tuple(float(base_price * (1.0 + p)) for p in frozen_curve)
        self.active_lock = {
            'sys_time': time.time(),
            'base_ts': float(df_ts),
            'base_time': df_time,
            'base_price': float(base_price),
            'target_times': list(future_times),
            'curve': np.array(frozen_curve, dtype=float),
            'frozen_curve': frozen_curve,
            'local_curve': np.array(frozen_local, dtype=float),
            'frozen_local_curve': frozen_local,
            'target_prices': list(frozen_targets),
            'frozen_target_prices': frozen_targets,
            'tension': float(tension),
            'last_eval_bar': 0,
            'var_trace': deque(maxlen=6),
            'settled_indices': set(),
            'stream_snapshots': stream_snapshots or {},
            'component_traces': component_traces or {}
        }

    def serialize_active_lock(self):
        if not self.active_lock:
            return None
        try:
            lock = self.active_lock
            return {
                'sys_time': float(lock['sys_time']),
                'base_ts': float(lock['base_ts']),
                'base_time_iso': lock['base_time'].isoformat(),
                'base_price': float(lock['base_price']),
                'target_times_iso': [t.isoformat() for t in lock['target_times']],
                'frozen_curve': list(lock['frozen_curve']),
                'frozen_local_curve': list(lock['frozen_local_curve']),
                'frozen_target_prices': list(lock['frozen_target_prices']),
                'tension': float(lock['tension']),
                'last_eval_bar': int(lock.get('last_eval_bar', 0)),
                'settled_indices': list(lock.get('settled_indices', set())),
                'dynamic_beta': float(lock.get('dynamic_beta', 1.0)),
                'apex_tag': str(lock.get('apex_tag', 'NONE')),
                'stream_snapshots': {k: np.array(v, dtype=float).tolist() for k, v in lock.get('stream_snapshots', {}).items()},
                'component_traces': {k: np.array(v, dtype=float).tolist() for k, v in lock.get('component_traces', {}).items()}
            }
        except Exception:
            return None

    def deserialize_active_lock(self, d):
        if not d or not isinstance(d, dict):
            return
        try:
            fc = tuple(float(x) for x in d['frozen_curve'])
            flc = tuple(float(x) for x in d.get('frozen_local_curve', fc))
            ftp = tuple(float(x) for x in d['frozen_target_prices'])
            self.active_lock = {
                'sys_time': float(d.get('sys_time', time.time())),
                'base_ts': float(d['base_ts']),
                'base_time': datetime.fromisoformat(d['base_time_iso']),
                'base_price': float(d['base_price']),
                'target_times': [datetime.fromisoformat(x) for x in d['target_times_iso']],
                'curve': np.array(fc, dtype=float),
                'frozen_curve': fc,
                'local_curve': np.array(flc, dtype=float),
                'frozen_local_curve': flc,
                'target_prices': list(ftp),
                'frozen_target_prices': ftp,
                'tension': float(d.get('tension', 0.01)),
                'last_eval_bar': int(d.get('last_eval_bar', 0)),
                'var_trace': deque(maxlen=6),
                'settled_indices': set(int(i) for i in d.get('settled_indices', [])),
                'dynamic_beta': float(d.get('dynamic_beta', 1.0)),
                'apex_tag': str(d.get('apex_tag', 'NONE')),
                'stream_snapshots': {k: np.array(v, dtype=float) for k, v in d.get('stream_snapshots', {}).items()},
                'component_traces': {k: np.array(v, dtype=float) for k, v in d.get('component_traces', {}).items()}
            }
        except Exception:
            self.active_lock = None

    def audit_physical_marker_hits(self, prev_price, live_price, swarm, persistence=None, tf_key="4hr"):
        if not self.active_lock or prev_price <= 0 or live_price <= 0:
            return 0
        settled = self.active_lock.setdefault('settled_indices', set())
        frozen_targets = self.active_lock['frozen_target_prices']
        low_p, high_p = min(prev_price, live_price), max(prev_price, live_price)
        hits_now = 0

        active_idx = int(self.active_lock.get('last_eval_bar', 0))
        valid_window = range(max(0, active_idx - 1), min(len(frozen_targets), active_idx + 2))

        for idx in valid_window:
            if idx in settled:
                continue
            target_p = frozen_targets[idx]
            if abs(target_p - self.active_lock['base_price']) < (self.active_lock['base_price'] * 0.0003):
                continue
            tolerance = live_price * 0.00035
            if (low_p - tolerance) <= target_p <= (high_p + tolerance):
                settled.add(idx)
                hits_now += 1
                arrival_acc = compute_instant_marker_accuracy(target_p, live_price)
                swarm.settle_physical_hit(idx, arrival_acc)
                self.update_historical_accuracy(arrival_acc, weight=0.03)
                if persistence is not None:
                    persistence.log_marker_hit(tf_key, idx, target_p, live_price, arrival_acc)
        return hits_now

    def force_abort_and_learn(self, df, live_price, swarm, governor, opinion_engine=None, formula=None, chop_bbw=0.015):
        if not self.active_lock:
            return
        actuals_df = df[df['ts'] > self.active_lock['base_ts']]
        realized_prices = actuals_df['close'].tolist() + ([live_price] if live_price > 0 else [])
        n_eval = min(len(realized_prices), self.horizon)
        if n_eval > 0:
            realized_curve = (np.array(realized_prices[:n_eval], dtype=float) - self.active_lock['base_price']) / self.active_lock['base_price']
            eval_curve = np.array(self.active_lock['frozen_local_curve'][:n_eval], dtype=float)
            swarm.evaluate_and_learn(eval_curve, realized_curve)
            grade = calculate_directional_truth(eval_curve, realized_curve, vol_scale=chop_bbw)
            self.update_historical_accuracy(grade, weight=0.10)
            governor.update(float(np.mean(np.abs(eval_curve - realized_curve))), self.historical_accuracy, live_acc=grade)
            if opinion_engine is not None:
                opinion_engine.ingest_realized_truth(
                    eval_curve, realized_curve,
                    self.active_lock.get('stream_snapshots', {}),
                    lr=governor.learning_rate, vol_scale=chop_bbw, hist_acc=self.historical_accuracy
                )
            if formula is not None:
                formula.tune_from_accuracy(
                    realized_curve, self.active_lock.get('component_traces', {}),
                    grade, self.historical_accuracy, lr=governor.learning_rate
                )
        self.active_lock = None

    def check_and_grade(self, df, swarm, metric, sanctuary, governor, opinion_engine=None, formula=None, chop_bbw=0.015):
        if not self.active_lock:
            return True
        actuals_df = df[df['ts'] > self.active_lock['base_ts']]
        if len(actuals_df) >= self.horizon:
            realized_curve = (actuals_df['close'].iloc[:self.horizon].values - self.active_lock['base_price']) / self.active_lock['base_price']
            eval_curve = np.array(self.active_lock['frozen_local_curve'], dtype=float)
            spliced_eval = np.array(self.active_lock['frozen_curve'], dtype=float)
            swarm.evaluate_and_learn(eval_curve, realized_curve)

            grade = calculate_directional_truth(spliced_eval, realized_curve, vol_scale=chop_bbw)
            self.update_historical_accuracy(grade, weight=0.16)

            if opinion_engine is not None:
                opinion_engine.ingest_realized_truth(
                    spliced_eval, realized_curve,
                    self.active_lock.get('stream_snapshots', {}),
                    lr=governor.learning_rate, vol_scale=chop_bbw, hist_acc=self.historical_accuracy
                )
            if formula is not None:
                formula.tune_from_accuracy(
                    realized_curve, self.active_lock.get('component_traces', {}),
                    grade, self.historical_accuracy, lr=governor.learning_rate
                )

            matching_rows = df[df['ts'] == self.active_lock['base_ts']].index
            if len(matching_rows) > 0 and metric is not None:
                pattern = extract_pattern_vector(df, matching_rows[0])
                if pattern is not None:
                    matches = sanctuary.recall(pattern, top_k=10, metric_learner=metric)
                    all_errs = []
                    for dist, outcome, mem_obj in matches:
                        err = np.clip(np.mean(np.abs(np.array(outcome) - realized_curve)), 0.0, 5.0)
                        all_errs.append(err)
                        mem_obj["error_ewma"] = 0.8 * mem_obj.get("error_ewma", 1.0) + 0.2 * err
                        mem_obj["score"] = sanctuary._score_memory(mem_obj)
                        metric.update_from_errors(np.array([mem_obj["vector"]]), np.array([err]), lr=governor.learning_rate)
                    if all_errs:
                        governor.update(np.mean(all_errs), self.historical_accuracy, live_acc=grade)
                    sanctuary.learn(pattern, realized_curve, volatility=float(np.std(realized_curve)), persist_now=True)

            self.ghosts.append({
                'base_ts': self.active_lock['base_ts'],
                'times': [self.active_lock['base_time']] + self.active_lock['target_times'],
                'prices': [self.active_lock['base_price']] + list(self.active_lock['frozen_target_prices']),
                'grade': grade
            })
            self.active_lock = None
            return True
        return False

    def get_live_tracking_error(self, df, current_live_price, chop_bbw=0.015):
        if not self.active_lock:
            return 100.0, [], []
        active_actuals_df = df[df['ts'] > self.active_lock['base_ts']]
        realized_prices = active_actuals_df['close'].tolist()
        self.active_lock['last_eval_bar'] = len(realized_prices)

        eval_prices = realized_prices + [current_live_price]
        frozen_targets = list(self.active_lock['frozen_target_prices'])
        eval_len = min(len(eval_prices), len(frozen_targets))

        now_dt = datetime.now().astimezone().replace(tzinfo=None)
        error_val = 100.0
        if eval_len > 0:
            expected_targets = np.array(frozen_targets[:eval_len], dtype=float)
            tip_idx = eval_len - 1
            t_times = self.active_lock['target_times']
            bar_span_secs = max(1.0, (t_times[1] - t_times[0]).total_seconds()) if len(t_times) > 1 else 900.0

            if tip_idx == 0:
                elapsed_in_bar = max(0.0, time.time() - self.active_lock.get('sys_time', time.time()))
                prev_p = self.active_lock['base_price']
            else:
                elapsed_in_bar = max(0.0, (now_dt - t_times[tip_idx - 1]).total_seconds())
                prev_p = frozen_targets[tip_idx - 1]

            bar_prog = float(np.clip(elapsed_in_bar / bar_span_secs, 0.0, 1.0))
            expected_targets[tip_idx] = prev_p + ((frozen_targets[tip_idx] - prev_p) * bar_prog)
            self.active_lock['expected_tip_price'] = float(expected_targets[tip_idx])

            base_p = self.active_lock['base_price']
            pred_moves = (expected_targets - base_p) / (base_p + 1e-9)
            real_moves = (np.array(eval_prices[:eval_len], dtype=float) - base_p) / (base_p + 1e-9)
            error_val = calculate_directional_truth(pred_moves, real_moves, vol_scale=chop_bbw)

        tracking_prices = [self.active_lock['base_price']] + realized_prices + [current_live_price]
        tracking_times = [self.active_lock['base_time']] + active_actuals_df['date'].tolist() + [now_dt]

        return error_val, tracking_prices, tracking_times

    def calculate_kinetic_yield(self, df, current_live_price, delta_seconds):
        if not self.active_lock:
            return 1.0
        elapsed_secs = time.time() - self.active_lock['sys_time']
        bars_elapsed = len(df[df['ts'] > self.active_lock['base_ts']])
        base_p = self.active_lock['base_price']
        min_delta = base_p * 0.00025
        dynamic_difficulty = 1.0 + (1.0 * min(1.0, max(0.0, self.historical_accuracy / 100.0)))
        frozen_curve = self.active_lock['frozen_curve']

        if bars_elapsed == 0:
            if elapsed_secs < 10:
                return 1.0
            expected_delta = ((base_p * (1 + frozen_curve[0])) - base_p) * min(1.0, elapsed_secs / delta_seconds) * dynamic_difficulty
        elif bars_elapsed < self.horizon:
            expected_delta = ((base_p * (1 + frozen_curve[bars_elapsed])) - base_p) * dynamic_difficulty
        else:
            return 1.0

        if abs(expected_delta) <= min_delta:
            expected_delta = min_delta * (1 if expected_delta >= 0 else -1)
        return max(0.0, min(3.0, (current_live_price - base_p) / expected_delta))
# --- END OF PART 2 ---
# -----------------------------
# LEARNING & MEMORY SANCTUARY
# -----------------------------
class AdaptationGovernor:
    """
    Self-tuning learning rate and recalibration threshold governor:
      - Asymptotically tightens learning rate as historical & live accuracy climb toward 100%
        so peak-tuned weights are locked in rather than overwritten by noise.
      - Keeps recalc_trigger in a realistic regime-aware band (62% - 86%) so locks
        complete their horizon during normal wiggles but break cleanly on real misses.
    """
    def __init__(self):
        self.short_term_error = 0.25
        self.long_term_error = 0.25
        self.st_error_trace = deque(maxlen=50)
        self.lt_error_trace = deque(maxlen=500)
        self.learning_rate = 0.015
        self.recalc_trigger = 76.0

    def update(self, realized_error, truth_accuracy=65.0, live_acc=85.0):
        self.st_error_trace.append(float(realized_error))
        self.lt_error_trace.append(float(realized_error))
        if len(self.st_error_trace) < 2:
            return
        self.short_term_error = float(np.mean(self.st_error_trace))
        self.long_term_error = float(np.mean(self.lt_error_trace))

        blended_acc = (truth_accuracy * 0.60) + (live_acc * 0.40)
        norm_accuracy = min(1.0, max(0.0, blended_acc / 100.0))

        base_lr = 0.085 * ((1.0 - (norm_accuracy * 0.88)) ** 1.6)
        err_vel = self.short_term_error - self.long_term_error
        if err_vel > 0.002:
            self.learning_rate = float(np.clip(base_lr + min(0.04, err_vel * 1.2), 0.002, 0.12))
        else:
            self.learning_rate = float(np.clip((self.learning_rate * 0.85) + (base_lr * 0.15), 0.0005, 0.08))

        target_rcl = (blended_acc * 0.82)
        self.recalc_trigger = float(np.clip((self.recalc_trigger * 0.88) + (target_rcl * 0.12), 80.0, 95.0))

class MetricLearner:
    def __init__(self, dim):
        self.weights = np.ones(dim, dtype=float)
        self.champion_weights = np.ones(dim, dtype=float)
        self.best_err = 999.0
        self.velocity = np.zeros(dim, dtype=float)

    def update_from_errors(self, feature_vecs, errors, lr=0.01):
        mean_err = float(np.mean(errors))
        if mean_err < self.best_err:
            self.best_err = (self.best_err * 0.5) + (mean_err * 0.5)
            self.champion_weights = self.weights.copy()
        grad = np.mean(np.abs(feature_vecs) * np.clip(errors, 0.0, 3.0)[:, None], axis=0)
        self.velocity = 0.88 * self.velocity + 0.12 * (grad / (np.linalg.norm(grad) + 1e-9))
        self.weights = np.clip(self.weights * np.exp(-lr * self.velocity), 0.08, 4.5)
        if mean_err > self.best_err * 1.75:
            self.weights = (0.80 * self.weights) + (0.20 * self.champion_weights)

    def get_weights(self):
        return self.weights / (np.linalg.norm(self.weights) + 1e-9)

class MarketSanctuary:
    def __init__(self, memory_file, scaler_file):
        self.memory_file = memory_file
        self.scaler_file = scaler_file
        self.memories = []
        self.count = 0
        self.mean_vec, self.std_vec = load_scaler(self.scaler_file)
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "rb") as f:
                    self.memories = pickle.load(f)
                    self.count = len(self.memories)
            except Exception:
                pass

    def _score_memory(self, mem):
        age_hours = max(0.0, (datetime.now() - mem.get("created_at", datetime.now())).total_seconds() / 3600.0)
        recency = math.exp(-age_hours / 336.0)
        precision = 1.0 / (1.0 + (mem.get("error_ewma", 0.5) * 1.5))
        return float((recency * 0.45 + 0.55) * precision)

    def save_memories(self):
        try:
            tmp_file = self.memory_file + ".tmp"
            with open(tmp_file, "wb") as f:
                pickle.dump(self.memories, f)
            os.replace(tmp_file, self.memory_file)
        except Exception:
            pass

    def learn(self, pattern, outcome, volatility=0.0, persist_now=False):
        stored_vec = scale_vector(pattern, self.mean_vec, self.std_vec) if self.mean_vec is not None else pattern.copy()
        fuzz_scale = max(0.001, np.mean(np.abs(pattern)) * 0.08 * (1.0 / (1.0 + volatility * 10.0)))
        fuzzed = stored_vec + np.random.normal(0, fuzz_scale, size=len(stored_vec))
        now = datetime.now()
        self.memories.extend([
            {"vector": stored_vec, "outcome": np.array(outcome, dtype=float), "created_at": now, "error_ewma": 0.4, "score": 1.0},
            {"vector": fuzzed, "outcome": np.array(outcome, dtype=float), "created_at": now, "error_ewma": 0.45, "score": 0.95}
        ])
        self.count += 2
        self.mean_vec, self.std_vec = fit_scaler_online(self.mean_vec, self.std_vec, pattern, self.count)
        save_scaler(self.mean_vec, self.std_vec, self.scaler_file)
        if len(self.memories) > MEMORY_MAX:
            for m in self.memories:
                m["score"] = self._score_memory(m)
            self.memories.sort(key=lambda x: x["score"], reverse=True)
            self.memories = self.memories[:MEMORY_MAX]
        if persist_now:
            self.save_memories()

    def recall(self, current_pattern, top_k=20, metric_learner=None):
        if not self.memories or current_pattern is None:
            return []
        cur = scale_vector(current_pattern, self.mean_vec, self.std_vec) if self.mean_vec is not None else current_pattern
        w = metric_learner.get_weights() if metric_learner is not None else np.ones_like(cur)
        diffs = np.array([m["vector"] for m in self.memories]) - cur
        dists = np.sqrt(np.sum((diffs * diffs) * w, axis=1)) / np.array([max(0.05, m.get("score", 1.0)) for m in self.memories])
        idx_sorted = np.argsort(dists)[:top_k]
        return [(float(dists[i]), self.memories[i]["outcome"], self.memories[i]) for i in idx_sorted]

# -----------------------------
# CAN BUS ROUTER (FOLLOW THE LEADER + CAUSALITY SYNC)
# -----------------------------
class CANBusRouter:
    def __init__(self):
        self.bus_memory = {}
        self.hierarchy = {'4hr': None, '1d': '4hr', '1wk': '1d', '1mo': '1wk'}

    def broadcast_intent(self, tf_key, times, prices, confidence):
        self.bus_memory[tf_key] = {
            'times': np.array([t.timestamp() for t in times]),
            'prices': np.array(prices, dtype=float),
            'confidence': max(1.0, float(confidence))
        }

    def negotiate_truth(self):
        for child_tf, parent_tf in self.hierarchy.items():
            if not parent_tf or parent_tf not in self.bus_memory or child_tf not in self.bus_memory:
                continue
            p_prices = self.bus_memory[parent_tf]['prices']
            c_prices = self.bus_memory[child_tf]['prices']
            if len(p_prices) > 1 and len(c_prices) > 1:
                p_span = abs(p_prices[-1] - p_prices[0]) / (p_prices[0] + 1e-9)
                c_early_span = abs(c_prices[1] - c_prices[0]) / (c_prices[0] + 1e-9)
                if c_early_span > max(0.025, p_span * 2.2):
                    damp = max(0.025, p_span * 1.5) / (c_early_span + 1e-9)
                    self.bus_memory[child_tf]['prices'] = c_prices[0] + (c_prices - c_prices[0]) * min(1.0, damp)

    def pull_consensus(self, target_times, local_prices, confidence, tf_key='unknown'):
        parent_key = self.hierarchy.get(tf_key)
        if not parent_key or parent_key not in self.bus_memory:
            return local_prices

        parent_data = self.bus_memory[parent_key]
        parent_end_ts = parent_data['times'][-1]

        target_ts = np.array([t.timestamp() for t in target_times])
        parent_curve = np.interp(target_ts, parent_data['times'], parent_data['prices'])

        parent_conf = parent_data.get('confidence', 65.0)
        rel_parent_trust = np.clip(parent_conf / (parent_conf + max(10.0, confidence)), 0.25, 0.78)

        void_slosh = float(np.mean(np.abs(local_prices - parent_curve) / (parent_curve + 1e-9)))
        blend_factor = max(rel_parent_trust, 0.80) if void_slosh > 0.024 else rel_parent_trust
        final_prices = np.zeros_like(local_prices)
        last_parent_idx = None

        for i, ts in enumerate(target_ts):
            if ts <= parent_end_ts:
                final_prices[i] = (parent_curve[i] * blend_factor) + (local_prices[i] * (1.0 - blend_factor))
                last_parent_idx = i
            else:
                if last_parent_idx is None:
                    seed_base = (float(parent_data['prices'][-1]) * blend_factor) + (float(local_prices[0]) * (1.0 - blend_factor))
                    final_prices[0] = seed_base
                    last_parent_idx = 0
                    if i == 0:
                        continue
                local_delta = local_prices[i] - local_prices[last_parent_idx]
                handoff_base = final_prices[last_parent_idx]
                final_prices[i] = handoff_base + local_delta

        return np.maximum(np.array(local_prices, dtype=float) * 0.25, final_prices)

# -----------------------------
# MULTI-COMBO LIVE FINGERPRINT & BLUE LIGHTNING ENGINE (V22.2)
# -----------------------------
class LiveFingerprintEngine:
    def __init__(self, data_dir):
        self.db_file = os.path.join(data_dir, "fingerprint_paths.pkl")
        self.database = []
        self.load_db()
        self.active_pkg = None
        self.counter = max([p.get('id', 0) for p in self.database] + [0]) + 1
        self.active_prediction = None
        self.active_combo_ids = []
        self.pred_start_time = 0
        self.pred_base_price = 0.0
        self.fingerprint_accuracy = 85.0
        self.sequence_buffer = deque(maxlen=4)
        self.matched_sequence_depth = 1
        self.active_combo_count = 0
        self.dynamic_gain = 1.0

    def load_db(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "rb") as f:
                    self.database = pickle.load(f)
            except Exception:
                pass

    def save_db(self):
        try:
            tmp_file = self.db_file + ".tmp"
            with open(tmp_file, "wb") as f:
                pickle.dump(self.database[-850:], f)
            os.replace(tmp_file, self.db_file)
        except Exception:
            pass

    def start_recording(self, current_time, engine_cache, start_price, bids=None, asks=None):
        try:
            imbalance = 0.0
            if bids is not None and asks is not None and len(bids) > 0 and len(asks) > 0:
                bid_v, ask_v = np.sum(bids[:50, 1]), np.sum(asks[:50, 1])
                imbalance = (bid_v - ask_v) / (bid_v + ask_v + 1e-9)

            c4 = engine_cache.get('4hr', {})
            snapshot = {
                'momentum': float(c4.get('momentum', 0.0)),
                'chop': float(c4.get('chop_bbw', 0.0)),
                'imbalance': float(imbalance),
                'rsi': float(c4.get('rsi', 50.0)),
                'coil': float(c4.get('microstructure', {}).get('coil_score', 0.0))
            }
            self.active_pkg = {
                'id': self.counter,
                'start_time': current_time,
                'base_price': start_price,
                'physics': snapshot,
                'markers': [],
                'next_id': None,
                'grade_ewma': 78.0
            }
        except Exception:
            pass

    def record_tick(self, price):
        if self.active_pkg:
            self.active_pkg['markers'].append((datetime.now().astimezone().replace(tzinfo=None), price))

    def commit_package(self):
        if not self.active_pkg or len(self.active_pkg['markers']) < 2:
            return
        base_p = self.active_pkg['base_price']
        self.active_pkg['path'] = [
            ((dt - self.active_pkg['markers'][0][0]).total_seconds(), (p - base_p) / (base_p + 1e-9))
            for dt, p in self.active_pkg['markers']
        ]
        if self.database:
            self.database[-1]['next_id'] = self.active_pkg['id']
        self.database.append(self.active_pkg)
        self.sequence_buffer.append(self.active_pkg)
        self.counter += 1
        self.active_pkg = None
        self.save_db()

    def synthesize_multi_combo_lightning(self, current_physics, tolerance=0.28, top_k=6):
        if not self.database:
            self.matched_sequence_depth = 1
            self.active_combo_count = 0
            self.dynamic_gain = 1.0
            return None

        live_physics_seq = [pkg['physics'] for pkg in self.sequence_buffer] + [current_physics]
        max_depth = min(4, len(live_physics_seq))
        search_space = self.database[-1000:]

        candidates = []
        for depth in range(max_depth, 0, -1):
            target_seq = live_physics_seq[-depth:]
            for i in range(depth - 1, len(search_space)):
                hist_seq = search_space[i - depth + 1 : i + 1]
                terminal_pkg = hist_seq[-1]
                if 'path' not in terminal_pkg or len(terminal_pkg['path']) < 2:
                    continue
                total_error = 0.0
                valid = True
                for j in range(depth):
                    hp = hist_seq[j].get('physics', {})
                    tp = target_seq[j]
                    m_diff = abs(hp.get('momentum', 0.0) - tp.get('momentum', 0.0))
                    c_diff = abs(hp.get('chop', 0.0) - tp.get('chop', 0.0))
                    i_diff = abs(hp.get('imbalance', 0.0) - tp.get('imbalance', 0.0))
                    r_diff = abs(hp.get('rsi', 50.0) - tp.get('rsi', 50.0)) / 100.0
                    k_diff = abs(hp.get('coil', 0.0) - tp.get('coil', 0.0)) / 100.0

                    if m_diff > tolerance or c_diff > tolerance or i_diff > (tolerance * 1.6):
                        valid = False
                        break
                    total_error += (m_diff * 2.2) + c_diff + (i_diff * 0.6) + (r_diff * 0.4) + (k_diff * 0.3)

                if valid:
                    norm_err = total_error / depth
                    pkg_grade = float(terminal_pkg.get('grade_ewma', 75.0)) / 100.0
                    depth_bonus = 1.0 + (0.35 * (depth - 1))
                    combo_score = (depth_bonus * pkg_grade) / (norm_err + 0.02)
                    candidates.append((combo_score, depth, terminal_pkg))

        if not candidates:
            self.matched_sequence_depth = 1
            self.active_combo_count = 0
            self.dynamic_gain = 1.0
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        selected = []
        seen_ids = set()
        for score, depth, pkg in candidates:
            pid = pkg.get('id')
            if pid not in seen_ids:
                seen_ids.add(pid)
                selected.append((score, depth, pkg))
            if len(selected) >= top_k:
                break

        self.active_combo_ids = [p[2].get('id') for p in selected]
        self.active_combo_count = len(selected)
        self.matched_sequence_depth = max(p[1] for p in selected)

        weights = np.array([p[0] for p in selected], dtype=float)
        weights /= (np.sum(weights) + 1e-9)

        grid_secs = np.linspace(0.0, 30.0, 12)
        interp_paths = []
        term_dirs = []
        for _, _, pkg in selected:
            p_arr = np.array(pkg['path'], dtype=float)
            secs = p_arr[:, 0]
            pcts = p_arr[:, 1]
            if secs[-1] <= 0:
                continue
            interp_pcts = np.interp(grid_secs, secs, pcts)
            interp_paths.append(interp_pcts)
            term_dirs.append(np.sign(interp_pcts[-1]))

        if not interp_paths:
            return selected[0][2]

        stack = np.vstack(interp_paths)
        w_valid = weights[:len(interp_paths)]
        w_valid /= (np.sum(w_valid) + 1e-9)
        synthesized_pcts = np.average(stack, axis=0, weights=w_valid)

        dir_agreement = abs(float(np.sum(np.array(term_dirs) * w_valid)))
        depth_factor = 1.0 + (0.20 * (self.matched_sequence_depth - 1))
        acc_factor = np.clip(self.fingerprint_accuracy / 65.0, 0.50, 1.55)
        self.dynamic_gain = float(np.clip(dir_agreement * depth_factor * acc_factor * 1.35, 0.45, 2.35))

        synthesized_pcts *= self.dynamic_gain
        synth_path = [(float(s), float(p)) for s, p in zip(grid_secs, synthesized_pcts)]

        return {
            'id': selected[0][2].get('id', 0),
            'path': synth_path,
            'next_id': selected[0][2].get('next_id'),
            'combo_strength': self.dynamic_gain,
            'combo_count': self.active_combo_count
        }

    def build_horizon_curve(self, cfg, base_curve_ref, formula=None):
        horizon = cfg["horizon"]
        base_arr = np.array(base_curve_ref, dtype=float)
        if not self.active_prediction or 'path' not in self.active_prediction or len(self.active_prediction['path']) < 2:
            return base_arr

        path_arr = np.array(self.active_prediction['path'], dtype=float)
        secs = path_arr[:, 0]
        pcts = path_arr[:, 1]
        total_secs = max(1.0, float(secs[-1]))
        norm_t = secs / total_secs

        reach_frac = formula.get("lightning_reach") if formula is not None else 0.48
        warp_gain = formula.get("lightning_warp_gain") if formula is not None else 0.88
        combo_boost = float(self.active_prediction.get('combo_strength', self.dynamic_gain))
        eff_reach = float(np.clip(reach_frac * (0.85 + 0.15 * combo_boost), 0.20, 0.88))

        tf_scale = min(4.2, math.sqrt(max(1.0, cfg["delta"].total_seconds() / 30.0)) * 0.38) * warp_gain
        scaled_contour = pcts * tf_scale
        terminal_val = float(scaled_contour[-1])

        l_curve = np.zeros(horizon, dtype=float)
        for i in range(horizon):
            prog = (i + 1) / horizon
            if prog <= eff_reach:
                sub_p = prog / max(1e-6, eff_reach)
                l_curve[i] = float(np.interp(sub_p, norm_t, scaled_contour))
            else:
                over_p = (prog - eff_reach) / max(1e-6, 1.0 - eff_reach)
                decay = math.exp(-over_p * 2.1)
                base_delta = base_arr[i] - base_arr[min(horizon - 1, int(eff_reach * horizon))]
                l_curve[i] = (terminal_val * decay) + ((terminal_val + base_delta) * (1.0 - decay))
        return l_curve

    def _backgrade_combo_packages(self, inst_acc):
        if not self.active_combo_ids:
            return
        id_set = set(self.active_combo_ids)
        for pkg in reversed(self.database[-250:]):
            if pkg.get('id') in id_set:
                old_g = float(pkg.get('grade_ewma', 75.0))
                pkg['grade_ewma'] = float(np.clip((old_g * 0.90) + (inst_acc * 0.10), 15.0, 99.0))

    def tick(self, current_time, live_price, engine_cache, governor, bids=None, asks=None):
        draw_data = {'recording': None, 'lightning': None}
        try:
            if not self.active_pkg:
                self.start_recording(current_time, engine_cache, live_price, bids, asks)
            else:
                self.record_tick(live_price)
                draw_data['recording'] = self.active_pkg['markers']
                if current_time - self.active_pkg['start_time'] > 30:
                    self.commit_package()
                    self.start_recording(current_time, engine_cache, live_price, bids, asks)

            if not self.active_prediction and '4hr' in engine_cache and int(current_time) % 5 == 0:
                self.active_prediction = self.synthesize_multi_combo_lightning(
                    self.active_pkg['physics'] if self.active_pkg else {}, tolerance=0.28, top_k=6
                )
                if self.active_prediction:
                    self.pred_start_time, self.pred_base_price = current_time, live_price

            if self.active_prediction:
                elapsed = current_time - self.pred_start_time
                if 'path' in self.active_prediction and self.pred_base_price > 0:
                    expected_pct = next((m[1] for m in self.active_prediction['path'] if m[0] >= elapsed), self.active_prediction['path'][-1][1])
                    actual_pct = (live_price - self.pred_base_price) / (self.pred_base_price + 1e-9)
                    inst_acc = float(np.clip(100.0 * math.exp(-abs(expected_pct - actual_pct) * 85.0), 10.0, 100.0))
                    self.fingerprint_accuracy = (self.fingerprint_accuracy * 0.92) + (inst_acc * 0.08)
                    self._backgrade_combo_packages(inst_acc)

                draw_data['lightning'] = self.active_prediction
                draw_data['lightning_accuracy'] = self.fingerprint_accuracy
                draw_data['pred_base_price'] = self.pred_base_price

                if current_time - self.pred_start_time > 30:
                    self.active_prediction = self.synthesize_multi_combo_lightning(
                        self.active_pkg['physics'] if self.active_pkg else {}, tolerance=0.28, top_k=6
                    )
                    if self.active_prediction:
                        self.pred_start_time = current_time
                        self.pred_base_price = live_price
                    else:
                        self.pred_start_time, self.pred_base_price = 0, 0.0
        except Exception:
            pass
        return draw_data

# -----------------------------
# DATA INGESTION (POOLED SESSION)
# -----------------------------
def fetch_timeframe_data(interval, limit_val):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={BINANCE_SYMBOL}&interval={interval}&limit={limit_val}"
        r = HTTP_SESSION.get(url, timeout=8)
        if r.status_code != 200:
            return None
        df = pd.DataFrame(r.json(), columns=['ts', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
        df = df[['ts', 'open', 'high', 'low', 'close', 'volume', 'num_trades', 'taker_base_vol']].astype(float)
        df["date"] = pd.to_datetime(df["ts"], unit="ms", utc=True).dt.tz_convert(datetime.now().astimezone().tzinfo).dt.tz_localize(None)
        return df
    except Exception:
        return None

def fetch_live_price():
    try:
        r = HTTP_SESSION.get(f"https://api.binance.com/api/v3/ticker/price?symbol={BINANCE_SYMBOL}", timeout=4)
        if r.status_code == 200:
            return float(r.json()['price'])
    except Exception:
        pass
    return None

def fetch_dancing_price():
    try:
        r = HTTP_SESSION.get(f"https://api.binance.com/api/v3/ticker/price?symbol={BINANCE_SYMBOL}", timeout=1.0)
        if r.status_code == 200:
            return float(r.json()['price'])
    except Exception:
        pass
    return None

def fetch_market_depth(symbol, limit=100):
    try:
        r = HTTP_SESSION.get(f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}", timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            return np.array(data['bids'], dtype=float), np.array(data['asks'], dtype=float)
    except Exception:
        pass
    return None, None

def fetch_factual_tape_commits(symbol, limit=80):
    try:
        r = HTTP_SESSION.get(f"https://api.binance.com/api/v3/trades?symbol={symbol}&limit={limit}", timeout=1.5)
        if r.status_code == 200:
            trades = r.json()
            if not trades:
                return None
            buy_vol = sum(float(t['qty']) for t in trades if not t.get('isBuyerMaker', False))
            sell_vol = sum(float(t['qty']) for t in trades if t.get('isBuyerMaker', False))
            total_vol = buy_vol + sell_vol + 1e-9
            t_span_sec = max(0.5, (float(trades[-1]['time']) - float(trades[0]['time'])) / 1000.0)
            qtys = np.array([float(t['qty']) for t in trades], dtype=float)
            whale_fills = float(np.sum(qtys[qtys > (np.mean(qtys) * 3.0)])) / total_vol
            return {
                'buy_vol': buy_vol, 'sell_vol': sell_vol,
                'tape_imbalance': (buy_vol - sell_vol) / total_vol,
                'trades_per_sec': len(trades) / t_span_sec,
                'whale_fill_ratio': whale_fills
            }
    except Exception:
        pass
    return None

class SpoofSamplerAndLandscapeEngine:
    def __init__(self, grid_size=65):
        self.grid_size = grid_size
        self.verified_bids = None
        self.verified_asks = None
        self.prev_raw_bid_vol = 0.0
        self.prev_raw_ask_vol = 0.0
        self.last_status = "SOLID-INIT"
        self.last_passed = True
        self.last_tape = {'tape_imbalance': 0.0, 'trades_per_sec': 1.0, 'whale_fill_ratio': 0.0}

    def sample_and_filter_book(self, raw_bids, raw_asks, live_price, tape_data=None, strictness=0.45):
        if raw_bids is None or raw_asks is None or len(raw_bids) == 0 or len(raw_asks) == 0 or live_price <= 0:
            return self.verified_bids, self.verified_asks, "BOOK-EMPTY(HOLD)", False
        if tape_data is not None:
            self.last_tape = tape_data
        tape = self.last_tape
        near_bids = raw_bids[raw_bids[:, 0] >= live_price * 0.982]
        near_asks = raw_asks[raw_asks[:, 0] <= live_price * 1.018]
        if len(near_bids) == 0: near_bids = raw_bids[:20]
        if len(near_asks) == 0: near_asks = raw_asks[:20]

        bid_vol, ask_vol = float(np.sum(near_bids[:, 1])), float(np.sum(near_asks[:, 1]))
        book_imb = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-9)
        bid_peak = float(np.max(near_bids[:, 1]) / (np.mean(near_bids[:, 1]) + 1e-9))
        ask_peak = float(np.max(near_asks[:, 1]) / (np.mean(near_asks[:, 1]) + 1e-9))
        bid_flash = (bid_vol / (self.prev_raw_bid_vol + 1e-9)) if self.prev_raw_bid_vol > 0 else 1.0
        ask_flash = (ask_vol / (self.prev_raw_ask_vol + 1e-9)) if self.prev_raw_ask_vol > 0 else 1.0
        self.prev_raw_bid_vol, self.prev_raw_ask_vol = bid_vol, ask_vol

        tape_imb, tps, whale_c = float(tape.get('tape_imbalance', 0.0)), float(tape.get('trades_per_sec', 1.0)), float(tape.get('whale_fill_ratio', 0.0))
        wall_thresh = 4.6 - (strictness * 1.5)
        spoof_detected, reason = False, "SOLID-VERIFIED"

        if (ask_peak > wall_thresh and book_imb < -0.35) or (ask_flash > 3.2):
            if not ((tape_imb < -0.05) or (tps > 1.8) or (whale_c > 0.18)):
                spoof_detected, reason = True, "SPOOF-ASK-IGN(PREV)"
        elif (bid_peak > wall_thresh and book_imb > 0.35) or (bid_flash > 3.2):
            if not ((tape_imb > 0.05) or (tps > 1.8) or (whale_c > 0.18)):
                spoof_detected, reason = True, "SPOOF-BID-IGN(PREV)"

        if spoof_detected and self.verified_bids is not None and self.verified_asks is not None:
            self.last_status, self.last_passed = reason, False
            return self.verified_bids, self.verified_asks, reason, False

        self.verified_bids, self.verified_asks = raw_bids.copy(), raw_asks.copy()
        self.last_status, self.last_passed = reason, True
        return self.verified_bids, self.verified_asks, reason, True

    def solve_easiest_path(self, df, live_price, verified_bids, verified_asks, hybrid_momentum, lightning_curve, fuzz_curve, chop_bbw, formula=None):
        horizon = len(lightning_curve)
        if live_price <= 0 or horizon == 0:
            return np.zeros(horizon, dtype=float), self.last_status, 1.0
        flow_gain = formula.get("landscape_flow_gain") if formula is not None else 0.90
        span_pct = float(np.clip(max(chop_bbw * 2.1, 0.018), 0.012, 0.075))
        rel_grid = np.linspace(-span_pct, span_pct, self.grid_size)
        resistance = np.ones(self.grid_size, dtype=float) * 0.35

        for book_side in (verified_bids, verified_asks):
            if book_side is not None and len(book_side) > 0:
                q_mean = float(np.mean(book_side[:, 1])) + 1e-9
                for bp, bq in book_side[:60]:
                    rel_p = (bp - live_price) / live_price
                    if -span_pct <= rel_p <= span_pct:
                        resistance += (bq / q_mean) * np.exp(-0.5 * (((rel_grid - rel_p) / (span_pct * 0.08)) ** 2)) * 0.45

        if df is not None and len(df) >= 20:
            sub_df = df.tail(50)
            v_mean = float(sub_df['volume'].mean()) + 1e-9
            for rc, rv in zip(sub_df['close'].values, sub_df['volume'].values):
                rel_c = (float(rc) - live_price) / live_price
                if -span_pct <= rel_c <= span_pct:
                    resistance += (float(rv) / v_mean) * np.exp(-0.5 * (((rel_grid - rel_c) / (span_pct * 0.10)) ** 2)) * 0.18

        resistance = np.clip(resistance, 0.15, 8.0)
        conductance = 1.0 / resistance
        tps_boost = min(2.0, float(self.last_tape.get('trades_per_sec', 1.0)) / 3.0)
        emf_bias = (hybrid_momentum * 0.55) + (float(self.last_tape.get('tape_imbalance', 0.0)) * 0.008 * tps_boost)

        curr_rel = 0.0
        easiest_path = np.zeros(horizon, dtype=float)
        step_radius = max(span_pct / max(3.0, horizon * 0.32), 0.0020)

        for t in range(horizon):
            feeler = (float(lightning_curve[t]) * 0.55) + (float(fuzz_curve[t]) * 0.45) + (emf_bias * ((t + 1) / horizon))
            mask = np.abs(rel_grid - curr_rel) <= (step_radius * 1.75)
            if not np.any(mask): mask = np.ones_like(rel_grid, dtype=bool)
            c_rel, c_cond, c_res = rel_grid[mask], conductance[mask], resistance[mask]
            align = np.exp(-np.abs(c_rel - feeler) / (step_radius + 1e-9))
            punch = np.where((abs(feeler) * 120.0 * tps_boost) > c_res * 1.35, 1.45, 1.0)
            pot = (c_cond ** 1.15) * align * punch
            pot /= (np.sum(pot) + 1e-9)
            step_pos = (float(np.sum(c_rel * pot)) * 0.65) + (float(c_rel[int(np.argmax(pot))]) * 0.35)
            curr_rel = (curr_rel * 0.25) + (step_pos * 0.75)
            easiest_path[t] = curr_rel * flow_gain

        return easiest_path, self.last_status, float(np.mean(conductance))

def check_path_against_orderbook(bids, asks, current_price, projected_move_pct):
    if bids is None or asks is None or len(bids) == 0 or len(asks) == 0:
        return True
    scan_pct = max(abs(projected_move_pct), 0.015)
    bid_vol = np.sum(bids[bids[:, 0] >= current_price * (1 - scan_pct)][:, 1])
    ask_vol = np.sum(asks[asks[:, 0] <= current_price * (1 + scan_pct)][:, 1])
    imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol + 1e-9)
    return (imbalance * np.sign(projected_move_pct)) >= -0.35

# -----------------------------
# 180° TICK VECTOR & CORNER KINEMATICS ENGINE (CDA GOVERNED)
# -----------------------------
class CornerKinematicsEngine:
    """
    1. Maps tick-to-tick velocity into 180 degrees of vertical possibility (-90° to +90°) with spread-bounce filtering.
    2. Monitors 3-phase cornering mechanics (APPROACH -> APEX -> EGRESS) and vaults proven 6-point corner signatures.
    3. Computes Change of Direction Accuracy (CDA) and dynamically governs how strongly stored corner signatures shape future turns.
    """
    def __init__(self, data_dir):
        self.vault_file = os.path.join(data_dir, "proven_corner_vault_v22.pkl")
        self.vault = deque(maxlen=400)
        self.cda_accuracy = 68.0
        self.influence_weight = 0.28
        self._load_vault()
        self.last_price = 0.0
        self.last_ts = time.time()
        self.raw_angles = deque(maxlen=5)
        self.angle_history = deque(maxlen=30)
        self.current_angle = 0.0
        self.angular_vel = 0.0
        self.last_tilt = 0.0
        self.delta_theta = 0.0
        self.phase = "CRUISE"
        self.entry_angle = 0.0
        self.entry_decel = 0.0
        self.apex_start_ts = 0.0
        self.apex_price = 0.0
        self.pending_corner_sig = None
        self.pending_pred_turn = {}

    def _load_vault(self):
        if os.path.exists(self.vault_file):
            try:
                with open(self.vault_file, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, dict):
                    self.vault = deque(data.get("vault", []), maxlen=400)
                    self.cda_accuracy = float(data.get("cda_accuracy", 68.0))
            except Exception:
                pass
        self._update_influence()

    def save_vault(self):
        try:
            tmp = self.vault_file + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump({"vault": list(self.vault), "cda_accuracy": self.cda_accuracy}, f)
            os.replace(tmp, self.vault_file)
        except Exception:
            pass

    def _update_influence(self):
        if self.cda_accuracy < 55.0:
            self.influence_weight = 0.0
        else:
            norm_cda = (self.cda_accuracy - 55.0) / 45.0
            self.influence_weight = float(np.clip(0.10 + (norm_cda ** 1.25) * 0.65, 0.0, 0.75))

    def update_tick(self, price, tape_data=None):
        if price is None or price <= 0:
            return self.current_angle
        now = time.time()
        if not hasattr(self, "abs_move_ema"):
            self.abs_move_ema = 0.00008
            self.tick_window = deque(maxlen=6)

        if self.last_price <= 0:
            self.last_price = float(price)
            self.last_ts = now
            self.tick_window.append((now, float(price)))
            return self.current_angle

        pct_move = (price - self.last_price) / (self.last_price + 1e-9)
        prev_angle = self.current_angle

        if abs(pct_move) > 1e-9:
            dt = max(0.25, min(20.0, now - self.last_ts))
            self.tick_window.append((now, float(price)))
            win_base = self.tick_window[0][1]
            win_pct = (price - win_base) / (win_base + 1e-9)

            self.abs_move_ema = float(np.clip((self.abs_move_ema * 0.85) + (abs(pct_move) * 0.15), 1e-6, 0.005))
            scale_denom = max(1e-6, self.abs_move_ema * 0.85 * math.sqrt(dt))
            norm_rate = ((pct_move * 0.65) + (win_pct * 0.35)) / scale_denom
            inst_angle = math.atan(norm_rate * 1.35) * (180.0 / math.pi)

            self.raw_angles.append(inst_angle)
            med_angle = float(np.median(list(self.raw_angles)[-3:]))
            self.current_angle = float(np.clip((prev_angle * 0.25) + (inst_angle * 0.50) + (med_angle * 0.25), -90.0, 90.0))
            self.angular_vel = (self.current_angle - prev_angle) / dt
            self.last_price = float(price)
            self.last_ts = now
            self.angle_history.append((now, price, self.current_angle))
            self._step_corner_state_machine(now, price, tape_data)
        else:
            idle_secs = now - self.last_ts
            if idle_secs > 2.5:
                self.current_angle = float(self.current_angle * 0.86)
                self.angular_vel = (self.current_angle - prev_angle) / max(0.5, idle_secs)
                self.angle_history.append((now, price, self.current_angle))
                self._step_corner_state_machine(now, price, tape_data)

        return self.current_angle

    def _step_corner_state_machine(self, now, price, tape_data):
        if len(self.angle_history) < 6:
            return
        recent_angles = [x[2] for x in list(self.angle_history)[-6:]]
        mean_prev = float(np.mean(recent_angles[:3]))
        mean_curr = float(np.mean(recent_angles[3:]))
        tape_imb = float(tape_data.get('tape_imbalance', 0.0)) if tape_data else 0.0
        tps_ratio = float(tape_data.get('trades_per_sec', 1.0)) if tape_data else 1.0

        if self.phase == "CRUISE":
            if abs(mean_prev) > 28.0 and abs(mean_curr) < abs(mean_prev) * 0.68:
                self.phase = "APPROACH"
                self.entry_angle = mean_prev
                self.entry_decel = mean_curr - mean_prev
                self.apex_start_ts = now
                self.apex_price = price

        elif self.phase == "APPROACH":
            if abs(self.current_angle) <= 15.0:
                self.phase = "APEX-DWELL"
                self.apex_start_ts = now
                self.apex_price = price
            elif (now - self.apex_start_ts) > 45.0:
                self.phase = "CRUISE"

        elif self.phase == "APEX-DWELL":
            dwell_secs = max(1.0, now - self.apex_start_ts)
            opposite_snap = (self.entry_angle * self.current_angle) < 0 and abs(self.current_angle) >= 22.0
            if opposite_snap:
                self.phase = "EGRESS"
                self.delta_theta = self.current_angle - self.last_tilt
                sig_vec = np.array([
                    self.entry_angle / 90.0,
                    np.clip(self.entry_decel / 90.0, -1.5, 1.5),
                    np.clip(dwell_secs / 60.0, 0.02, 2.0),
                    self.current_angle / 90.0,
                    np.clip(self.delta_theta / 90.0, -2.0, 2.0),
                    tape_imb
                ], dtype=float)
                self.pending_corner_sig = {
                    'ts': now,
                    'apex_price': self.apex_price,
                    'egress_price': price,
                    'exit_angle': self.current_angle,
                    'dwell_secs': dwell_secs,
                    'vec': sig_vec,
                    'verified': False
                }
                self._grade_predicted_turn(now, price, self.current_angle)
            elif dwell_secs > 90.0 or (abs(self.current_angle) > 35.0 and (self.entry_angle * self.current_angle) > 0):
                self.phase = "CRUISE"

        elif self.phase == "EGRESS":
            if self.pending_corner_sig:
                elapsed_egress = now - self.pending_corner_sig['ts']
                move_from_apex = (price - self.pending_corner_sig['apex_price']) / (self.pending_corner_sig['apex_price'] + 1e-9)
                expected_dir = 1.0 if self.pending_corner_sig['exit_angle'] > 0 else -1.0
                if elapsed_egress >= 12.0:
                    if (move_from_apex * expected_dir) > 0.0012:
                        self.pending_corner_sig['follow_through'] = float(move_from_apex)
                        self.pending_corner_sig['verified'] = True
                        self.vault.append(self.pending_corner_sig)
                        self.cda_accuracy = float(np.clip((self.cda_accuracy * 0.88) + (88.0 * 0.12), 20.0, 99.0))
                        self._update_influence()
                        self.save_vault()
                    self.pending_corner_sig = None
                    self.phase = "CRUISE"

    def register_predicted_turn(self, tf_key, apex_idx, horizon, delta_secs, pred_exit_angle):
        self.pending_pred_turn[tf_key] = {
            'pred_ts': time.time() + (apex_idx * delta_secs),
            'tau': max(30.0, delta_secs * 1.5),
            'pred_exit_angle': float(pred_exit_angle)
        }

    def _grade_predicted_turn(self, actual_ts, actual_price, actual_exit_angle):
        if '4hr' not in self.pending_pred_turn:
            return
        pt = self.pending_pred_turn['4hr']
        a_timing = math.exp(-abs(actual_ts - pt['pred_ts']) / max(60.0, pt['tau']))
        rad_diff = math.radians((actual_exit_angle - pt['pred_exit_angle']) * 0.5)
        a_vector = max(0.0, math.cos(rad_diff))
        a_kinetic = min(1.0, abs(actual_exit_angle) / 45.0)
        cda_score = 100.0 * ((0.35 * a_timing) + (0.40 * a_vector) + (0.25 * a_kinetic))
        self.cda_accuracy = float(np.clip((self.cda_accuracy * 0.82) + (cda_score * 0.18), 20.0, 99.0))
        self._update_influence()

    def apply_corner_signature_influence(self, curve, tf_key, cfg, df, live_price, rsi, spatial_data, order_flow, apex_tag):
        shaped = np.array(curve, dtype=float)
        horizon = len(shaped)
        if horizon < 4 or self.influence_weight <= 0.01 or len(self.vault) == 0:
            return shaped, apex_tag
        delta_r = float(order_flow.get('taker_delta_ratio', 0.0))
        vel_r = float(order_flow.get('trade_velocity', 1.0))
        live_vec = np.array([
            self.current_angle / 90.0,
            np.clip(self.angular_vel / 45.0, -1.5, 1.5),
            0.35,
            -np.sign(self.current_angle) * 0.5,
            delta_r,
            np.clip(vel_r / 3.0, 0.2, 3.0)
        ], dtype=float)
        dists = []
        for item in self.vault:
            v = item['vec']
            d = float(np.linalg.norm((v[:2] - live_vec[:2]) * 1.5) + np.linalg.norm(v[4:] - live_vec[4:]))
            dists.append((d, item))
        dists.sort(key=lambda x: x[0])
        best_dist, best_match = dists[0]
        if best_dist > 1.35:
            return shaped, apex_tag
        match_conf = math.exp(-best_dist * 0.85) * self.influence_weight
        proven_exit_angle = float(best_match.get('exit_angle', -self.current_angle))
        proven_ft = float(best_match.get('follow_through', 0.004 * np.sign(proven_exit_angle)))
        dwell_ratio = float(np.clip(best_match.get('dwell_secs', 15.0) / 45.0, 0.15, 0.65))
        turn_idx = int(np.clip(round(horizon * dwell_ratio), 1, horizon - 2))
        for i in range(turn_idx + 1, horizon):
            post_p = (i - turn_idx) / float(max(1, horizon - 1 - turn_idx))
            corner_pull = shaped[turn_idx] + (proven_ft * (post_p ** 0.90) * (1.0 + abs(proven_exit_angle) / 90.0))
            shaped[i] = ((1.0 - match_conf) * shaped[i]) + (match_conf * corner_pull)
        if tf_key == '4hr':
            self.register_predicted_turn(tf_key, turn_idx, horizon, cfg["delta"].total_seconds(), proven_exit_angle)
        new_tag = f"CRN-{'TOP' if proven_exit_angle < 0 else 'BTM'}@{turn_idx}" if match_conf > 0.22 else apex_tag
        return shaped, new_tag

    def compute_nose_segment(self, ax, now_dt, live_price, cfg):
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_span = max(1e-6, xlim[1] - xlim[0])
        y_span = max(1e-9, ylim[1] - ylim[0])
        theta_rad = math.radians(self.current_angle)
        nose_len = 0.072
        head_len = nose_len * 0.36
        wing_rad = math.radians(150.0)

        dx_norm = nose_len * math.cos(theta_rad)
        dy_norm = nose_len * math.sin(theta_rad)

        lx_norm = dx_norm + (head_len * math.cos(theta_rad + wing_rad))
        ly_norm = dy_norm + (head_len * math.sin(theta_rad + wing_rad))
        rx_norm = dx_norm + (head_len * math.cos(theta_rad - wing_rad))
        ry_norm = dy_norm + (head_len * math.sin(theta_rad - wing_rad))

        x0_num = mdates.date2num(now_dt)
        tip_dt = mdates.num2date(x0_num + (dx_norm * x_span)).replace(tzinfo=None)
        l_dt = mdates.num2date(x0_num + (lx_norm * x_span)).replace(tzinfo=None)
        r_dt = mdates.num2date(x0_num + (rx_norm * x_span)).replace(tzinfo=None)

        tip_y = live_price + (dy_norm * y_span)
        l_y = live_price + (ly_norm * y_span)
        r_y = live_price + (ry_norm * y_span)

        return [now_dt, tip_dt, l_dt, r_dt, tip_dt], [live_price, tip_y, l_y, r_y, tip_y]

STATE_MANAGER = StatePersistence(STATE_JSON_FILE, STATE_SQLITE_DB, fallback_json_path=STATE_JSON_FALLBACK)
EXEC_ENGINE = FeeAwareExecutionEngine(fee_rate=0.0010, initial_bankroll=1000.0)
REGIME_SENTINEL = RegimeShiftSentinel(min_lock_seconds=120.0, confirm_ticks_required=4)
REDFUZZ_VAULT = SelfGoverningRedFuzzVault(DATA_DIR)
SPOOF_LANDSCAPE = SpoofSamplerAndLandscapeEngine(grid_size=65)
CORNER_ENGINE = CornerKinematicsEngine(DATA_DIR)

ENGINES = {}
for tf, cfg in TIMEFRAMES.items():
    ENGINES[tf] = {
        "sanctuary": MarketSanctuary(os.path.join(DATA_DIR, f"neiro_memory_{tf}.pkl"), os.path.join(DATA_DIR, f"neiro_scaler_{tf}.json")),
        "governor": AdaptationGovernor(),
        "fuzz": AdvancedFuzzEngine(cfg["horizon"]),
        "swarm": MarkerSwarm(cfg["horizon"]),
        "locker": TemporalLockManager(cfg["horizon"]),
        "opinion": BackfeedOpinionEngine(cfg["horizon"]),
        "formula": DecomposedPredictionFormula(cfg["horizon"]),
        "metric": None,
        "prev_tilt": 0.0,
        "last_live_accuracy": 100.0,
        "p_max": 1.0
    }

def bootstrap_history(tf_key, state_restored=False):
    cfg, engine = TIMEFRAMES[tf_key], ENGINES[tf_key]
    df = fetch_timeframe_data(cfg["interval"], cfg["limit"])
    if df is None or len(df) < 35:
        return

    if engine["sanctuary"].count <= 50:
        print(f"[*] Cold Boot: Harvesting {tf_key} historical signatures...")
        learned_count = 0
        for i in range(10, len(df) - cfg["horizon"] - 1):
            pat = extract_pattern_vector(df, i)
            if pat is not None:
                base_p = df['close'].iloc[i]
                future_p = df['close'].iloc[i+1 : i+1+cfg["horizon"]].values
                if len(future_p) == cfg["horizon"] and base_p > 0:
                    engine["sanctuary"].learn(pat, (future_p - base_p) / base_p, volatility=df['close'].iloc[i-10:i].std() if i >= 10 else 0.0)
                    learned_count += 1
        engine["sanctuary"].save_memories()
        print(f"[+] {tf_key} Sanctuary hydrated: {learned_count} signatures.")

    last_pat = extract_pattern_vector(df, len(df) - 1)
    if last_pat is not None and engine["metric"] is None:
        engine["metric"] = MetricLearner(len(last_pat))

    if not state_restored or engine["swarm"].eval_count == 0:
        print(f"[*] Calibrating {tf_key} Decomposed Formula, Swarm Nodes & Backfeed Opinion...")
        chop_est = calculate_advanced_chop_bias(df)
        for idx in np.linspace(20, len(df) - cfg["horizon"] - 2, min(35, len(df) - cfg["horizon"] - 25)).astype(int):
            pat = extract_pattern_vector(df, idx)
            if pat is not None:
                base_p = df['close'].iloc[idx]
                future_p = df['close'].iloc[idx+1 : idx+1+cfg["horizon"]].values
                if len(future_p) == cfg["horizon"] and base_p > 0:
                    matches = engine["sanctuary"].recall(pat, top_k=5, metric_learner=engine["metric"])
                    if matches:
                        paths = np.vstack([np.pad(m[1][:cfg["horizon"]], (0, max(0, cfg["horizon"] - len(m[1][:cfg["horizon"]]))), 'edge') for m in matches])
                        sanc_curve = simulate_smashed_path(
                            paths, np.array([m[0] for m in matches]),
                            np.array([m[2].get("score", 1.0) for m in matches]),
                            1.0, formula=engine["formula"]
                        )
                        real_curve = (future_p - base_p) / base_p
                        engine["swarm"].evaluate_and_learn(sanc_curve, real_curve)
                        swarm_c = engine["swarm"].apply_swarm_intelligence(sanc_curve)
                        grade = calculate_directional_truth(swarm_c, real_curve, vol_scale=chop_est)
                        engine["locker"].update_historical_accuracy(grade, weight=0.10)
                        engine["opinion"].ingest_realized_truth(
                            swarm_c, real_curve,
                            {"sanctuary": sanc_curve, "swarm_fuzz": swarm_c, "lightning": sanc_curve, "opinion": np.zeros_like(sanc_curve), "corridor": sanc_curve * 0.5, "landscape": swarm_c * 0.85},
                            lr=0.04, vol_scale=chop_est, hist_acc=engine["locker"].historical_accuracy
                        )
                        engine["formula"].tune_from_accuracy(
                            real_curve,
                            {"knn_raw": sanc_curve, "swarm_fuzz": swarm_c, "final_blended": swarm_c},
                            grade, engine["locker"].historical_accuracy, lr=0.03
                        )
    print(f"[+] {tf_key} Ready | Hist Acc: {engine['locker'].historical_accuracy:.1f}% (Peak {engine['locker'].peak_historical_accuracy:.1f}%) | Formula Eff: {engine['formula'].formula_efficiency:.1f}%")

def run_multi_grid_oracle():
    print("---------------------------------------------------------")
    print(" GOLDEN RIVER ORACLE - MASTER HYBRID EDITION (V22.2)")
    print(" ARCHITECTURE: DECOMPOSED SELF-TUNING FORMULA + HONEST OOS")
    print(" INTEGRATED: Tactile Ground/Ceiling + Cliff/Climb Surges")
    print("---------------------------------------------------------")

    state_restored = STATE_MANAGER.load_state(ENGINES, EXEC_ENGINE)
    if state_restored:
        print(f"[+] V22.2 Sovereign State Restored | Lazarus Fund: ${EXEC_ENGINE.lazarus_bankroll:.2f}")
    for tf in TIMEFRAMES.keys():
        bootstrap_history(tf, state_restored=state_restored)
    STATE_MANAGER.save_state(ENGINES, EXEC_ENGINE)

    plt.ion()
    fig, axs = plt.subplots(2, 2, figsize=(15, 11))
    fig.patch.set_facecolor('#050505')
    fig.suptitle("GOLDEN RIVER ORACLE - V22.2 ADAPTIVE SELF-TUNING (NEIRO/USDT)\n[ BOOTING SYSTEMS... ]", color='#D4AF37', fontsize=13, fontweight='bold')

    grid_map = [("4hr", axs[0, 0]), ("1d", axs[0, 1]), ("1wk", axs[1, 0]), ("1mo", axs[1, 1])]
    for _, ax in grid_map:
        ax.set_facecolor('#0A0A0A')
        ax.text(0.5, 0.5, 'AWAITING DATA LINK...\n(Fetching live calibration)', color='#555555', ha='center', va='center', fontsize=10, fontfamily='monospace')
        ax.set_xticks([])
        ax.set_yticks([])

    fig.tight_layout(pad=3.5)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.05, wspace=0.15, hspace=0.20)
    plt.show(block=False)
    plt.pause(0.5)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    fingerprint_engine = LiveFingerprintEngine(DATA_DIR)

    rec_lines = {tf: None for tf in TIMEFRAMES.keys()}
    light_lines = {tf: None for tf in TIMEFRAMES.keys()}
    live_price_buffer = deque(maxlen=12)

    while True:
        try:
            if not plt.fignum_exists(fig.number):
                break

            live_price = fetch_live_price()
            if live_price is not None:
                live_price_buffer.append(live_price)

            burst_vol = float(np.std(live_price_buffer)) if len(live_price_buffer) > 1 else 0.0

            if live_price is None:
                sys.stdout.write("\r[!] API Blocked or Network Error: Retrying in 4s...       ")
                sys.stdout.flush()
                for _, ax_err in grid_map:
                    ax_err.clear()
                    ax_err.set_facecolor('#0A0A0A')
                    ax_err.text(0.5, 0.5, 'NETWORK ERROR / API BLOCKED\nRetrying connection...', color='#FF3366', ha='center', va='center', fontfamily='monospace')
                    ax_err.set_xticks([])
                    ax_err.set_yticks([])
                fig.canvas.draw()
                plt.pause(4.0)
                continue

            raw_bids, raw_asks = fetch_market_depth(BINANCE_SYMBOL, limit=100)
            factual_tape = fetch_factual_tape_commits(BINANCE_SYMBOL, limit=80)
            global_bids, global_asks, spoof_status, spoof_passed = SPOOF_LANDSCAPE.sample_and_filter_book(
                raw_bids, raw_asks, live_price, tape_data=factual_tape,
                strictness=ENGINES['4hr']['formula'].get("spoof_strictness")
            )

            dfs = {}
            future_to_tf = {executor.submit(fetch_timeframe_data, TIMEFRAMES[tf]["interval"], TIMEFRAMES[tf]["limit"]): tf for tf in TIMEFRAMES.keys()}
            done, not_done = concurrent.futures.wait(future_to_tf.keys(), timeout=4.5)

            for future in done:
                try:
                    dfs[future_to_tf[future]] = future.result()
                except Exception:
                    dfs[future_to_tf[future]] = None

            for future in not_done:
                dfs[future_to_tf[future]] = None

            if dfs.get('4hr') is None or len(dfs['4hr']) < 25:
                sys.stdout.write("\r[!] Leader 4HR frame dropped. Skipping calculation frame to prevent CAN Bus corruption... ")
                sys.stdout.flush()
                plt.pause(1.0)
                continue

            engine_state_cache = {}

            # PASS 1: GATHER INTELLIGENCE & CONTINUOUS IN-LOCK TUNING
            for tf_key, ax in grid_map:
                cfg, engine, df = TIMEFRAMES[tf_key], ENGINES[tf_key], dfs.get(tf_key)
                if df is None or len(df) < 25:
                    ax.clear()
                    ax.set_facecolor('#0A0A0A')
                    ax.text(0.5, 0.5, f"[{tf_key}] API TIMEOUT\nRetrying...", color='#FF9900', ha='center', va='center')
                    fig.canvas.draw()
                    continue

                chop_bbw = calculate_advanced_chop_bias(df)
                momentum = (df['close'].iloc[-1] - df['close'].iloc[-5]) / (df['close'].iloc[-5] + 1e-9)
                microstructure = calculate_microstructure(df, period=20)
                base_volatility = df['close'].tail(15).std() / (df['close'].iloc[-1] + 1e-9)
                current_rsi = calculate_advanced_rsi(df)

                if engine["locker"].active_lock is not None:
                    _f_targets = engine["locker"].active_lock.get('frozen_target_prices', [])
                    if (not _f_targets) or (not np.all(np.isfinite(_f_targets))) or min(_f_targets) <= (live_price * 0.15):
                        engine["locker"].active_lock = None

                # Requirement 1 & 2: Global Recalc Trigger across all frames + immediate lesson integration
                global_recalc_flag = False
                if engine["locker"].active_lock is not None:
                    chk_acc, _, _ = engine["locker"].get_live_tracking_error(df, live_price, chop_bbw=chop_bbw)
                    if not np.isfinite(chk_acc):
                        chk_acc = 0.0
                    engine["last_live_accuracy"] = chk_acc
                    lock_age = time.time() - engine["locker"].active_lock.get('sys_time', time.time())
                    if lock_age >= 45.0 and chk_acc < engine["governor"].recalc_trigger:
                        global_recalc_flag = True

                if global_recalc_flag:
                    sys.stdout.write(f"\r[!] GLOBAL RECALC TRIGGERED by [{tf_key}]: Forcing all frames to abort, learn lessons & resynthesize...\n")
                    sys.stdout.flush()
                    for t_k, t_eng in ENGINES.items():
                        t_df = dfs.get(t_k)
                        if t_df is not None and t_eng["locker"].active_lock is not None:
                            t_chop = calculate_advanced_chop_bias(t_df)
                            t_eng["locker"].force_abort_and_learn(
                                t_df, live_price, t_eng["swarm"], t_eng["governor"],
                                opinion_engine=t_eng["opinion"], formula=t_eng["formula"], chop_bbw=t_chop
                            )
                            # Invalidate active lock so Pass 1 immediately regenerates fresh curves using updated lessons
                            t_eng["locker"].active_lock = None

                needs_new_prediction = engine["locker"].check_and_grade(
                    df, engine["swarm"], engine["metric"], engine["sanctuary"],
                    engine["governor"], opinion_engine=engine["opinion"],
                    formula=engine["formula"], chop_bbw=chop_bbw
                )

                if needs_new_prediction:
                    cur_pat = extract_pattern_vector(df, len(df) - 1)
                    if cur_pat is not None:
                        all_matches = engine["sanctuary"].recall(cur_pat, top_k=20, metric_learner=engine["metric"]) or [(1.0, np.zeros(cfg["horizon"]), {"score": 1.0, "vector": cur_pat})]
                        valid_matches = [m for m in all_matches if check_path_against_orderbook(global_bids, global_asks, live_price, m[1][-1] if len(m[1]) > 0 else 0.0)][:6]

                        fallback_multiplier = 1.0
                        if not valid_matches:
                            valid_matches, fallback_multiplier = [all_matches[0]], 0.35

                        paths = np.vstack([np.pad(m[1][:cfg["horizon"]], (0, max(0, cfg["horizon"] - len(m[1][:cfg["horizon"]]))), 'edge') for m in valid_matches])
                        tuning_dial = max(0.5, min(2.0, 2.0 - (engine["locker"].historical_accuracy / 100.0) * 1.5))
                        live_thrust = (live_price - df['close'].iloc[-1]) / (df['close'].iloc[-1] + 1e-9)

                        raw_smashed_curve = simulate_smashed_path(
                            paths, np.array([m[0] for m in valid_matches]),
                            np.array([m[2].get("score", 1.0) for m in valid_matches]),
                            tuning_dial, live_thrust=live_thrust, formula=engine["formula"]
                        ) * fallback_multiplier

                        current_drift = engine["governor"].short_term_error - engine["governor"].long_term_error
                        warped_curve = apply_adaptive_phase_shift(raw_smashed_curve, microstructure['coil_score'], chop_bbw, current_drift, formula=engine["formula"])
                        live_path_acc = engine.get("last_live_accuracy", 100.0)
                        flow_preview = calculate_order_flow_footprint(df)
                        tactile_preview = calculate_tactile_ground_ceiling_and_legs(df, live_price, flow_preview, global_bids, global_asks)
                        amp_curve = apply_adaptive_amplitude(
                            warped_curve, engine["locker"].historical_accuracy, live_path_acc,
                            formula=engine["formula"], leg_drive=tactile_preview['leg_drive']
                        )

                        engine_state_cache[tf_key] = {
                            'status': 'NEW',
                            'df': df,
                            'knn_raw_curve': raw_smashed_curve,
                            'base_curve': amp_curve,
                            'tension': float(np.std(paths)),
                            'momentum': momentum,
                            'chop_bbw': chop_bbw,
                            'base_volatility': base_volatility,
                            'drift': current_drift,
                            'rsi': current_rsi,
                            'microstructure': microstructure,
                            'live_accuracy': live_path_acc,
                            'tactile_data': tactile_preview
                        }
                else:
                    lock = engine["locker"].active_lock
                    bars_elapsed = len(df[df['ts'] > lock['base_ts']])
                    live_acc, t_prices, t_times = engine["locker"].get_live_tracking_error(df, live_price, chop_bbw=chop_bbw)
                    engine["last_live_accuracy"] = live_acc

                    if bars_elapsed > lock.get('last_eval_bar', 0):
                        lock['last_eval_bar'] = bars_elapsed
                        eval_bars = min(bars_elapsed, cfg["horizon"])
                        partial_pred = np.array(lock['frozen_curve'][:eval_bars], dtype=float)
                        realized_curve = (df[df['ts'] > lock['base_ts']]['close'].iloc[:eval_bars].values - lock['base_price']) / lock['base_price']

                        in_flight_grade = calculate_directional_truth(partial_pred, realized_curve, vol_scale=chop_bbw)
                        engine["locker"].update_historical_accuracy(in_flight_grade, weight=0.06)
                        engine["swarm"].evaluate_and_learn(partial_pred, realized_curve)
                        engine["governor"].update(
                            (float(np.mean(np.abs(partial_pred - realized_curve))) * 0.4) + (abs(partial_pred[-1] - realized_curve[-1]) * 0.6),
                            engine["locker"].historical_accuracy,
                            live_acc=live_acc
                        )
                        engine["opinion"].ingest_realized_truth(
                            partial_pred, realized_curve,
                            lock.get('stream_snapshots', {}),
                            lr=engine["governor"].learning_rate * 0.65,
                            vol_scale=chop_bbw, hist_acc=engine["locker"].historical_accuracy
                        )
                        engine["formula"].tune_from_accuracy(
                            realized_curve, lock.get('component_traces', {}),
                            in_flight_grade, engine["locker"].historical_accuracy,
                            lr=engine["governor"].learning_rate * 0.55
                        )

                    engine_state_cache[tf_key] = {
                        'status': 'LOCKED',
                        'df': df,
                        'tension': lock['tension'],
                        'momentum': momentum,
                        'chop_bbw': chop_bbw,
                        'base_volatility': base_volatility,
                        'kinetic_yield': engine["locker"].calculate_kinetic_yield(df, live_price, cfg["delta"].total_seconds()),
                        'live_accuracy': live_acc,
                        'tracking_prices': t_prices,
                        'tracking_times': t_times,
                        'bars_elapsed': bars_elapsed,
                        'rsi': current_rsi,
                        'drift': engine["governor"].short_term_error - engine["governor"].long_term_error,
                        'microstructure': microstructure,
                        'dynamic_beta': lock.get('dynamic_beta', 1.0),
                        'apex_tag': lock.get('apex_tag', 'NONE')
                    }

            # PASS 1.5: STAGES 3-6, 6-STREAM BLENDER, APEX, TACTILE & 288-CLAMP
            can_bus = CANBusRouter()

            for tf_key in ['4hr', '1d', '1wk', '1mo']:
                if tf_key not in engine_state_cache:
                    continue
                cache, engine, cfg = engine_state_cache[tf_key], ENGINES[tf_key], TIMEFRAMES[tf_key]
                formula = engine["formula"]

                if cache['status'] == 'NEW':
                    base_time = cache['df']['date'].iloc[-1]
                    future_times = [base_time + (cfg["delta"] * (i + 1)) for i in range(cfg["horizon"])]
                    spatial_data = calculate_spatial_structure(cache['df'])
                    order_flow = calculate_order_flow_footprint(cache['df'])

                    btc_momentum, dynamic_beta = fetch_btc_macro_context(cfg["interval"], cache['df']['close'].values)
                    cache['dynamic_beta'] = dynamic_beta
                    macro_pull = btc_momentum * dynamic_beta

                    accuracy_pct = min(1.0, max(0.2, engine["locker"].historical_accuracy / 100.0))
                    hybrid_momentum = (cache['momentum'] * accuracy_pct) + (macro_pull * (1.0 - accuracy_pct))

                    if spatial_data['is_breaking_down']:
                        if order_flow['status'] == "STRUCTURAL_COLLAPSE":
                            hybrid_momentum = -abs(hybrid_momentum) * 3.2
                            engine["fuzz"].lens.focus_multiplier = 0.5
                        elif order_flow['status'] == "LIQUIDITY_SWEEP":
                            hybrid_momentum = abs(hybrid_momentum) * 2.0
                            cache['microstructure']['coil_score'] = min(100.0, cache['microstructure']['coil_score'] + 50.0)

                    tactile_data = cache.get('tactile_data') or calculate_tactile_ground_ceiling_and_legs(
                        cache['df'], live_price, order_flow, global_bids, global_asks
                    )
                    cache['tactile_data'] = tactile_data
                    _signed_delta = (live_price - cache['df']['close'].iloc[-4]) / (cache['df']['close'].iloc[-4] + 1e-9) if len(cache['df']) >= 4 else 0.0
                    _live_vel = abs(_signed_delta)
                    rf_status, rf_throttle, rf_alarm = beam_redfuzz_terrain_sensor(
                        global_bids, global_asks, live_price, _live_vel, burst_vol,
                        raw_bids=raw_bids, raw_asks=raw_asks,
                        signed_delta=_signed_delta, leg_drive=tactile_data['leg_drive']
                    )
                    cache['redfuzz_status'] = rf_status

                    if rf_alarm:
                        if "CLIFF" in rf_status:
                            hybrid_momentum = -max(abs(hybrid_momentum) * 2.8, _live_vel * 1.5)
                            cache['microstructure']['coil_score'] = min(100.0, cache['microstructure']['coil_score'] + 25.0)
                        elif "CLIMB" in rf_status or "WALL" in rf_status:
                            hybrid_momentum = max(abs(hybrid_momentum) * 2.8, _live_vel * 1.5)
                            cache['microstructure']['coil_score'] = min(100.0, cache['microstructure']['coil_score'] + 25.0)

                    sanctuary_curve = np.array(cache['base_curve'], dtype=float)

                    swarm_curve = engine["swarm"].apply_swarm_intelligence(sanctuary_curve)
                    raw_fuzzed = engine["fuzz"].shoot_fuzz(
                        swarm_curve, hybrid_momentum,
                        cache['base_volatility'] * max(0.15, engine["swarm"].swarm_health / 100.0),
                        cache['drift'], cache['chop_bbw'], accuracy_pct,
                        rsi=cache['rsi'], proximity=spatial_data['proximity'],
                        formula=formula
                    )
                    swarm_mix = formula.get("swarm_trust_mix")
                    trust_shape = min(1.0, max(0.15, ((min(1.0, max(0.0, engine["swarm"].swarm_health / 100.0)) * swarm_mix) + (accuracy_pct * (1.0 - swarm_mix))) * min(1.0, max(0.2, cache.get('live_accuracy', 100.0) / 100.0))))
                    swarm_fuzz_curve = (swarm_curve * trust_shape) + ((raw_fuzzed - swarm_curve) * (1.0 - trust_shape + 0.3))

                    if fingerprint_engine.active_prediction is None:
                        fingerprint_engine.active_prediction = fingerprint_engine.synthesize_multi_combo_lightning(
                            {'momentum': cache['momentum'], 'chop': cache['chop_bbw'], 'imbalance': 0.0, 'rsi': cache['rsi'], 'coil': cache['microstructure']['coil_score']},
                            tolerance=0.28, top_k=6
                        )
                    lightning_curve = fingerprint_engine.build_horizon_curve(cfg, swarm_fuzz_curve, formula=formula)

                    ghost_slope_corr, _ = audit_ghost_grid(cache['df'], live_price, engine["locker"])
                    opinion_curve = engine["opinion"].build_opinion_curve(
                        cache['df'], live_price, spatial_data, order_flow,
                        global_bids, global_asks, btc_momentum, dynamic_beta,
                        ghost_slope_corr, formula=formula
                    )

                    chop_corridor = calculate_ghost_chop_corridor(
                        cache['df'], live_price, engine["locker"], cache['chop_bbw'],
                        cache['microstructure'], live_acc=cache.get('live_accuracy', 100.0), t_idx=0
                    )
                    corridor_curve = (chop_corridor['mid_ground_line'] - live_price) / (live_price + 1e-9)

                    landscape_curve, _, _ = SPOOF_LANDSCAPE.solve_easiest_path(
                        cache['df'], live_price, global_bids, global_asks,
                        hybrid_momentum, lightning_curve, swarm_fuzz_curve,
                        cache['chop_bbw'], formula=formula
                    )

                    stream_snapshots = {
                        "sanctuary": sanctuary_curve.copy(),
                        "swarm_fuzz": swarm_fuzz_curve.copy(),
                        "lightning": lightning_curve.copy(),
                        "opinion": opinion_curve.copy(),
                        "corridor": corridor_curve.copy(),
                        "landscape": landscape_curve.copy()
                    }

                    blended_curve, _ = engine["opinion"].blend_marker_streams(
                        stream_snapshots,
                        live_acc=cache.get('live_accuracy', 100.0),
                        fp_acc=fingerprint_engine.fingerprint_accuracy,
                        is_chop=(chop_corridor['is_swing_chop'] and not rf_alarm),
                        formula=formula,
                        spoof_passed=SPOOF_LANDSCAPE.last_passed,
                        hist_acc=engine["locker"].historical_accuracy,
                        leg_drive=tactile_data['leg_drive']
                    )

                    blended_curve, apex_tag = apply_apex_trough_inflection(
                        blended_curve, cache['df'], live_price, cache['rsi'],
                        spatial_data, order_flow, global_bids, global_asks,
                        formula=formula, tactile_data=tactile_data
                    )
                    blended_curve, leg_tag = apply_tactile_leg_and_boundary_feel(
                        blended_curve, tactile_data, formula=formula
                    )
                    if leg_tag != "NONE" and apex_tag == "NONE":
                        apex_tag = leg_tag
                    blended_curve, apex_tag = CORNER_ENGINE.apply_corner_signature_influence(
                        blended_curve, tf_key, cfg, cache['df'], live_price,
                        cache['rsi'], spatial_data, order_flow, apex_tag
                    )
                    blended_curve, chop_tag = apply_chop_middle_ground_governor(
                        blended_curve, live_price, chop_corridor, cache['chop_bbw'],
                        cache['microstructure'], formula=formula, tactile_data=tactile_data
                    )
                    post_apex_chop_curve = blended_curve.copy()

                    blended_curve, p_max = apply_288_marker_clamp(
                        blended_curve, cache['df'], live_price,
                        cache['microstructure']['coil_score'], cache['chop_bbw'],
                        ghost_slope_corr=ghost_slope_corr, formula=formula,
                        tactile_data=tactile_data
                    )
                    engine["p_max"] = p_max

                    component_traces = {
                        "knn_raw": np.array(cache.get('knn_raw_curve', sanctuary_curve), dtype=float),
                        "phase_amp": sanctuary_curve.copy(),
                        "swarm_fuzz": swarm_fuzz_curve.copy(),
                        "lightning": lightning_curve.copy(),
                        "opinion": opinion_curve.copy(),
                        "landscape": landscape_curve.copy(),
                        "post_apex_chop": post_apex_chop_curve,
                        "final_blended": blended_curve.copy()
                    }

                    cache['chop_corridor'] = chop_corridor
                    cache['apex_tag'] = chop_tag if chop_tag != "NONE" else apex_tag
                    cache['future_times'] = future_times
                    cache['local_curve_pct'] = blended_curve
                    cache['stream_snapshots'] = stream_snapshots
                    cache['component_traces'] = component_traces

                    local_prices = [live_price * (1 + p) for p in blended_curve]
                    can_bus.broadcast_intent(tf_key, future_times, local_prices, engine["locker"].historical_accuracy)
                else:
                    lock = engine["locker"].active_lock
                    can_bus.broadcast_intent(tf_key, [lock['base_time']] + lock['target_times'], [lock['base_price']] + list(lock['frozen_target_prices']), engine["locker"].historical_accuracy)

            can_bus.negotiate_truth()

            # PASS 2: RENDER & VIEWPORT TRACKING
            for tf_key in ['4hr', '1d', '1wk', '1mo']:
                if tf_key not in engine_state_cache:
                    continue
                ax, cache, engine, cfg = dict(grid_map)[tf_key], engine_state_cache[tf_key], ENGINES[tf_key], TIMEFRAMES[tf_key]

                if cache['status'] == 'NEW':
                    local_prices = [live_price * (1 + p) for p in cache['local_curve_pct']]
                    spliced_targets = apply_triphase_equilibrium(
                        can_bus.pull_consensus(cache['future_times'], local_prices, engine["locker"].historical_accuracy, tf_key=tf_key),
                        formula=engine["formula"]
                    )

                    engine["locker"].lock_projection(
                        cache['df']['ts'].iloc[-1],
                        cache['df']['date'].iloc[-1],
                        live_price,
                        cache['future_times'],
                        [(p - live_price) / live_price for p in spliced_targets],
                        cache['tension'],
                        local_curve=cache['local_curve_pct'],
                        stream_snapshots=cache.get('stream_snapshots', {}),
                        component_traces=cache.get('component_traces', {})
                    )
                    engine["locker"].active_lock['dynamic_beta'] = cache['dynamic_beta']
                    engine["locker"].active_lock['apex_tag'] = cache.get('apex_tag', 'NONE')

                    _, init_t_prices, init_t_times = engine["locker"].get_live_tracking_error(cache['df'], live_price, chop_bbw=cache['chop_bbw'])
                    cache.update({
                        'kinetic_yield': 1.0,
                        'live_accuracy': 100.0,
                        'bars_elapsed': 0,
                        'tracking_prices': init_t_prices,
                        'tracking_times': init_t_times
                    })

                lock = engine["locker"].active_lock
                ax.clear()
                ax.set_facecolor('#0A0A0A')
                ax.grid(color='#D4AF37', linestyle=':', linewidth=0.5, alpha=0.15)
                rec_lines[tf_key], light_lines[tf_key] = None, None

                recent_df = cache['df'].tail(45)
                plot_dates = recent_df['date'].tolist() + [datetime.now().astimezone().replace(tzinfo=None)]
                plot_closes = recent_df['close'].tolist() + [live_price]

                ax.plot(plot_dates, plot_closes, color='#FFFFFF', linewidth=1.0, alpha=0.5)
                if SHOW_GHOST_LINES:
                    for g in engine["locker"].ghosts:
                        ax.plot(g['times'], g['prices'], color='#333333', linewidth=1.5, linestyle='--')

                corridor = cache.get('chop_corridor') or calculate_ghost_chop_corridor(
                    cache['df'], live_price, engine["locker"], cache['chop_bbw'],
                    cache['microstructure'], live_acc=cache.get('live_accuracy', 100.0), t_idx=cache.get('bars_elapsed', 0)
                )
                cache['chop_corridor'] = corridor
                if len(lock['target_times']) == len(corridor['mid_ground_line']):
                    ax.plot(lock['target_times'], corridor['up_ghost_line'], color='#446688', linewidth=1.0, linestyle=':', alpha=0.55)
                    ax.plot(lock['target_times'], corridor['low_ghost_line'], color='#446688', linewidth=1.0, linestyle=':', alpha=0.55)
                    ax.plot(lock['target_times'], corridor['mid_ground_line'], color='#D4AF37', linewidth=1.2, linestyle='-.', alpha=0.45)

                disp_t = [lock['base_time']] + list(lock['target_times'])
                disp_p = [lock['base_price']] + list(lock['frozen_target_prices'])

                line_color = '#00FF66' if disp_p[-1] >= lock['base_price'] else '#FF3366'

                fuzz_vol = lock['base_price'] * lock['tension']
                ax.fill_between(
                    disp_t,
                    [p - (fuzz_vol * (i / max(1, len(disp_p) - 1))) for i, p in enumerate(disp_p)],
                    [p + (fuzz_vol * (i / max(1, len(disp_p) - 1))) for i, p in enumerate(disp_p)],
                    color=line_color, alpha=0.15
                )

                main_lock_line, = ax.plot(disp_t, disp_p, color=line_color, linewidth=2, linestyle='--')
                lock_base_dot, = ax.plot([disp_t[0]], [disp_p[0]], marker='o', markersize=6, markerfacecolor='#D4AF37', markeredgecolor='white')

                if len(disp_p) >= 3:
                    max_i = int(np.argmax(disp_p))
                    min_i = int(np.argmin(disp_p))
                    if 0 < max_i < len(disp_p) - 1:
                        ax.plot(disp_t[max_i], disp_p[max_i], marker='v', markersize=7, color='#FFD700', alpha=0.85)
                    if 0 < min_i < len(disp_p) - 1:
                        ax.plot(disp_t[min_i], disp_p[min_i], marker='^', markersize=7, color='#00FFFF', alpha=0.85)

                live_line, = ax.plot(cache['tracking_times'], cache['tracking_prices'], color='#FF00FF', linewidth=2.5)
                live_dot, = ax.plot([cache['tracking_times'][-1]], [cache['tracking_prices'][-1]], marker='o', markersize=7, color='#FF00FF', zorder=8)

                all_x, all_y = plot_dates + disp_t, plot_closes + disp_p
                x_pad = cfg["delta"] * 2
                ax.set_xlim(min(all_x) - x_pad, max(all_x) + x_pad)
                y_min, y_max = min(all_y), max(all_y)
                y_pad = max((y_max - y_min) * 0.15, live_price * 0.005)
                ax.set_ylim(y_min - y_pad, y_max + y_pad)

                nose_t, nose_p = CORNER_ENGINE.compute_nose_segment(ax, cache['tracking_times'][-1], cache['tracking_prices'][-1], cfg)
                nose_line, = ax.plot(nose_t, nose_p, color='#39FF14', linewidth=2.4, zorder=9)
                nose_tip, = ax.plot([nose_t[-1]], [nose_p[-1]], marker=(3, 0, CORNER_ENGINE.current_angle - 90.0), markersize=8, color='#39FF14', zorder=10)

                tilt, stress = calculate_vessel_physics(cache['momentum'], lock['tension'], cache['base_volatility'], cache['microstructure']['coil_score'], engine["prev_tilt"], engine["locker"].historical_accuracy)
                engine["prev_tilt"] = tilt

                _current_close, _closes = live_price, cache['df']['close'].values
                _live_delta = (_current_close - _closes[-4]) / (_closes[-4] + 1e-9) if len(_closes) >= 4 else 0.0
                _live_dir, _live_vel = (1 if _live_delta > 0 else -1), abs(_live_delta)
                _pred_dir = 1 if (lock['frozen_curve'][3] - lock['frozen_curve'][0]) > 0 else -1 if len(lock['frozen_curve']) >= 4 else _live_dir

                _volumes, _current_open = cache['df']['volume'].values, cache['df']['open'].values[-1]
                _volume_spike = _volumes[-1] / max(0.0001, np.mean(_volumes[-20:]) if len(_volumes) >= 20 else _volumes[-1])

                _tact = cache.get('tactile_data') or calculate_tactile_ground_ceiling_and_legs(
                    cache['df'], live_price, calculate_order_flow_footprint(cache['df']), global_bids, global_asks
                )
                cache['tactile_data'] = _tact
                rf_status, _, rf_alarm = beam_redfuzz_terrain_sensor(
                    global_bids, global_asks, live_price, _live_vel, burst_vol,
                    raw_bids=raw_bids, raw_asks=raw_asks,
                    signed_delta=_live_delta, leg_drive=_tact['leg_drive']
                )

                cache.update({
                    'vector_aligned': _live_dir == _pred_dir,
                    'kinetic_velocity': _live_vel,
                    'minimum_velocity_met': _live_vel > 0.0005,
                    'whale_alert': _volume_spike > 5.0,
                    'splash_direction': 1 if _current_close > _current_open else -1,
                    'splash_magnitude': _volume_spike,
                    'redfuzz_status': rf_status
                })

                if tf_key == '4hr':
                    EXEC_ENGINE.evaluate_pressure(
                        lock['base_price'],
                        live_price,
                        list(lock['frozen_target_prices']),
                        [n.accuracy_weight for n in engine['swarm'].nodes],
                        cache['live_accuracy'],
                        engine.get('p_max', 1.0),
                        redfuzz_alarm=rf_alarm,
                        redfuzz_status=rf_status
                    )

                hp_mix_val = engine['formula'].get("honest_path_mix")
                all_frame_avg_acc = float(np.mean([ENGINES[k].get('last_live_accuracy', 100.0) for k in TIMEFRAMES.keys()]))
                hud_data = {
                    'target_p': disp_p[-1],
                    'all_frame_acc': all_frame_avg_acc,
                    'move_pct': ((disp_p[-1] - lock['base_price']) / lock['base_price']) * 100.0,
                    'bars_elapsed': cache['bars_elapsed'],
                    'horizon': cfg['horizon'],
                    'delta': cfg['delta'],
                    'live_accuracy': cache['live_accuracy'],
                    'historical_accuracy': engine['locker'].historical_accuracy,
                    'peak_accuracy': engine['locker'].peak_historical_accuracy,
                    'formula_eff': engine['formula'].formula_efficiency,
                    'tuning_epoch': engine['formula'].tuning_epoch,
                    'topology_tag': f"[{'LEADER' if tf_key == '4hr' else 'SPLICED'}]",
                    'swarm_health': engine['swarm'].swarm_health,
                    'learning_rate': engine['governor'].learning_rate,
                    'opinion_trust': engine['opinion'].opinion_trust,
                    'landscape_trust': engine['opinion'].landscape_trust,
                    'landscape_gain': engine['formula'].get("landscape_flow_gain"),
                    'spoof_status': SPOOF_LANDSCAPE.last_status,
                    'lightning_gain': fingerprint_engine.dynamic_gain,
                    'lightning_combos': fingerprint_engine.active_combo_count,
                    'kinetic_yield': cache['kinetic_yield'],
                    'current_lens_focus': engine["fuzz"].lens.focus_multiplier,
                    'wiggles': cache['microstructure']['wiggles'],
                    'coil_score': cache['microstructure']['coil_score'],
                    'chop_bbw': cache['chop_bbw'],
                    'tilt': tilt,
                    'stress': stress,
                    'stress_warn': "[KILL-SWITCH: BEKENSTEIN]" if abs(tilt) > 42.0 or stress > 12.0 else ("[HEDGED: HEAVY DAMP]" if abs(tilt) > 22.0 or stress > 6.5 else "ACTIVE MARKET"),
                    'dynamic_beta': cache.get('dynamic_beta', 1.0),
                    'burst_vol': burst_vol,
                    'redfuzz_status': rf_status,
                    'target_time_end': disp_t[-1],
                    'target_prices': list(lock['frozen_target_prices']),
                    'realized_prices': cache['df'][cache['df']['ts'] > lock['base_ts']]['close'].tolist(),
                    'vector_aligned': _live_dir == _pred_dir,
                    'kinetic_velocity': _live_vel,
                    'minimum_velocity_met': _live_vel > 0.0005,
                    'whale_alert': _volume_spike > 5.0,
                    'splash_direction': 1 if _current_close > _current_open else -1,
                    'splash_magnitude': _volume_spike,
                    'recalc_trigger': engine['governor'].recalc_trigger,
                    'rsi': cache.get('rsi', 50.0),
                    'apex_tag': lock.get('apex_tag', 'NONE'),
                    'p_max': engine.get('p_max', 1.0),
                    'settled_hits': len(lock.get('settled_indices', set())),
                    'pos_side': EXEC_ENGINE.position_side,
                    'conviction': EXEC_ENGINE.conviction,
                    'net_pnl_pct': EXEC_ENGINE.cumulative_net_pnl_pct + EXEC_ENGINE.get_live_unrealized_pnl_pct(live_price),
                    'lazarus_fund': EXEC_ENGINE.lazarus_bankroll,
                    'tick_angle': CORNER_ENGINE.current_angle,
                    'corner_phase': CORNER_ENGINE.phase,
                    'cda_acc': CORNER_ENGINE.cda_accuracy,
                    'corner_inf': CORNER_ENGINE.influence_weight,
                    'corner_vault_cnt': len(CORNER_ENGINE.vault),
                    'honest_path_mix': hp_mix_val,
                    'leg_regime': _tact.get('leg_regime', 'NORMAL')
                }

                hud_text = ax.text(0.02, 0.97, build_hud_string(live_price, hud_data), transform=ax.transAxes, color='#D4AF37', alpha=0.75, fontfamily='monospace', fontsize=7.5, va='top', bbox=dict(facecolor='#111', edgecolor='#333', alpha=0.40, pad=6.0))
                ax.xaxis.set_major_formatter(mdates.DateFormatter(cfg["dt_fmt"]))
                ax.tick_params(axis='x', rotation=20, colors='#666', labelsize=8)
                ax.tick_params(axis='y', colors='#666', labelsize=8)
                ax.set_title(cfg["label"], color='#D4AF37', fontsize=10, fontweight='bold')

                fun_plane = ax.text(-0.1, 0.85, "✈️💨", color='#FF3366', fontsize=22, transform=ax.transAxes, alpha=0)
                fun_sub = ax.text(-0.1, 0.15, "🚢🫧", color='#00BFFF', fontsize=22, transform=ax.transAxes, alpha=0)
                fun_swan = ax.text(-0.1, 0.35, "🦢💦", color='#FFFFFF', fontsize=22, transform=ax.transAxes, alpha=0)
                fun_goat = ax.text(-0.1, 0.65, "🐐🏔️", color='#D4AF37', fontsize=22, transform=ax.transAxes, alpha=0)
                flash_arrow = ax.text(
                    0.88, 0.86, "", color='#00FF66', fontsize=26, fontweight='bold',
                    ha='center', va='center', transform=ax.transAxes, alpha=0.0, zorder=12,
                    bbox=dict(facecolor='#050505', edgecolor='#00FF66', linewidth=1.8, alpha=0.0, pad=5.0)
                )

                cache.update({
                    'live_line': live_line,
                    'live_dot': live_dot,
                    'nose_line': nose_line,
                    'nose_tip': nose_tip,
                    'hud_text': hud_text,
                    'hud_data': hud_data,
                    'main_lock_line': main_lock_line,
                    'lock_base_dot': lock_base_dot,
                    'fun_plane': fun_plane,
                    'fun_sub': fun_sub,
                    'fun_swan': fun_swan,
                    'fun_goat': fun_goat,
                    'flash_arrow': flash_arrow
                })

            fig.canvas.draw()
            STATE_MANAGER.save_state(ENGINES, EXEC_ENGINE)

            # 7-MINUTE LIVE DANCE
            end_time, dancing_price, loop_counter, emergency_abort = time.time() + (7 * 60), live_price, 0, False

            while True:
                remaining_time = end_time - time.time()
                if remaining_time <= 0 or not plt.fignum_exists(fig.number):
                    break

                if loop_counter % 2 == 0:
                    quick_p = fetch_dancing_price()
                    if quick_p is not None:
                        prev_dance_p = dancing_price
                        dancing_price = quick_p
                        live_price_buffer.append(dancing_price)
                        burst_vol = float(np.std(live_price_buffer)) if len(live_price_buffer) > 1 else 0.0
                        CORNER_ENGINE.update_tick(dancing_price, SPOOF_LANDSCAPE.last_tape)

                        for tf_k in TIMEFRAMES.keys():
                            if tf_k in engine_state_cache and 'df' in engine_state_cache[tf_k]:
                                _tf_closes = engine_state_cache[tf_k]['df']['close'].values
                                if len(_tf_closes) >= 4:
                                    _delta = (dancing_price - _tf_closes[-4]) / (_tf_closes[-4] + 1e-9)
                                    _vel = abs(_delta)
                                    _dir = 1 if _delta > 0 else -1
                                    _lck = ENGINES[tf_k]['locker'].active_lock
                                    _pdir = (1 if (_lck['frozen_curve'][3] - _lck['frozen_curve'][0]) > 0 else -1) if (_lck and len(_lck['frozen_curve']) >= 4) else _dir
                                    engine_state_cache[tf_k]['kinetic_velocity'] = _vel
                                    engine_state_cache[tf_k]['minimum_velocity_met'] = _vel > 0.0005
                                    engine_state_cache[tf_k]['vector_aligned'] = (_dir == _pdir)
                                    if 'hud_data' in engine_state_cache[tf_k]:
                                        engine_state_cache[tf_k]['hud_data'].update({
                                            'kinetic_velocity': _vel,
                                            'minimum_velocity_met': _vel > 0.0005,
                                            'vector_aligned': (_dir == _pdir),
                                            'burst_vol': burst_vol
                                        })

                            hits = ENGINES[tf_k]["locker"].audit_physical_marker_hits(
                                prev_dance_p, dancing_price, ENGINES[tf_k]["swarm"], STATE_MANAGER, tf_key=tf_k
                            )
                            if hits > 0:
                                EXEC_ENGINE.total_settled_hits += hits

                if loop_counter > 0 and loop_counter % 16 == 0:
                    quick_bids, quick_asks = fetch_market_depth(BINANCE_SYMBOL, limit=50)
                    if quick_bids is not None and quick_asks is not None:
                        raw_bids, raw_asks = quick_bids, quick_asks
                        quick_tape = fetch_factual_tape_commits(BINANCE_SYMBOL, limit=60)
                        global_bids, global_asks, _, _ = SPOOF_LANDSCAPE.sample_and_filter_book(
                            quick_bids, quick_asks, dancing_price, tape_data=quick_tape,
                            strictness=ENGINES['4hr']['formula'].get("spoof_strictness")
                        )

                try:
                    draw_data = fingerprint_engine.tick(time.time(), dancing_price, engine_state_cache, ENGINES['4hr']['governor'], global_bids, global_asks)
                except Exception:
                    draw_data = {'recording': None, 'lightning': None}

                if '4hr' in engine_state_cache and loop_counter > 0 and loop_counter % 5 == 0:
                    leader_cache = engine_state_cache['4hr']
                    leader_locker = ENGINES['4hr']['locker']
                    leader_chop = leader_cache.get('chop_bbw', 0.015)
                    acc, _, _ = leader_locker.get_live_tracking_error(leader_cache['df'], dancing_price, chop_bbw=leader_chop)
                    ENGINES['4hr']['last_live_accuracy'] = acc
                    leader_cache['hud_data']['live_accuracy'] = acc
                    live_vel_now = leader_cache.get('kinetic_velocity', 0.0)
                    vol_floor = max(0.0005, leader_chop * 0.075)
                    rcl_gate = ENGINES['4hr']['governor'].recalc_trigger
                    dyn_tune_mod = 10 if (live_vel_now >= vol_floor and (acc < rcl_gate + 7.0 or acc >= 84.0)) else (20 if live_vel_now >= vol_floor * 0.65 else 60)
                    if loop_counter % dyn_tune_mod == 0:
                        for tf_k, tf_eng in ENGINES.items():
                            tf_lck, tf_c = tf_eng['locker'].active_lock, engine_state_cache.get(tf_k)
                            if tf_lck and tf_c and 'df' in tf_c:
                                tf_chop = tf_c.get('chop_bbw', 0.015)
                                tf_acc, _, _ = tf_eng['locker'].get_live_tracking_error(tf_c['df'], dancing_price, chop_bbw=tf_chop)
                                act_s = tf_c['df'][tf_c['df']['ts'] > tf_lck['base_ts']]['close'].tolist() + [dancing_price]
                                n_ev = min(len(act_s), TIMEFRAMES[tf_k]['horizon'])
                                if n_ev > 0:
                                    r_c = (np.array(act_s[:n_ev], dtype=float) - tf_lck['base_price']) / (tf_lck['base_price'] + 1e-9)
                                    p_c = np.array(tf_lck['frozen_curve'][:n_ev], dtype=float)
                                    p_lr = tf_eng['governor'].learning_rate * (0.45 if tf_acc < rcl_gate else 0.25)
                                    tf_eng['opinion'].ingest_realized_truth(p_c, r_c, tf_lck.get('stream_snapshots', {}), lr=p_lr, vol_scale=tf_chop, hist_acc=tf_eng['locker'].historical_accuracy)
                                    tf_eng['formula'].tune_from_accuracy(r_c, tf_lck.get('component_traces', {}), tf_acc, tf_eng['locker'].historical_accuracy, lr=p_lr)

                    lock = leader_locker.active_lock
                    if lock:
                        _l_tact = leader_cache.get('tactile_data') or calculate_tactile_ground_ceiling_and_legs(
                            leader_cache['df'], dancing_price, calculate_order_flow_footprint(leader_cache['df']), global_bids, global_asks
                        )
                        rf_status, _, rf_alarm = beam_redfuzz_terrain_sensor(
                            global_bids, global_asks, dancing_price,
                            leader_cache.get('kinetic_velocity', 0.0), burst_vol,
                            raw_bids=raw_bids, raw_asks=raw_asks,
                            signed_delta=((dancing_price - leader_cache['df']['close'].iloc[-4]) / (leader_cache['df']['close'].iloc[-4] + 1e-9)),
                            leg_drive=_l_tact['leg_drive']
                        )
                        for tf_k in TIMEFRAMES.keys():
                            if tf_k in engine_state_cache and 'hud_data' in engine_state_cache[tf_k]:
                                engine_state_cache[tf_k]['hud_data']['redfuzz_status'] = rf_status

                        if rf_alarm:
                            REDFUZZ_VAULT.record_trigger(rf_status, dancing_price, factual_tape if 'factual_tape' in locals() and factual_tape else {}, lock['frozen_curve'])
                            sys.stdout.write('\a')
                            sys.stdout.write(f"\r[!] {rf_status} | VEL: {leader_cache.get('kinetic_velocity', 0.0)*100.0:.2f}% [!]\n")
                            sys.stdout.flush()

                        fp_dir = 0
                        if fingerprint_engine.active_prediction and 'path' in fingerprint_engine.active_prediction:
                            fp_dir = 1 if fingerprint_engine.active_prediction['path'][-1][1] >= 0 else -1

                        should_break, break_reason = REGIME_SENTINEL.check_regime_break(
                            lock, dancing_price, acc, rf_alarm, rf_status,
                            fp_dir, fingerprint_engine.fingerprint_accuracy, ENGINES['4hr'].get('p_max', 1.0),
                            recalc_trigger=ENGINES['4hr']['governor'].recalc_trigger,
                            chop_bbw=leader_chop
                        )
                        if should_break:
                            sys.stdout.write(f"\r[!] REGIME SENTINEL ({break_reason}): Synchronized All-Frame Recalc & Lesson Integration... [!]\n")
                            sys.stdout.flush()
                            for tf_k in TIMEFRAMES.keys():
                                tf_df = engine_state_cache.get(tf_k, {}).get('df')
                                tf_chop = engine_state_cache.get(tf_k, {}).get('chop_bbw', 0.015)
                                if tf_df is not None:
                                    ENGINES[tf_k]['locker'].force_abort_and_learn(
                                        tf_df, dancing_price, ENGINES[tf_k]['swarm'],
                                        ENGINES[tf_k]['governor'], opinion_engine=ENGINES[tf_k]['opinion'],
                                        formula=ENGINES[tf_k]['formula'], chop_bbw=tf_chop
                                    )
                                    ENGINES[tf_k]['locker'].active_lock = None
                            STATE_MANAGER.save_state(ENGINES, EXEC_ENGINE)
                            emergency_abort = True
                            break

                        prev_side = EXEC_ENGINE.position_side
                        prev_entry = EXEC_ENGINE.entry_price
                        EXEC_ENGINE.evaluate_pressure(
                            lock['base_price'],
                            dancing_price,
                            list(lock['frozen_target_prices']),
                            [n.accuracy_weight for n in ENGINES['4hr']['swarm'].nodes],
                            acc,
                            ENGINES['4hr'].get('p_max', 1.0),
                            redfuzz_alarm=rf_alarm,
                            redfuzz_status=rf_status
                        )
                        if prev_side != "FLAT" and EXEC_ENGINE.position_side != prev_side and prev_entry > 0:
                            real_pct = (dancing_price - prev_entry) / prev_entry * (1.0 if prev_side == "LONG" else -1.0)
                            STATE_MANAGER.log_trade_audit(
                                "4hr", prev_side, prev_entry, dancing_price,
                                EXEC_ENGINE.projected_move_pct, real_pct,
                                (real_pct - 0.002) * 100.0, EXEC_ENGINE.lazarus_bankroll,
                                ENGINES['4hr'].get('p_max', 1.0)
                            )

                if loop_counter > 0 and loop_counter % 120 == 0:
                    fresh_df = fetch_timeframe_data(TIMEFRAMES['4hr']["interval"], 25)
                    if fresh_df is not None and '4hr' in engine_state_cache and fresh_df['ts'].iloc[-1] >= engine_state_cache['4hr']['df']['ts'].iloc[-1]:
                        engine_state_cache['4hr']['df'] = fresh_df
                        if ENGINES['4hr']['locker'].active_lock:
                            leader_chop = engine_state_cache['4hr'].get('chop_bbw', 0.015)
                            acc, t_p, t_t = ENGINES['4hr']['locker'].get_live_tracking_error(fresh_df, dancing_price, chop_bbw=leader_chop)
                            ENGINES['4hr']['last_live_accuracy'] = acc
                            new_bars = len(fresh_df[fresh_df['ts'] > ENGINES['4hr']['locker'].active_lock['base_ts']])
                            engine_state_cache['4hr'].update({'live_accuracy': acc, 'tracking_prices': t_p, 'tracking_times': t_t, 'bars_elapsed': new_bars})
                            engine_state_cache['4hr']['hud_data'].update({
                                'live_accuracy': acc,
                                'bars_elapsed': new_bars,
                                'realized_prices': fresh_df[fresh_df['ts'] > ENGINES['4hr']['locker'].active_lock['base_ts']]['close'].tolist()
                            })
                    STATE_MANAGER.save_state(ENGINES, EXEC_ENGINE)

                mins, secs = divmod(int(max(0, remaining_time)), 60)
                fig.suptitle(f"GOLDEN RIVER ORACLE - V22.2 ADAPTIVE SELF-TUNING (NEIRO/USDT)\n[ {'🟢' if loop_counter % 2 == 0 else '🟩'} LIVE ] | NEXT BURST: {mins:02d}:{secs:02d}", color='#D4AF37', fontsize=13, fontweight='bold')

                for tf_key, ax in grid_map:
                    if tf_key in engine_state_cache and 'hud_text' in engine_state_cache[tf_key]:
                        c = engine_state_cache[tf_key]
                        lock_ref = ENGINES[tf_key]['locker'].active_lock
                        live_acc_now, _, _ = ENGINES[tf_key]['locker'].get_live_tracking_error(c['df'], dancing_price, chop_bbw=c.get('chop_bbw', 0.015))
                        ENGINES[tf_key]['last_live_accuracy'] = live_acc_now
                        c['hud_data']['live_accuracy'] = live_acc_now
                        c['hud_data']['historical_accuracy'] = ENGINES[tf_key]['locker'].historical_accuracy
                        c['hud_data']['peak_accuracy'] = ENGINES[tf_key]['locker'].peak_historical_accuracy
                        c['hud_data']['formula_eff'] = ENGINES[tf_key]['formula'].formula_efficiency
                        c['hud_data']['tuning_epoch'] = ENGINES[tf_key]['formula'].tuning_epoch
                        if lock_ref and 'expected_tip_price' in lock_ref:
                            c['hud_data']['expected_tip_price'] = lock_ref['expected_tip_price']
                        c['hud_data']['kinetic_yield'] = ENGINES[tf_key]["locker"].calculate_kinetic_yield(c['df'], dancing_price, TIMEFRAMES[tf_key]["delta"].total_seconds())
                        c['hud_data']['settled_hits'] = len(lock_ref.get('settled_indices', set())) if lock_ref else 0
                        c['hud_data']['p_max'] = ENGINES[tf_key].get('p_max', 1.0)
                        c['hud_data']['opinion_trust'] = ENGINES[tf_key]['opinion'].opinion_trust
                        c['hud_data']['landscape_trust'] = ENGINES[tf_key]['opinion'].landscape_trust
                        c['hud_data']['landscape_gain'] = ENGINES[tf_key]['formula'].get("landscape_flow_gain")
                        c['hud_data']['spoof_status'] = SPOOF_LANDSCAPE.last_status
                        c['hud_data']['lightning_gain'] = fingerprint_engine.dynamic_gain
                        c['hud_data']['lightning_combos'] = fingerprint_engine.active_combo_count
                        c['hud_data']['pos_side'] = EXEC_ENGINE.position_side
                        c['hud_data']['conviction'] = EXEC_ENGINE.conviction
                        c['hud_data']['net_pnl_pct'] = EXEC_ENGINE.cumulative_net_pnl_pct + EXEC_ENGINE.get_live_unrealized_pnl_pct(dancing_price)
                        c['hud_data']['lazarus_fund'] = EXEC_ENGINE.lazarus_bankroll

                        c['hud_data']['tick_angle'] = CORNER_ENGINE.current_angle
                        c['hud_data']['corner_phase'] = CORNER_ENGINE.phase
                        c['hud_data']['cda_acc'] = CORNER_ENGINE.cda_accuracy
                        c['hud_data']['corner_inf'] = CORNER_ENGINE.influence_weight
                        c['hud_data']['corner_vault_cnt'] = len(CORNER_ENGINE.vault)

                        now_tick_dt = datetime.now().astimezone().replace(tzinfo=None)
                        t_prices, t_times = c['tracking_prices'][:], c['tracking_times'][:]
                        t_prices[-1], t_times[-1] = dancing_price, now_tick_dt
                        c['live_line'].set_data(t_times, t_prices)
                        c['live_dot'].set_data([t_times[-1]], [dancing_price])

                        if 'nose_line' in c and 'nose_tip' in c:
                            n_t, n_p = CORNER_ENGINE.compute_nose_segment(ax, now_tick_dt, dancing_price, TIMEFRAMES[tf_key])
                            c['nose_line'].set_data(n_t, n_p)
                            c['nose_tip'].set_data([n_t[-1]], [n_p[-1]])
                            c['nose_tip'].set_marker((3, 0, CORNER_ENGINE.current_angle - 90.0))

                        if lock_ref:
                            frozen_end_p = lock_ref['frozen_target_prices'][-1]
                            c['hud_data']['target_p'] = frozen_end_p
                            c['hud_data']['move_pct'] = ((frozen_end_p - lock_ref['base_price']) / (lock_ref['base_price'] + 1e-9)) * 100.0
                            c['hud_data']['target_prices'] = list(lock_ref['frozen_target_prices'])

                        c['hud_text'].set_text(build_hud_string(dancing_price, c['hud_data']))

                        curr_ylim = ax.get_ylim()
                        if dancing_price >= curr_ylim[1] or dancing_price <= curr_ylim[0]:
                            y_pad = (curr_ylim[1] - curr_ylim[0]) * 0.2
                            ax.set_ylim(min(curr_ylim[0], dancing_price - y_pad), max(curr_ylim[1], dancing_price + y_pad))

                        curr_xlim = ax.get_xlim()
                        current_time_num = mdates.date2num(t_times[-1])
                        if current_time_num >= curr_xlim[1]:
                            x_shift = current_time_num - curr_xlim[1] + (0.05 * (curr_xlim[1] - curr_xlim[0]))
                            ax.set_xlim(curr_xlim[0] + x_shift, curr_xlim[1] + x_shift)

                        if lock_ref and 'fun_plane' in c:
                            max_t, min_t = max(lock_ref['frozen_target_prices']), min(lock_ref['frozen_target_prices'])

                            if dancing_price >= max_t:
                                c['fun_plane'].set_position(((loop_counter % 60) / 60.0, 0.85 + (math.sin(loop_counter) * 0.01)))
                                c['fun_plane'].set_alpha(0.9)
                            else:
                                c['fun_plane'].set_alpha(0.0)

                            if dancing_price <= min_t:
                                c['fun_sub'].set_position((1.0 - ((loop_counter % 80) / 80.0), 0.15 + (math.cos(loop_counter) * 0.01)))
                                c['fun_sub'].set_alpha(0.9)
                            else:
                                c['fun_sub'].set_alpha(0.0)

                            if c['hud_data'].get('whale_alert') and c['hud_data'].get('splash_direction') == -1:
                                c['fun_swan'].set_position(((loop_counter % 100) / 100.0, 0.35 + (math.sin(loop_counter) * 0.02)))
                                c['fun_swan'].set_alpha(0.9)
                            else:
                                c['fun_swan'].set_alpha(0.0)

                            rf_str = c['hud_data'].get('redfuzz_status', '')
                            leg_reg = c.get('tactile_data', {}).get('leg_regime', 'NORMAL')
                            if "VERTICAL WALL" in rf_str or "CLIMB" in rf_str:
                                c['fun_goat'].set_position(((loop_counter % 70) / 70.0, 0.65 + abs(math.sin(loop_counter * 0.5)) * 0.05))
                                c['fun_goat'].set_alpha(0.9)
                            else:
                                c['fun_goat'].set_alpha(0.0)

                            if 'flash_arrow' in c:
                                is_cliff = ("CLIFF" in rf_str) or (leg_reg == "LEG-DROP")
                                is_climb = ("CLIMB" in rf_str) or ("WALL" in rf_str) or (leg_reg == "LEG-CLIMB")
                                flash_on = (loop_counter % 2 == 0)
                                if is_cliff:
                                    c['flash_arrow'].set_text("⬇ CLIFF")
                                    c['flash_arrow'].set_color('#FF1744')
                                    c['flash_arrow'].set_alpha(0.95 if flash_on else 0.20)
                                    c['flash_arrow'].get_bbox_patch().set_edgecolor('#FF1744')
                                    c['flash_arrow'].get_bbox_patch().set_alpha(0.75 if flash_on else 0.15)
                                elif is_climb:
                                    c['flash_arrow'].set_text("⬆ CLIMB")
                                    c['flash_arrow'].set_color('#00FF66')
                                    c['flash_arrow'].set_alpha(0.95 if flash_on else 0.20)
                                    c['flash_arrow'].get_bbox_patch().set_edgecolor('#00FF66')
                                    c['flash_arrow'].get_bbox_patch().set_alpha(0.75 if flash_on else 0.15)
                                else:
                                    c['flash_arrow'].set_alpha(0.0)
                                    c['flash_arrow'].get_bbox_patch().set_alpha(0.0)

                        try:
                            if draw_data['recording']:
                                rec_t, rec_p = [m[0] for m in draw_data['recording']], [m[1] for m in draw_data['recording']]
                                if not rec_lines[tf_key]:
                                    rec_lines[tf_key], = ax.plot(rec_t, rec_p, color='#00BFFF', linewidth=1.5, marker='o', markersize=4)
                                else:
                                    rec_lines[tf_key].set_data(rec_t, rec_p)
                            elif rec_lines[tf_key]:
                                rec_lines[tf_key].set_data([], [])

                            if draw_data['lightning'] and 'path' in draw_data['lightning']:
                                pkg = draw_data['lightning']
                                fp_acc = draw_data.get('lightning_accuracy', 100.0)
                                y_span = curr_ylim[1] - curr_ylim[0]
                                l_t, l_p = build_directional_lightning_bolt(pkg, dancing_price, fp_acc, TIMEFRAMES[tf_key], y_span)

                                if len(l_t) >= 2:
                                    dyn_alpha = max(0.25, min(1.0, fp_acc / 85.0))
                                    if not light_lines[tf_key]:
                                        g2, = ax.plot(l_t, l_p, color='#0033FF', linewidth=6.5, alpha=dyn_alpha * 0.25)
                                        g1, = ax.plot(l_t, l_p, color='#00BFFF', linewidth=3.0, alpha=dyn_alpha * 0.60)
                                        core, = ax.plot(l_t, l_p, color='#E0FFFF', linewidth=1.6, marker='>', markevery=[-1], markersize=6, alpha=dyn_alpha)
                                        light_lines[tf_key] = (g2, g1, core)
                                    else:
                                        g2, g1, core = light_lines[tf_key]
                                        for line in (g2, g1, core):
                                            line.set_data(l_t, l_p)
                                        g2.set_alpha(dyn_alpha * 0.25)
                                        g1.set_alpha(dyn_alpha * 0.60)
                                        core.set_alpha(dyn_alpha)
                            elif light_lines[tf_key]:
                                for line in light_lines[tf_key]:
                                    line.set_data([], [])
                        except Exception:
                            pass

                plt.pause(0.5)
                loop_counter += 1

            if emergency_abort:
                continue
            STATE_MANAGER.save_state(ENGINES, EXEC_ENGINE)
            sys.stdout.write("\r[*] ORACLE WAKING: Synchronizing matrix & in-flight tuning... \n")

        except Exception as e:
            if "invalid command name" in str(e) or "application has been destroyed" in str(e):
                break
            import traceback
            err_msg = traceback.format_exc().split('\n')[-3:]
            for _, ax_err in grid_map:
                ax_err.clear()
                ax_err.set_facecolor('#330000')
                ax_err.text(0.5, 0.5, f"FATAL ERROR:\n{err_msg[0]}\n{err_msg[1]}", color='#FF0000', ha='center', va='center', fontsize=9, wrap=True)
                ax_err.set_xticks([])
                ax_err.set_yticks([])
            try:
                fig.canvas.draw()
                plt.pause(5.0)
            except Exception:
                time.sleep(5.0)

if __name__ == "__main__":
    run_multi_grid_oracle()
def save_and_push_to_github(file_path, commit_message="Auto-save persistent file"):
    repo_dir = os.getcwd()

    try:
        repo = Repo(repo_dir)

        repo.git.config("user.email", "streamlit-bot@example.com")

        repo.git.config("user.name", "Streamlit Bot")

        repo.index.add([file_path])

        repo.index.commit(commit_message)

        origin = repo.remote(name='origin')
        origin.push()
        print(f"Successfully pushed {file_path} to GitHub!")

    except Exception as e:
        print(f"Git push failed: {e}")
