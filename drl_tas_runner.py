import os
import numpy as np
import networkx as nx
import pandas as pd
import random
import collections

from stable_baselines3 import PPO
from gym import Env, spaces

# ---------------------------------------------------------------------
# P. Karimi @ TUE
# ---------------------------------------------------------------------

def define_zonal_topology(num_zones=6):
    G = nx.DiGraph()
    central_switch = "Central_Switch"
    G.add_node(central_switch, type="switch", ports=7)
    central_computer = "Central_Computer"
    G.add_node(central_computer, type="endpoint")
    G.add_edge(central_switch, central_computer, capacity_mbps=10, portA=0, portB=0)
    G.add_edge(central_computer, central_switch, capacity_mbps=10, portA=0, portB=0)

    for z in range(num_zones):
        zsw = f"Zone_{z}_Switch"
        zc = f"Zone_{z}_Controller"
        s0 = f"Zone_{z}_Sensor0"
        s1 = f"Zone_{z}_Sensor1"
        s2 = f"Zone_{z}_Sensor2"

        G.add_node(zsw, type="switch", ports=5)
        G.add_node(zc, type="endpoint")
        G.add_node(s0, type="endpoint")
        G.add_node(s1, type="endpoint")
        G.add_node(s2, type="endpoint")

        G.add_edge(central_switch, zsw, capacity_mbps=10, portA=(z+1), portB=0)
        G.add_edge(zsw, central_switch, capacity_mbps=10, portA=0, portB=(z+1))

        G.add_edge(zsw, zc, capacity_mbps=10, portA=1, portB=0)
        G.add_edge(zc, zsw, capacity_mbps=10, portA=0, portB=1)

        G.add_edge(zsw, s0, capacity_mbps=10, portA=2, portB=0)
        G.add_edge(s0, zsw, capacity_mbps=10, portA=0, portB=2)

        G.add_edge(zsw, s1, capacity_mbps=10, portA=3, portB=0)
        G.add_edge(s1, zsw, capacity_mbps=10, portA=0, portB=3)

        G.add_edge(zsw, s2, capacity_mbps=10, portA=4, portB=0)
        G.add_edge(s2, zsw, capacity_mbps=10, portA=0, portB=4)

    return G

def load_flows(csv_file):
    df = pd.read_csv(csv_file)
    flows = []
    for idx, row in df.iterrows():
        flow = {
            "id": row["id"],
            "talker": row["talker"],
            "listener": row["listener"],
            "frame_size": float(row["frame_size"]),
            "period": float(row["period"]),
            "deadline": float(row["deadline"]),
            "release_time": float(row["release_time"]),
            "queue": int(row["queue"])
        }
        flows.append(flow)
    return flows

def compute_paths(flows, G):
    for flow in flows:
        try:
            path = nx.shortest_path(G, source=flow["talker"], target=flow["listener"])
        except nx.NetworkXNoPath:
            path = []
        flow["path"] = path
    return flows

def compute_metrics(flows, link_available, G):
    total_flows = len(flows)
    if total_flows == 0:
        return 100.0, 0.0, 100.0

    successful = [f for f in flows if f["finish_time"] <= f["deadline_time"]]
    success_rate = (len(successful) / total_flows) * 100.0

    lat_sum = 0.0
    for f in flows:
        lat_sum += (f["finish_time"] - f["arrival_time"])

    avg_latency = lat_sum / total_flows

    trunk_links = []
    for u, v in G.edges():
        if G.nodes[u].get("type") == "switch" and \
           (G.nodes[v].get("type") == "switch" or "Central" in v):
            trunk_links.append((u, v))

    simulation_window = max(f["finish_time"] for f in flows)
    total_available = simulation_window * len(trunk_links)
    total_occupied = sum(link_available.get(edge, 0.0) for edge in trunk_links)

    if total_available <= 0.0:
        idle_percentage = 100.0
    else:
        used_pct = (total_occupied / total_available) * 100.0
        idle_percentage = max(0.0, 100.0 - used_pct)
    return success_rate, avg_latency, idle_percentage

class TASEnv(Env):
    def __init__(self, scenario_files, G, max_flows=50, alpha=0.01,
                 num_queues=8, max_segments=10):
        super().__init__()
        self.scenario_files = scenario_files
        self.G = G
        self.max_flows = max_flows
        self.alpha = alpha
        self.num_queues = num_queues
        self.max_segments = max_segments
        self.action_space = spaces.Box(low=0.0, high=1.0,
                                       shape=(self.num_queues + 1,),
                                       dtype=np.float32)
        self.num_features = 6
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(self.max_flows * self.num_features,),
            dtype=np.float32
        )

        self.current_step_count = 0
        self.current_flows = []
        self.num_flows = 0
        self.link_available = {}
        self.sim_time = 0.0
        self.done = False
        self.link_intervals = collections.defaultdict(list)
        self.meet_deadline_reward = 0.1
        self.miss_deadline_penalty = -0.1
        self.invalid_action_penalty = -0.01

    def _get_observation(self):
        DEADLINE_DIV = 10000.0
        SIZE_DIV = 9000.0
        RELEASE_DIV = 10000.0
        PATHLEN_DIV = 20.0
        EARLIEST_DIV = 200000.0

        obs = np.zeros((self.max_flows, self.num_features), dtype=np.float32)

        for i in range(self.num_flows):
            f = self.current_flows[i]
            not_finished_flag = 1.0 if (f["finish_time"] is None) else 0.0
            d_norm = min(f["deadline"] / DEADLINE_DIV, 1.0)
            s_norm = min(f["frame_size"] / SIZE_DIV, 1.0) if not_finished_flag > 0.5 else 0.0
            r_norm = min(f["release_time"] / RELEASE_DIV, 1.0)
            path_len = max(0, len(f["path"]) - 1)
            p_norm = min(path_len / PATHLEN_DIV, 1.0)

            if not_finished_flag > 0.5:
                next_start_est = max(self.sim_time, f["arrival_time"])
                est_norm = min(next_start_est / EARLIEST_DIV, 1.0)
            else:
                est_norm = 0.0

            obs[i, 0] = not_finished_flag
            obs[i, 1] = d_norm
            obs[i, 2] = s_norm
            obs[i, 3] = r_norm
            obs[i, 4] = p_norm
            obs[i, 5] = est_norm

        return obs.flatten()

    def reset(self):
        self.current_step_count = 0
        self.sim_time = 0.0
        self.done = False
        self.link_available.clear()
        self.link_intervals.clear()

        import random
        scenario_path = random.choice(self.scenario_files)
        flows = load_flows(scenario_path)
        flows = compute_paths(flows, self.G)
        flows = [f for f in flows if f["path"]]
        if len(flows) > self.max_flows:
            flows = flows[:self.max_flows]
        self.current_flows = flows
        self.num_flows = len(flows)

        for f in self.current_flows:
            f["arrival_time"] = f["release_time"]
            f["deadline_time"] = f["release_time"] + f["deadline"]
            f["finish_time"] = None

        return self._get_observation()

    def step(self, action):
        if self.done:
            return self._get_observation(), 0.0, True, {}

        gate_mask = action[:self.num_queues]
        seg_len_norm = action[-1]

        gates_open = []
        for i in range(self.num_queues):
            if gate_mask[i] >= 0.5:
                gates_open.append(i)

        segment_length = seg_len_norm * 20000.0
        if segment_length < 1.0:
            segment_length = 1.0

        reward = 0.0
        info = {}

        if len(gates_open) == 0:
            reward += self.invalid_action_penalty

        start_t = self.sim_time
        end_t = self.sim_time + segment_length

        for f in self.current_flows:
            if f["finish_time"] is not None:
                continue
            qid = f["queue"]
            if qid not in gates_open:
                continue

            path = f["path"]
            current_time = max(f["arrival_time"], start_t)
            for i in range(len(path) - 1):
                edge = (path[i], path[i+1])
                if edge not in self.link_available:
                    self.link_available[edge] = 0.0
                capacity = self.G[edge[0]][edge[1]]["capacity_mbps"]
                bytes_per_ms = (capacity * 1e6) / 8 / 1000.0
                tx_time = f["frame_size"] / bytes_per_ms

                earliest_start = max(self.link_available[edge], current_time)
                finish_time = earliest_start + tx_time

                if finish_time > end_t:
                    portion = end_t - earliest_start
                    if portion < 0:
                        pass
                    else:
                        used_up = earliest_start + portion
                        self.link_available[edge] = used_up
                        self.link_intervals[edge].append((earliest_start, used_up))

                        leftover_time = (finish_time - end_t)
                        leftover_bytes = (leftover_time / tx_time) * f["frame_size"]
                        f["frame_size"] = leftover_bytes
                    break
                else:
                    self.link_available[edge] = finish_time
                    self.link_intervals[edge].append((earliest_start, finish_time))
                    current_time = finish_time
            else:
                f["finish_time"] = current_time

        for f in self.current_flows:
            if f["finish_time"] is not None:
                if start_t <= f["finish_time"] <= end_t:
                    if f["finish_time"] <= f["deadline_time"]:
                        reward += self.meet_deadline_reward
                    else:
                        reward += self.miss_deadline_penalty

        self.sim_time = end_t
        self.current_step_count += 1

        all_finished = all(f["finish_time"] is not None for f in self.current_flows)
        if self.current_step_count >= self.max_segments or all_finished:
            self.done = True

        if self.done:
            sr, avg_lat, _ = self._finalize_and_metrics()
            final_r = (sr / 100.0) - (self.alpha * avg_lat)
            reward += final_r
            info["sr"] = sr
            info["avg_lat"] = avg_lat
            info["idle"] = self._compute_correct_idle()

        return self._get_observation(), reward, self.done, info

    def _finalize_and_metrics(self):
        for f in self.current_flows:
            if f["finish_time"] is None:
                f["finish_time"] = f["deadline_time"] + 999999
        sr, avg_lat, idle_ = compute_metrics(self.current_flows, self.link_available, self.G)
        return sr, avg_lat, idle_

    def _compute_correct_idle(self):
        if not self.current_flows:
            return 100.0
        real_end = max(f["finish_time"] for f in self.current_flows)
        if real_end <= 0.0:
            return 100.0
        all_intervals = []
        for edge, intervals in self.link_intervals.items():
            all_intervals.extend(intervals)
        if not all_intervals:
            return 100.0
        all_intervals.sort(key=lambda x: x[0])
        merged = []
        cur_start, cur_end = all_intervals[0]
        for i in range(1, len(all_intervals)):
            st, ed = all_intervals[i]
            if st <= cur_end:
                cur_end = max(cur_end, ed)
            else:
                merged.append((cur_start, cur_end))
                cur_start, cur_end = st, ed
        merged.append((cur_start, cur_end))
        total_busy = sum(interval[1] - interval[0] for interval in merged)
        idle_time = real_end - total_busy
        if idle_time < 0.0:
            idle_time = 0.0
        idle_pct = 100.0 * (idle_time / real_end)
        return idle_pct

def convert_actions_to_gcl(schedule_actions):
    current_time_ms = 0.0
    schedule_entries = []

    for action in schedule_actions:
        gates = action[:-1]
        seg_len_norm = action[-1]
        seg_ms = seg_len_norm * 20000.0
        if seg_ms < 2.0:
            seg_ms = 2.0

        open_queues = [i for i, val in enumerate(gates) if val >= 0.5]

        half_ms = seg_ms / 2.0
        durations_str = f"[{half_ms}ms, {half_ms}ms]"

        schedule_entries.append({
            "offset": f"{current_time_ms}ms",
            "durations": durations_str,
            "queueIndex": open_queues[0] if open_queues else 0
        })

        current_time_ms += seg_ms

    gcl_data = [{
        "nodeId": "Central_Switch",
        "portIndex": 0,
        "numTrafficClasses": 8,
        "schedule": schedule_entries
    }]
    return gcl_data

def run_drl_scheduler(csv_path: str):
    model_path = "ppo_final_model_tas.zip"
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = PPO.load(model_path)
    G = define_zonal_topology(num_zones=6)
    env = TASEnv([csv_path], G, max_flows=50, alpha=0.01, num_queues=8, max_segments=10)

    obs = env.reset()
    done = False
    schedule_actions = []
    while not done:
        action, _states = model.predict(obs, deterministic=True)
        schedule_actions.append(action)
        obs, reward, done, info = env.step(action)

    gcl_output = convert_actions_to_gcl(schedule_actions)
    return gcl_output
