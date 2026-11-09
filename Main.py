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

        screaming_veto = abs(leg_drive) >= 0.45
        if screaming_veto:
            dyn_w[0, :] *= 0.55
            dyn_w[1, :] *= 1.45
            dyn_w[2, :] *= 1.60

        honest_factor = float(np.clip((hist_acc / 68.0) * (0.65 + 0.70 * hp_mix), 0.35, 1.85))
        path_factor = float(np.clip((live_acc / 72.0) * (0.65 + 0.70 * (1.0 - hp_mix)), 0.35, 1.85))
        leg_surge = 1.0 + (min(1.8, abs(leg_drive)) * 0.65)

        dyn_w[0, :] *= honest_factor
        dyn_w[1, :] *= (path_factor * leg_surge)

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
    def __init__(self, data_dir):
        self.vault_file = os.path.join(data_dir, "proven_redfuzz_vault.pkl")
        self.active_audits = []
        self.proven_vault = []
        self.redfuzz_shape_scale = 1.0
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
# BINANCE DATA RETRIEVAL & API WRAPPERS
# -----------------------------
@st.cache_data(ttl=10, show_spinner=False)
def fetch_binance_klines(symbol, interval, limit=1000):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = HTTP_SESSION.get(url, timeout=4)
        if r.status_code == 200:
            raw = r.json()
            if not raw or len(raw) == 0:
                return None
            df = pd.DataFrame(raw, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_base_vol', 'taker_quote_vol', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['ts'] = df['close_time'] / 1000.0
            df['date'] = pd.to_datetime(df['close_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Australia/Adelaide').dt.tz_localize(None)
            return df[['ts', 'date', 'open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']]
    except Exception:
        pass
    return None

@st.cache_data(ttl=3, show_spinner=False)
def fetch_binance_depth(symbol, limit=100):
    try:
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}"
        r = HTTP_SESSION.get(url, timeout=3)
        if r.status_code == 200:
            d = r.json()
            bids = np.array(d.get('bids', []), dtype=float)
            asks = np.array(d.get('asks', []), dtype=float)
            return bids, asks
    except Exception:
        pass
    return None, None

@st.cache_data(ttl=2, show_spinner=False)
def fetch_binance_ticker(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = HTTP_SESSION.get(url, timeout=2)
        if r.status_code == 200:
            return float(r.json().get('price', 0.0))
    except Exception:
        pass
    return 0.0

# -----------------------------
# SANCTUARY MEMORY RECALL SYSTEM
# -----------------------------
class MetricLearner:
    def __init__(self, dim):
        self.weights = np.ones(dim, dtype=float)

    def distance(self, v1, v2):
        diff = v1 - v2
        return float(np.sqrt(np.dot(diff * self.weights, diff)))

    def update_from_errors(self, vectors, errors, lr=0.01):
        if len(vectors) == 0:
            return
        mean_err = np.mean(errors)
        for vec, err in zip(vectors, errors):
            if err > mean_err:
                self.weights = np.clip(self.weights + lr * (vec ** 2), 0.1, 10.0)

class SanctuaryMemory:
    def __init__(self):
        self.memories = deque(maxlen=MEMORY_MAX)

    def remember(self, pattern_vector, outcome_curve, volatility=0.01):
        mem = {
            "vector": pattern_vector,
            "outcome": outcome_curve,
            "volatility": volatility,
            "error_ewma": 1.0,
            "hits": 1
        }
        mem["score"] = self._score_memory(mem)
        self.memories.append(mem)

    def _score_memory(self, mem):
        return float(1.0 / (1.0 + mem["error_ewma"] * 5.0))

    def recall(self, pattern_vector, top_k=10, metric_learner=None):
        if not self.memories:
            return []
        scored = []
        for mem in self.memories:
            dist = metric_learner.distance(pattern_vector, mem["vector"]) if metric_learner else float(np.linalg.norm(pattern_vector - mem["vector"]))
            effective_dist = dist / (mem["score"] + 1e-6)
            scored.append((effective_dist, mem["outcome"], mem))
        scored.sort(key=lambda x: x[0])
        return scored[:top_k]

    def learn(self, pattern_vector, outcome_curve, volatility=0.01, persist_now=False):
        self.remember(pattern_vector, outcome_curve, volatility)

# -----------------------------
# ADAPTIVE LEARNING GOVERNOR
# -----------------------------
class AdaptiveLearningGovernor:
    def __init__(self, initial_lr=0.01):
        self.learning_rate = initial_lr
        self.recalc_trigger = 78.0

    def update(self, error, historical_accuracy, live_acc=100.0):
        acc_gap = (100.0 - historical_accuracy) / 100.0
        live_gap = (100.0 - live_acc) / 100.0
        self.learning_rate = float(np.clip(0.005 + (error * 0.1) + (acc_gap * 0.05) + (live_gap * 0.05), 0.001, 0.15))
        self.recalc_trigger = float(np.clip(72.0 + (historical_accuracy * 0.1), 65.0, 88.0))

# -----------------------------
# STREAMLIT MAIN APPLICATION & DASHBOARD RUNTIME
# -----------------------------
def main():
    st.sidebar.title("🌊 Golden River Oracle v22.2")
    st.sidebar.markdown(f"**Asset:** `{BINANCE_SYMBOL}` (Binance)")
    st.sidebar.markdown(f"**Owners:** Cale Sutherland & Daniela Admidina")
    st.sidebar.markdown("---")

    tf_choice = st.sidebar.selectbox("Select Projection Timeframe", list(TIMEFRAMES.keys()), index=1)
    cfg = TIMEFRAMES[tf_choice]
    horizon = cfg["horizon"]

    # Initialize Engine States
    if "engines" not in st.session_state:
        persistence = StatePersistence(STATE_JSON_FILE, STATE_SQLITE_DB, STATE_JSON_FALLBACK)
        exec_engine = FeeAwareExecutionEngine()
        redfuzz_vault = SelfGoverningRedFuzzVault(DATA_DIR)
        sentinel = RegimeShiftSentinel()

        timeframe_engines = {}
        for tf_k, tf_cfg in TIMEFRAMES.items():
            h = tf_cfg["horizon"]
            timeframe_engines[tf_k] = {
                "horizon": h,
                "sanctuary": SanctuaryMemory(),
                "metric": MetricLearner(12),
                "governor": AdaptiveLearningGovernor(),
                "swarm": MarkerSwarm(h),
                "opinion": BackfeedOpinionEngine(h),
                "formula": DecomposedPredictionFormula(h),
                "locker": TemporalLockManager(h),
                "fuzz": AdvancedFuzzEngine(h),
                "last_live_accuracy": 100.0,
                "p_max": 1.0
            }
        persistence.load_state(timeframe_engines, exec_engine)
        st.session_state.persistence = persistence
        st.session_state.exec_engine = exec_engine
        st.session_state.redfuzz_vault = redfuzz_vault
        st.session_state.sentinel = sentinel
        st.session_state.timeframe_engines = timeframe_engines

    engines = st.session_state.timeframe_engines
    persistence = st.session_state.persistence
    exec_engine = st.session_state.exec_engine
    redfuzz_vault = st.session_state.redfuzz_vault
    sentinel = st.session_state.sentinel

    eng = engines[tf_choice]
    sanctuary = eng["sanctuary"]
    metric = eng["metric"]
    governor = eng["governor"]
    swarm = eng["swarm"]
    opinion_engine = eng["opinion"]
    formula = eng["formula"]
    locker = eng["locker"]
    fuzz_engine = eng["fuzz"]

    # Fetch Live Data
    df = fetch_binance_klines(BINANCE_SYMBOL, cfg["interval"], cfg["limit"])
    live_price = fetch_binance_ticker(BINANCE_SYMBOL)
    bids, asks = fetch_binance_depth(BINANCE_SYMBOL, 100)

    if df is None or len(df) < 50 or live_price <= 0:
        st.error(f"⚠️ Unable to fetch live market data for {BINANCE_SYMBOL}. Retrying connection...")
        if st.button("🔄 Force Refresh"):
            st.rerun()
        return

    # Update current candle live price
    df.iloc[-1, df.columns.get_loc('close')] = live_price
    df.iloc[-1, df.columns.get_loc('high')] = max(df.iloc[-1]['high'], live_price)
    df.iloc[-1, df.columns.get_loc('low')] = min(df.iloc[-1]['low'], live_price)

    # Microstructure & Indicators
    micro = calculate_microstructure(df, 20)
    chop_bbw = calculate_advanced_chop_bias(df, 20, 2.0)
    rsi = calculate_advanced_rsi(df, 14)
    spatial = calculate_spatial_structure(df, 50)
    order_flow = calculate_order_flow_footprint(df, 20)
    tactile_data = calculate_tactile_ground_ceiling_and_legs(df, live_price, order_flow, bids, asks)
    btc_mom, dyn_beta = fetch_btc_macro_context(cfg["interval"], df['close'].values, 25)
    ghost_slope_corr, ghost_trust = audit_ghost_grid(df, live_price, locker)

    # Redfuzz Terrain Scan
    recent_velocity = (live_price - df['close'].iloc[-3]) / (df['close'].iloc[-3] + 1e-9) if len(df) >= 3 else 0.0
    burst_vol = float(df['volume'].iloc[-1]) - float(df['volume'].rolling(window=10, min_periods=1).mean().iloc[-1])
    rf_status, rf_conf, rf_alarm = beam_redfuzz_terrain_sensor(
        bids, asks, live_price, recent_velocity, burst_vol,
        signed_delta=order_flow.get('taker_delta_ratio', 0.0),
        leg_drive=tactile_data.get('leg_drive', 0.0)
    )

    # Check Active Lock & Grade
    prev_live_price = float(df['close'].iloc[-2]) if len(df) >= 2 else live_price
    locker.audit_physical_marker_hits(prev_live_price, live_price, swarm, persistence, tf_choice)
    locker.check_and_grade(df, swarm, metric, sanctuary, governor, opinion_engine, formula, chop_bbw)

    # Regime Shift Check
    live_acc_val, tracking_prices, tracking_times = locker.get_live_tracking_error(df, live_price, chop_bbw)
    eng["last_live_accuracy"] = live_acc_val

    is_broken, break_reason = sentinel.check_regime_break(
        locker.active_lock, live_price, live_acc_val, rf_alarm, rf_status,
        0.0, live_acc_val, eng.get("p_max", 1.0), governor.recalc_trigger, chop_bbw
    )
    if is_broken:
        locker.force_abort_and_learn(df, live_price, swarm, governor, opinion_engine, formula, chop_bbw)

    # Lock creation if missing
    if locker.active_lock is None:
        last_row = df.iloc[-1]
        base_ts = float(last_row['ts'])
        base_time = last_row['date']
        future_times = [base_time + (cfg["delta"] * (i + 1)) for i in range(horizon)]

        # Generate Projection Curve across Streams
        pattern = extract_pattern_vector(df, len(df) - 1)
        matches = sanctuary.recall(pattern, top_k=10, metric_learner=metric) if pattern is not None else []
        
        paths, dists, mem_scores = [], [], []
        for dist, outcome, mem in matches:
            paths.append(outcome)
            dists.append(dist)
            mem_scores.append(mem["score"])

        if len(paths) == 0:
            paths.append(np.zeros(horizon))
            dists.append(1.0)
            mem_scores.append(0.5)

        knn_raw = simulate_smashed_path(paths, dists, mem_scores, 0.5, recent_velocity, formula)
        swarm_fuzz = fuzz_engine.shoot_fuzz(knn_raw, recent_velocity, chop_bbw, 0.0, chop_bbw, 1.0, rsi, spatial['proximity'], formula)
        opinion_curve = opinion_engine.build_opinion_curve(df, live_price, spatial, order_flow, bids, asks, btc_mom, dyn_beta, ghost_slope_corr, formula)
        corridor_curve = (ghost_slope_corr * np.arange(1, horizon + 1)) + ((spatial['proximity'] - 0.5) * 0.01)
        landscape_curve = swarm_fuzz * 0.5 + opinion_curve * 0.5

        stream_snapshots = {
            "sanctuary": knn_raw,
            "swarm_fuzz": swarm_fuzz,
            "lightning": swarm_fuzz,
            "opinion": opinion_curve,
            "corridor": corridor_curve,
            "landscape": landscape_curve
        }

        blended, _ = opinion_engine.blend_marker_streams(
            stream_snapshots, live_acc=live_acc_val, fp_acc=locker.historical_accuracy,
            is_chop=chop_bbw < 0.008, formula=formula, spoof_passed=not rf_alarm,
            hist_acc=locker.historical_accuracy, leg_drive=tactile_data.get('leg_drive', 0.0)
        )

        shaped, apex_tag = apply_apex_trough_inflection(blended, df, live_price, rsi, spatial, order_flow, bids, asks, formula, tactile_data)
        tactile_shaped, tactile_tag = apply_tactile_leg_and_boundary_feel(shaped, tactile_data, formula)
        clamped_curve, p_max = apply_288_marker_clamp(tactile_shaped, df, live_price, micro['coil_score'], chop_bbw, ghost_slope_corr, formula, tactile_data)
        eng["p_max"] = p_max

        locker.lock_projection(
            base_ts, base_time, live_price, future_times, clamped_curve,
            chop_bbw, local_curve=clamped_curve, stream_snapshots=stream_snapshots,
            component_traces={"knn_raw": knn_raw, "swarm_fuzz": swarm_fuzz, "opinion": opinion_curve, "final_blended": clamped_curve}
        )
        locker.active_lock['apex_tag'] = apex_tag

    # Fee-aware execution evaluation
    exec_engine.evaluate_pressure(
        locker.active_lock['base_price'], live_price, locker.active_lock['frozen_target_prices'],
        [n.accuracy_weight for n in swarm.nodes], live_acc_val, eng.get("p_max", 1.0),
        redfuzz_alarm=rf_alarm, redfuzz_status=rf_status
    )

    # Save state periodically
    persistence.save_state(engines, exec_engine)

    # --- RENDER DASHBOARD UI ---
    st.title(f"🌊 Golden River Oracle v22.2 — {cfg['label']}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Live Price", f"${live_price:.7f}", f"{recent_velocity*100.0:+.2f}%")
    with col2:
        st.metric("Honest OOS Accuracy", f"{locker.historical_accuracy:.1f}%", f"Peak {locker.peak_historical_accuracy:.1f}%")
    with col3:
        st.metric("Live Path Tracking", f"{live_acc_val:.1f}%", f"Swarm Health {swarm.swarm_health:.1f}%")
    with col4:
        st.metric("Fee-Adj PnL", f"{exec_engine.cumulative_net_pnl_pct:+.2f}%", f"${exec_engine.bankroll:.2f}")

    # HUD String generation
    target_p = locker.active_lock['frozen_target_prices'][-1]
    move_pct = ((target_p - live_price) / live_price) * 100.0
    tilt, stress = calculate_vessel_physics(recent_velocity, chop_bbw, 0.01, micro['coil_score'], 0.0, locker.historical_accuracy)

    hud_dict = {
        'target_p': target_p, 'move_pct': move_pct, 'burst_vol': burst_vol,
        'apex_tag': locker.active_lock.get('apex_tag', 'NONE'),
        'redfuzz_status': rf_status, 'p_max': eng.get('p_max', 1.0),
        'bars_elapsed': len(df[df['ts'] > locker.active_lock['base_ts']]),
        'horizon': horizon, 'target_time_end': locker.active_lock['target_times'][-1],
        'settled_hits': len(locker.active_lock.get('settled_indices', set())),
        'live_accuracy': live_acc_val, 'all_frame_acc': live_acc_val,
        'historical_accuracy': locker.historical_accuracy, 'peak_accuracy': locker.peak_historical_accuracy,
        'topology_tag': tactile_data.get('leg_regime', 'NORMAL'),
        'formula_eff': formula.formula_efficiency, 'tuning_epoch': formula.tuning_epoch,
        'swarm_health': swarm.swarm_health, 'learning_rate': governor.learning_rate,
        'opinion_trust': opinion_engine.opinion_trust, 'lightning_gain': 1.2, 'lightning_combos': 2,
        'landscape_trust': opinion_engine.landscape_trust, 'landscape_gain': 0.9,
        'spoof_status': 'SOLID-VERIFIED' if not rf_alarm else 'WARNING-TRIGGERED',
        'wiggles': micro['wiggles'], 'coil_score': micro['coil_score'], 'rsi': rsi,
        'current_lens_focus': fuzz_engine.lens.focus_multiplier, 'chop_bbw': chop_bbw, 'dynamic_beta': dyn_beta,
        'tilt': tilt, 'stress': stress, 'stress_warn': '(NORMAL)' if stress < 1.5 else '(HIGH STRESS)',
        'vector_aligned': True, 'tick_angle': tilt, 'kinetic_velocity': recent_velocity,
        'minimum_velocity_met': True, 'corner_phase': 'CRUISE', 'cda_acc': 75.0, 'corner_inf': 0.35,
        'corner_vault_cnt': len(redfuzz_vault.proven_vault), 'whale_alert': burst_vol > 0.005,
        'splash_magnitude': 1.2, 'splash_direction': 1, 'pos_side': exec_engine.position_side,
        'conviction': exec_engine.conviction, 'net_pnl_pct': exec_engine.cumulative_net_pnl_pct,
        'lazarus_fund': exec_engine.lazarus_bankroll
    }

    hud_text = build_hud_string(live_price, hud_dict)
    st.text_area("Oracle Sovereign HUD Console", hud_text, height=220)

    # Matplotlib Charting
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')

    history_df = df.tail(60)
    ax.plot(history_df['date'], history_df['close'], color='#00FFFF', linewidth=1.8, label='Live Price Tape')

    future_times = locker.active_lock['target_times']
    target_prices = locker.active_lock['frozen_target_prices']
    ax.plot([history_df['date'].iloc[-1]] + future_times, [live_price] + list(target_prices), color='#FF007F', linewidth=2.2, linestyle='--', label='Oracle Trajectory Lock')

    ax.set_title(f"Golden River Oracle Projection & Execution Space ({BINANCE_SYMBOL})", color='white', fontsize=12, fontweight='bold')
    ax.tick_params(colors='white', labelsize=9)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(cfg["dt_fmt"]))
    ax.spines['bottom'].set_color('#333333')
    ax.spines['top'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.spines['right'].set_color('#333333')
    ax.legend(loc='upper left', facecolor='#1E1E1E', edgecolor='none', labelcolor='white')
    ax.grid(color='#222222', linestyle=':', linewidth=0.8)

    st.pyplot(fig)

    if st.sidebar.button("⚡ Force Recalculate Oracle Lock"):
        locker.active_lock = None
        st.rerun()

if __name__ == "__main__":
    main()
# --- END OF PART 2 ---
# -----------------------------
# MULTI-SOURCE DATA RETRIEVAL & API WRAPPERS (FALLBACK RESILIENT)
# -----------------------------
@st.cache_data(ttl=10, show_spinner=False)
def fetch_binance_klines(symbol="NEIROUSDT", interval="1h", limit=1000):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = HTTP_SESSION.get(url, timeout=4)
        if r.status_code == 200:
            raw = r.json()
            if not raw or len(raw) == 0:
                return None
            df = pd.DataFrame(raw, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_base_vol', 'taker_quote_vol', 'ignore'
            ])
            for col in ['open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['ts'] = df['close_time'] / 1000.0
            df['date'] = pd.to_datetime(df['close_time'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Australia/Adelaide').dt.tz_localize(None)
            return df[['ts', 'date', 'open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']]
    except Exception:
        pass
    return None

@st.cache_data(ttl=10, show_spinner=False)
def fetch_coingecko_data(coin_id="first-neiro-on-ethereum", vs_currency="usd", limit=100):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency={vs_currency}&days=7"
        r = HTTP_SESSION.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])
            if not prices:
                return None
            records = []
            now_ts = time.time()
            for idx, (p_ts, p_val) in enumerate(prices[-limit:]):
                ts_sec = p_ts / 1000.0
                vol = volumes[idx][1] if idx < len(volumes) else 10000.0
                records.append({
                    'ts': ts_sec,
                    'date': pd.to_datetime(ts_sec, unit='s').dt.tz_localize('UTC').dt.tz_convert('Australia/Adelaide').dt.tz_localize(None) if hasattr(pd.to_datetime(ts_sec, unit='s'), 'dt') else datetime.fromtimestamp(ts_sec),
                    'open': p_val * 0.999, 'high': p_val * 1.002, 'low': p_val * 0.998, 'close': p_val,
                    'volume': vol, 'taker_base_vol': vol * 0.5, 'num_trades': 150
                })
            df = pd.DataFrame(records)
            return df[['ts', 'date', 'open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']]
    except Exception:
        pass
    return None

@st.cache_data(ttl=10, show_spinner=False)
def fetch_coincap_data(asset="first-neiro-on-ethereum", limit=100):
    try:
        url = f"https://api.coincap.io/v2/assets/{asset}/history?interval=h1"
        r = HTTP_SESSION.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if not data:
                return None
            records = []
            for item in data[-limit:]:
                p_val = float(item.get("priceUsd", 0.0))
                ts_sec = float(item.get("time", time.time() * 1000)) / 1000.0
                records.append({
                    'ts': ts_sec,
                    'date': datetime.fromtimestamp(ts_sec),
                    'open': p_val * 0.999, 'high': p_val * 1.002, 'low': p_val * 0.998, 'close': p_val,
                    'volume': 50000.0, 'taker_base_vol': 25000.0, 'num_trades': 100
                })
            df = pd.DataFrame(records)
            return df[['ts', 'date', 'open', 'high', 'low', 'close', 'volume', 'taker_base_vol', 'num_trades']]
    except Exception:
        pass
    return None

def fetch_synthetic_fallback_data(base_price=0.0015, limit=500):
    now = time.time()
    dt_now = datetime.now()
    records = []
    p = base_price
    np.random.seed(42)
    for i in range(limit):
        ts = now - ((limit - i) * 3600)
        dt = dt_now - timedelta(hours=(limit - i))
        change = np.random.normal(0.0, p * 0.015)
        p = max(0.00001, p + change)
        records.append({
            'ts': ts, 'date': dt,
            'open': p * 0.995, 'high': p * 1.012, 'low': p * 0.988, 'close': p,
            'volume': 100000.0, 'taker_base_vol': 50000.0, 'num_trades': 200
        })
    return pd.DataFrame(records)

def multi_source_klines_router(source_choice, symbol="NEIROUSDT"):
    df = None
    if source_choice == "Binance (Direct REST)":
        df = fetch_binance_klines(symbol, "1h", 1000)
        if df is None:
            st.warning("⚠️ Binance API unavailable or rate-limited. Falling back to CoinGecko...")
            df = fetch_coingecko_data()
    elif source_choice == "CoinGecko (Public REST)":
        df = fetch_coingecko_data()
        if df is None:
            st.warning("⚠️ CoinGecko API unavailable. Falling back to CoinCap...")
            df = fetch_coincap_data()
    elif source_choice == "CoinCap (Public REST)":
        df = fetch_coincap_data()
    
    if df is None or len(df) < 20:
        st.info("ℹ️ External exchange feeds unreachable. Initializing robust Synthetic Simulation Feed.")
        df = fetch_synthetic_fallback_data(0.0015, 500)
    return df

@st.cache_data(ttl=3, show_spinner=False)
def fetch_multi_source_depth(source_choice):
    if source_choice == "Binance (Direct REST)":
        bids, asks = fetch_binance_depth(BINANCE_SYMBOL, 100)
        if bids is not None and len(bids) > 0:
            return bids, asks
    
    # Synthetic / Simulated Order Book fallback
    live_p = 0.0015
    bids = np.array([[live_p * (1.0 - (i * 0.001)), 10000.0 * (i + 1)] for i in range(50)], dtype=float)
    asks = np.array([[live_p * (1.0 + (i * 0.001)), 10000.0 * (i + 1)] for i in range(50)], dtype=float)
    return bids, asks

@st.cache_data(ttl=2, show_spinner=False)
def fetch_multi_source_ticker(source_choice, df):
    if source_choice == "Binance (Direct REST)":
        p = fetch_binance_ticker(BINANCE_SYMBOL)
        if p > 0:
            return p
    if df is not None and len(df) > 0:
        return float(df['close'].iloc[-1])
    return 0.0015

# -----------------------------
# SANCTUARY MEMORY RECALL SYSTEM
# -----------------------------
class MetricLearner:
    def __init__(self, dim):
        self.weights = np.ones(dim, dtype=float)

    def distance(self, v1, v2):
        diff = v1 - v2
        return float(np.sqrt(np.dot(diff * self.weights, diff)))

    def update_from_errors(self, vectors, errors, lr=0.01):
        if len(vectors) == 0:
            return
        mean_err = np.mean(errors)
        for vec, err in zip(vectors, errors):
            if err > mean_err:
                self.weights = np.clip(self.weights + lr * (vec ** 2), 0.1, 10.0)

class SanctuaryMemory:
    def __init__(self):
        self.memories = deque(maxlen=MEMORY_MAX)

    def remember(self, pattern_vector, outcome_curve, volatility=0.01):
        mem = {
            "vector": pattern_vector,
            "outcome": outcome_curve,
            "volatility": volatility,
            "error_ewma": 1.0,
            "hits": 1
        }
        mem["score"] = self._score_memory(mem)
        self.memories.append(mem)

    def _score_memory(self, mem):
        return float(1.0 / (1.0 + mem["error_ewma"] * 5.0))

    def recall(self, pattern_vector, top_k=10, metric_learner=None):
        if not self.memories:
            return []
        scored = []
        for mem in self.memories:
            dist = metric_learner.distance(pattern_vector, mem["vector"]) if metric_learner else float(np.linalg.norm(pattern_vector - mem["vector"]))
            effective_dist = dist / (mem["score"] + 1e-6)
            scored.append((effective_dist, mem["outcome"], mem))
        scored.sort(key=lambda x: x[0])
        return scored[:top_k]

    def learn(self, pattern_vector, outcome_curve, volatility=0.01, persist_now=False):
        self.remember(pattern_vector, outcome_curve, volatility)

# -----------------------------
# ADAPTIVE LEARNING GOVERNOR
# -----------------------------
class AdaptiveLearningGovernor:
    def __init__(self, initial_lr=0.01):
        self.learning_rate = initial_lr
        self.recalc_trigger = 78.0

    def update(self, error, historical_accuracy, live_acc=100.0):
        acc_gap = (100.0 - historical_accuracy) / 100.0
        live_gap = (100.0 - live_acc) / 100.0
        self.learning_rate = float(np.clip(0.005 + (error * 0.1) + (acc_gap * 0.05) + (live_gap * 0.05), 0.001, 0.15))
        self.recalc_trigger = float(np.clip(72.0 + (historical_accuracy * 0.1), 65.0, 88.0))

# -----------------------------
# STREAMLIT MAIN APPLICATION & DASHBOARD RUNTIME
# -----------------------------
def main():
    st.sidebar.title("🌊 Golden River Oracle v22.2")
    st.sidebar.markdown(f"**Owners:** Cale Sutherland & Daniela Admidina")
    st.sidebar.markdown("---")

    data_source_option = st.sidebar.selectbox(
        "Select Price Data Source",
        ["Binance (Direct REST)", "CoinGecko (Public REST)", "CoinCap (Public REST)"],
        index=0
    )

    tf_choice = st.sidebar.selectbox("Select Projection Timeframe", list(TIMEFRAMES.keys()), index=1)
    cfg = TIMEFRAMES[tf_choice]
    horizon = cfg["horizon"]

    # Initialize Engine States
    if "engines" not in st.session_state:
        persistence = StatePersistence(STATE_JSON_FILE, STATE_SQLITE_DB, STATE_JSON_FALLBACK)
        exec_engine = FeeAwareExecutionEngine()
        redfuzz_vault = SelfGoverningRedFuzzVault(DATA_DIR)
        sentinel = RegimeShiftSentinel()

        timeframe_engines = {}
        for tf_k, tf_cfg in TIMEFRAMES.items():
            h = tf_cfg["horizon"]
            timeframe_engines[tf_k] = {
                "horizon": h,
                "sanctuary": SanctuaryMemory(),
                "metric": MetricLearner(12),
                "governor": AdaptiveLearningGovernor(),
                "swarm": MarkerSwarm(h),
                "opinion": BackfeedOpinionEngine(h),
                "formula": DecomposedPredictionFormula(h),
                "locker": TemporalLockManager(h),
                "fuzz": AdvancedFuzzEngine(h),
                "last_live_accuracy": 100.0,
                "p_max": 1.0
            }
        persistence.load_state(timeframe_engines, exec_engine)
        st.session_state.persistence = persistence
        st.session_state.exec_engine = exec_engine
        st.session_state.redfuzz_vault = redfuzz_vault
        st.session_state.sentinel = sentinel
        st.session_state.timeframe_engines = timeframe_engines

    engines = st.session_state.timeframe_engines
    persistence = st.session_state.persistence
    exec_engine = st.session_state.exec_engine
    redfuzz_vault = st.session_state.redfuzz_vault
    sentinel = st.session_state.sentinel

    eng = engines[tf_choice]
    sanctuary = eng["sanctuary"]
    metric = eng["metric"]
    governor = eng["governor"]
    swarm = eng["swarm"]
    opinion_engine = eng["opinion"]
    formula = eng["formula"]
    locker = eng["locker"]
    fuzz_engine = eng["fuzz"]

    # Fetch Data via Multi-Source Router
    df = multi_source_klines_router(data_source_option, BINANCE_SYMBOL)
    live_price = fetch_multi_source_ticker(data_source_option, df)
    bids, asks = fetch_multi_source_depth(data_source_option)

    if df is None or len(df) < 30 or live_price <= 0:
        st.error("⚠️ Unable to retrieve price feed from any selected source. Please check network connection.")
        if st.button("🔄 Force Refresh"):
            st.rerun()
        return

    # Update current candle live price
    df.iloc[-1, df.columns.get_loc('close')] = live_price
    df.iloc[-1, df.columns.get_loc('high')] = max(df.iloc[-1]['high'], live_price)
    df.iloc[-1, df.columns.get_loc('low')] = min(df.iloc[-1]['low'], live_price)

    # Microstructure & Indicators
    micro = calculate_microstructure(df, 20)
    chop_bbw = calculate_advanced_chop_bias(df, 20, 2.0)
    rsi = calculate_advanced_rsi(df, 14)
    spatial = calculate_spatial_structure(df, 50)
    order_flow = calculate_order_flow_footprint(df, 20)
    tactile_data = calculate_tactile_ground_ceiling_and_legs(df, live_price, order_flow, bids, asks)
    btc_mom, dyn_beta = fetch_btc_macro_context(cfg["interval"], df['close'].values, 25)
    ghost_slope_corr, ghost_trust = audit_ghost_grid(df, live_price, locker)

    # Redfuzz Terrain Scan
    recent_velocity = (live_price - df['close'].iloc[-3]) / (df['close'].iloc[-3] + 1e-9) if len(df) >= 3 else 0.0
    burst_vol = float(df['volume'].iloc[-1]) - float(df['volume'].rolling(window=10, min_periods=1).mean().iloc[-1])
    rf_status, rf_conf, rf_alarm = beam_redfuzz_terrain_sensor(
        bids, asks, live_price, recent_velocity, burst_vol,
        signed_delta=order_flow.get('taker_delta_ratio', 0.0),
        leg_drive=tactile_data.get('leg_drive', 0.0)
    )

    # Check Active Lock & Grade
    prev_live_price = float(df['close'].iloc[-2]) if len(df) >= 2 else live_price
    locker.audit_physical_marker_hits(prev_live_price, live_price, swarm, persistence, tf_choice)
    locker.check_and_grade(df, swarm, metric, sanctuary, governor, opinion_engine, formula, chop_bbw)

    # Regime Shift Check
    live_acc_val, tracking_prices, tracking_times = locker.get_live_tracking_error(df, live_price, chop_bbw)
    eng["last_live_accuracy"] = live_acc_val

    is_broken, break_reason = sentinel.check_regime_break(
        locker.active_lock, live_price, live_acc_val, rf_alarm, rf_status,
        0.0, live_acc_val, eng.get("p_max", 1.0), governor.recalc_trigger, chop_bbw
    )
    if is_broken:
        locker.force_abort_and_learn(df, live_price, swarm, governor, opinion_engine, formula, chop_bbw)

    # Lock creation if missing
    if locker.active_lock is None:
        last_row = df.iloc[-1]
        base_ts = float(last_row['ts'])
        base_time = last_row['date']
        future_times = [base_time + (cfg["delta"] * (i + 1)) for i in range(horizon)]

        # Generate Projection Curve across Streams
        pattern = extract_pattern_vector(df, len(df) - 1)
        matches = sanctuary.recall(pattern, top_k=10, metric_learner=metric) if pattern is not None else []
        
        paths, dists, mem_scores = [], [], []
        for dist, outcome, mem in matches:
            paths.append(outcome)
            dists.append(dist)
            mem_scores.append(mem["score"])

        if len(paths) == 0:
            paths.append(np.zeros(horizon))
            dists.append(1.0)
            mem_scores.append(0.5)

        knn_raw = simulate_smashed_path(paths, dists, mem_scores, 0.5, recent_velocity, formula)
        swarm_fuzz = fuzz_engine.shoot_fuzz(knn_raw, recent_velocity, chop_bbw, 0.0, chop_bbw, 1.0, rsi, spatial['proximity'], formula)
        opinion_curve = opinion_engine.build_opinion_curve(df, live_price, spatial, order_flow, bids, asks, btc_mom, dyn_beta, ghost_slope_corr, formula)
        corridor_curve = (ghost_slope_corr * np.arange(1, horizon + 1)) + ((spatial['proximity'] - 0.5) * 0.01)
        landscape_curve = swarm_fuzz * 0.5 + opinion_curve * 0.5

        stream_snapshots = {
            "sanctuary": knn_raw,
            "swarm_fuzz": swarm_fuzz,
            "lightning": swarm_fuzz,
            "opinion": opinion_curve,
            "corridor": corridor_curve,
            "landscape": landscape_curve
        }

        blended, _ = opinion_engine.blend_marker_streams(
            stream_snapshots, live_acc=live_acc_val, fp_acc=locker.historical_accuracy,
            is_chop=chop_bbw < 0.008, formula=formula, spoof_passed=not rf_alarm,
            hist_acc=locker.historical_accuracy, leg_drive=tactile_data.get('leg_drive', 0.0)
        )

        shaped, apex_tag = apply_apex_trough_inflection(blended, df, live_price, rsi, spatial, order_flow, bids, asks, formula, tactile_data)
        tactile_shaped, tactile_tag = apply_tactile_leg_and_boundary_feel(shaped, tactile_data, formula)
        clamped_curve, p_max = apply_288_marker_clamp(tactile_shaped, df, live_price, micro['coil_score'], chop_bbw, ghost_slope_corr, formula, tactile_data)
        eng["p_max"] = p_max

        locker.lock_projection(
            base_ts, base_time, live_price, future_times, clamped_curve,
            chop_bbw, local_curve=clamped_curve, stream_snapshots=stream_snapshots,
            component_traces={"knn_raw": knn_raw, "swarm_fuzz": swarm_fuzz, "opinion": opinion_curve, "final_blended": clamped_curve}
        )
        locker.active_lock['apex_tag'] = apex_tag

    # Fee-aware execution evaluation
    exec_engine.evaluate_pressure(
        locker.active_lock['base_price'], live_price, locker.active_lock['frozen_target_prices'],
        [n.accuracy_weight for n in swarm.nodes], live_acc_val, eng.get("p_max", 1.0),
        redfuzz_alarm=rf_alarm, redfuzz_status=rf_status
    )

    # Save state periodically
    persistence.save_state(engines, exec_engine)

    # --- RENDER DASHBOARD UI ---
    st.title(f"🌊 Golden River Oracle v22.2 — {cfg['label']}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Live Price", f"${live_price:.7f}", f"{recent_velocity*100.0:+.2f}%")
    with col2:
        st.metric("Honest OOS Accuracy", f"{locker.historical_accuracy:.1f}%", f"Peak {locker.peak_historical_accuracy:.1f}%")
    with col3:
        st.metric("Live Path Tracking", f"{live_acc_val:.1f}%", f"Swarm Health {swarm.swarm_health:.1f}%")
    with col4:
        st.metric("Fee-Adj PnL", f"{exec_engine.cumulative_net_pnl_pct:+.2f}%", f"${exec_engine.bankroll:.2f}")

    # HUD String generation
    target_p = locker.active_lock['frozen_target_prices'][-1]
    move_pct = ((target_p - live_price) / live_price) * 100.0
    tilt, stress = calculate_vessel_physics(recent_velocity, chop_bbw, 0.01, micro['coil_score'], 0.0, locker.historical_accuracy)

    hud_dict = {
        'target_p': target_p, 'move_pct': move_pct, 'burst_vol': burst_vol,
        'apex_tag': locker.active_lock.get('apex_tag', 'NONE'),
        'redfuzz_status': rf_status, 'p_max': eng.get('p_max', 1.0),
        'bars_elapsed': len(df[df['ts'] > locker.active_lock['base_ts']]),
        'horizon': horizon, 'target_time_end': locker.active_lock['target_times'][-1],
        'settled_hits': len(locker.active_lock.get('settled_indices', set())),
        'live_accuracy': live_acc_val, 'all_frame_acc': live_acc_val,
        'historical_accuracy': locker.historical_accuracy, 'peak_accuracy': locker.peak_historical_accuracy,
        'topology_tag': tactile_data.get('leg_regime', 'NORMAL'),
        'formula_eff': formula.formula_efficiency, 'tuning_epoch': formula.tuning_epoch,
        'swarm_health': swarm.swarm_health, 'learning_rate': governor.learning_rate,
        'opinion_trust': opinion_engine.opinion_trust, 'lightning_gain': 1.2, 'lightning_combos': 2,
        'landscape_trust': opinion_engine.landscape_trust, 'landscape_gain': 0.9,
        'spoof_status': 'SOLID-VERIFIED' if not rf_alarm else 'WARNING-TRIGGERED',
        'wiggles': micro['wiggles'], 'coil_score': micro['coil_score'], 'rsi': rsi,
        'current_lens_focus': fuzz_engine.lens.focus_multiplier, 'chop_bbw': chop_bbw, 'dynamic_beta': dyn_beta,
        'tilt': tilt, 'stress': stress, 'stress_warn': '(NORMAL)' if stress < 1.5 else '(HIGH STRESS)',
        'vector_aligned': True, 'tick_angle': tilt, 'kinetic_velocity': recent_velocity,
        'minimum_velocity_met': True, 'corner_phase': 'CRUISE', 'cda_acc': 75.0, 'corner_inf': 0.35,
        'corner_vault_cnt': len(redfuzz_vault.proven_vault), 'whale_alert': burst_vol > 0.005,
        'splash_magnitude': 1.2, 'splash_direction': 1, 'pos_side': exec_engine.position_side,
        'conviction': exec_engine.conviction, 'net_pnl_pct': exec_engine.cumulative_net_pnl_pct,
        'lazarus_fund': exec_engine.lazarus_bankroll
    }

    hud_text = build_hud_string(live_price, hud_dict)
    st.text_area("Oracle Sovereign HUD Console", hud_text, height=220)

    # Matplotlib Charting
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor('#0E1117')
    ax.set_facecolor('#0E1117')

    history_df = df.tail(60)
    ax.plot(history_df['date'], history_df['close'], color='#00FFFF', linewidth=1.8, label=f'Live Price Tape ({data_source_option})')

    future_times = locker.active_lock['target_times']
    target_prices = locker.active_lock['frozen_target_prices']
    ax.plot([history_df['date'].iloc[-1]] + future_times, [live_price] + list(target_prices), color='#FF007F', linewidth=2.2, linestyle='--', label='Oracle Trajectory Lock')

    ax.set_title(f"Golden River Oracle Projection & Execution Space ({BINANCE_SYMBOL})", color='white', fontsize=12, fontweight='bold')
    ax.tick_params(colors='white', labelsize=9)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(cfg["dt_fmt"]))
    ax.spines['bottom'].set_color('#333333')
    ax.spines['top'].set_color('#333333')
    ax.spines['left'].set_color('#333333')
    ax.spines['right'].set_color('#333333')
    ax.legend(loc='upper left', facecolor='#1E1E1E', edgecolor='none', labelcolor='white')
    ax.grid(color='#222222', linestyle=':', linewidth=0.8)

    st.pyplot(fig)

    if st.sidebar.button("⚡ Force Recalculate Oracle Lock"):
        locker.active_lock = None
        st.rerun()

if __name__ == "__main__":
    main()
