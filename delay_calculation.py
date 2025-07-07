import io
import math
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# P. Karimi @ TUE
# ---------------------------------------------------------------------

def parse_bitrate(speed_str):
    s = speed_str.strip().lower()
    if s.endswith("mbps"):
        val = float(s.replace("mbps", ""))
        return val * 1e6
    elif s.endswith("gbps"):
        val = float(s.replace("gbps", ""))
        return val * 1e9
    else:
        return 100e6  

def parse_packet_size(size_str):
    s = size_str.strip().lower()
    if s.endswith("b"):
        s = s.replace("b", "")
    try:
        return int(s)
    except:
        return 1000  

def parse_time_to_seconds(time_str):
    t = time_str.strip().lower()
    if "us" in t:
        val = float(t.replace("us", "")) * 1e-6
        return val
    elif "ms" in t:
        val = float(t.replace("ms", "")) * 1e-3
        return val
    elif "s" in t:
        val = float(t.replace("s", ""))
        return val
    else:
        try:
            return float(t)
        except:
            return 2e-4  

def parse_durations(dur_str):
    ds = dur_str.strip().strip("[]")
    if not ds:
        return []
    parts = ds.split(",")
    results = []
    for p in parts:
        results.append(parse_time_to_seconds(p))
    return results


class GateSchedule:
    def __init__(self, offset, durations, first_state_open=True):

        self.offset = offset
        self.durations = durations
        self.cycle_time = sum(durations)
        if len(durations) == 2:
            T = self.cycle_time
            open_dur = durations[0]
            close_dur = durations[1]
            self.first_open = (T - offset) % T
            self.first_close = self.first_open + open_dur
            if self.first_close <= T:
                self.open_intervals = [(self.first_open, self.first_close)]
            else:
                self.open_intervals = [(self.first_open, T), (0, self.first_close - T)]
        else:
            self.open_intervals = []
            cur = offset % self.cycle_time
            is_open = True
            for d in durations:
                start = cur
                end = cur + d
                if is_open:
                    s = start % self.cycle_time
                    e = end % self.cycle_time
                    if s < e:
                        self.open_intervals.append((s, e))
                    else:
                        self.open_intervals.append((s, self.cycle_time))
                        self.open_intervals.append((0, e))
                cur += d
                is_open = not is_open
            self.open_intervals.sort()
            merged = []
            for intr in self.open_intervals:
                if not merged:
                    merged.append(intr)
                else:
                    last = merged[-1]
                    if intr[0] <= last[1]:
                        merged[-1] = (last[0], max(last[1], intr[1]))
                    else:
                        merged.append(intr)
            self.open_intervals = merged

    def is_open(self, t):
        modt = t % self.cycle_time
        for (start, end) in self.open_intervals:
            if start <= modt < end:
                return True
        return False

    def next_open_time(self, t):
        modt = t % self.cycle_time
        for (start, end) in sorted(self.open_intervals):
            if modt < start:
                return t - modt + start
            if start <= modt < end:
                return t
        first_start = sorted(self.open_intervals)[0][0]
        return t - modt + self.cycle_time + first_start

def parse_node_gateschedules(nodes):
    from collections import defaultdict
    gate_schedules = defaultdict(lambda: defaultdict(dict))
    for node in nodes:
        n_id = node["id"]
        gcl_list = node.get("gclConfigs", [])
        if not gcl_list:
            continue
        for port_cfg in gcl_list:
            port_idx = port_cfg.get("portIndex", 0)
            schedule_list = port_cfg.get("schedule", [])
            for sched in schedule_list:
                offset_str    = sched.get("offset", "0ms")
                durations_str = sched.get("durations", "[4ms,6ms]")
                queue_index   = sched.get("queueIndex", 0)
                offset_val    = parse_time_to_seconds(offset_str)
                durations     = parse_durations(durations_str)
                gate_schedules[n_id][port_idx][queue_index] = GateSchedule(offset_val, durations, first_state_open=True)
    return gate_schedules


def build_hop_path(src_node, dst_node, links):
    from collections import defaultdict, deque
    graph = defaultdict(list)
    link_map = {}
    for lk in links:
        nA = lk["sourceNode"]
        nB = lk["targetNode"]
        graph[nA].append(nB)
        graph[nB].append(nA)
        link_map[(nA, nB)] = lk
        link_map[(nB, nA)] = lk
    visited = set()
    parent = {}
    queue = deque([src_node])
    visited.add(src_node)
    found = False
    while queue:
        cur = queue.popleft()
        if cur == dst_node:
            found = True
            break
        for nbr in graph[cur]:
            if nbr not in visited:
                visited.add(nbr)
                parent[nbr] = cur
                queue.append(nbr)
    if not found:
        return []
    path_nodes = []
    x = dst_node
    while x != src_node:
        path_nodes.append(x)
        x = parent[x]
    path_nodes.append(src_node)
    path_nodes.reverse()
    return path_nodes

def find_port_and_speed(nodeA, nodeB, links, default_bps):
    for lk in links:
        s_node = lk["sourceNode"]
        t_node = lk["targetNode"]
        s_port = lk.get("sourcePort", 0)
        t_port = lk.get("targetPort", 0)
        link_speed_str = lk.get("linkSpeed", None)
        bps = parse_bitrate(link_speed_str) if link_speed_str else default_bps
        if s_node == nodeA and t_node == nodeB:
            return (s_port, t_port, bps)
        if s_node == nodeB and t_node == nodeA:
            return (t_port, s_port, bps)
    return None

def generate_delay_plot(config):

    import numpy as np
    nodes = config.get("nodes", [])
    links = config.get("links", [])
    flows_raw = config.get("flows", [])
    global_config = config.get("globalConfig", {})
    sim_time_str = global_config.get("defaultSimTime", "20ms")
    sim_end = parse_time_to_seconds(sim_time_str)
    if sim_end <= 0:
        sim_end = 0.02
    default_link_speed_str = global_config.get("defaultLinkSpeed", "100Mbps")
    default_link_bps = parse_bitrate(default_link_speed_str)
    
    gate_schedules = parse_node_gateschedules(nodes)
    
    from collections import defaultdict
    next_free_time = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    
    def get_gate_schedule(nodeId, portIndex, queueIndex):
        if nodeId in gate_schedules:
            if portIndex in gate_schedules[nodeId]:
                if queueIndex in gate_schedules[nodeId][portIndex]:
                    return gate_schedules[nodeId][portIndex][queueIndex]
        return None  
    
    path_cache = {}
    def get_path(src, dst):
        if (src, dst) in path_cache:
            return path_cache[(src, dst)]
        p = build_hop_path(src, dst, links)
        path_cache[(src, dst)] = p
        return p
    
    results = []
    total_packets = 0
    delivered_packets = 0
    
    for fdict in flows_raw:
        flow_name = fdict.get("name", "flow")
        s_id = fdict.get("sourceId", "src")
        d_id = fdict.get("destId", "dst")
        interval_s = parse_time_to_seconds(fdict.get("interval", "200us"))
        pkt_bytes = parse_packet_size(fdict.get("packetSize", "1000B"))
        pcp = fdict.get("trafficClass", 0)  
        
        node_path = get_path(s_id, d_id)
        if len(node_path) < 2:
            continue
        
        t = 0.0
        pkt_index = 0
        while t <= sim_end:
            total_packets += 1
            pkt_index += 1
            gen_time = t  
            current_time = gen_time
            delivered = True
        
            for i in range(len(node_path) - 1):
                srcNode = node_path[i]
                dstNode = node_path[i+1]
                portinfo = find_port_and_speed(srcNode, dstNode, links, default_link_bps)
                if not portinfo:
                    delivered = False
                    break
                (portA, portB, link_bps) = portinfo
                
                base_time = max(current_time, next_free_time[srcNode][portA][pcp])
                gsch = get_gate_schedule(srcNode, portA, pcp)
                if gsch is not None:
                    gate_open_time = gsch.next_open_time(base_time)
                else:
                    gate_open_time = base_time
                start_tx = max(base_time, gate_open_time)
                tx_time = (pkt_bytes * 8.0) / link_bps
                finish_tx = start_tx + tx_time
                if finish_tx > sim_end:
                    delivered = False
                    break
                next_free_time[srcNode][portA][pcp] = finish_tx
                current_time = finish_tx  
            if delivered and current_time <= sim_end:
                delivered_packets += 1
                delay = current_time - gen_time
                results.append((flow_name, gen_time, current_time, delay))
            t += interval_s

    stream_delays = {}
    for (flowName, genTime, arrivalTime, delay) in results:
        if flowName not in stream_delays:
            stream_delays[flowName] = []
        stream_delays[flowName].append(delay * 1000.0)  # in ms
    
    fig, ax = plt.subplots(figsize=(8,4))
    bins = 30
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, (flowName, delays_ms) in enumerate(sorted(stream_delays.items())):
        ax.hist(delays_ms, bins=bins, alpha=0.6, 
                color=colors[i % len(colors)], label=f"Stream {flowName}")
    
    ax.set_xlabel("End-to-End Delay (ms)")
    ax.set_ylabel("Number of Packets")
    total_delivered = sum(len(v) for v in stream_delays.values())
    ax.grid(True)
    ax.legend()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf
