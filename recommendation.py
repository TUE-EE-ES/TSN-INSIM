
import os
import math
import re
import pandas as pd
from collections import defaultdict

# ---------------------------------------------------------------------
# P. Karimi @ TUE
# ---------------------------------------------------------------------

HERE               = os.path.dirname(os.path.abspath(__file__))
TOPO_FILE          = os.path.join(HERE, "topology.xlsx")  
STREAM_FILE        = os.path.join(HERE, "stream.xlsx")
DEFAULT_LINK_SPEED = "100Mbps"


def _canon(s: str) -> str:
    return re.sub(r'[\s\-]+', '_', s.strip()).lower()


def _is_switch(name: str) -> bool:
    return "switch" in name.lower()


def _next_port(switch, neighbour, switch_ports):
    if neighbour not in switch_ports[switch]:
        switch_ports[switch][neighbour] = len(switch_ports[switch])
    return switch_ports[switch][neighbour]



def generate_recommended_topology(app_name: str):
    if not os.path.exists(TOPO_FILE) or not os.path.exists(STREAM_FILE):
        raise FileNotFoundError("topology_clean.xlsx / stream_clean.xlsx not found")

    df_topo   = pd.read_excel(TOPO_FILE,   sheet_name=app_name)
    df_stream = pd.read_excel(STREAM_FILE, sheet_name=app_name)

    df_topo = df_topo[df_topo["Device"] != "Device"] 

    device_zone = {}
    links_seen  = set()
    edges       = []

    for _, row in df_topo.iterrows():
        a = row["Device"].strip()
        b = row["Connected to"].strip()
        z = row["Zone"].strip()

        device_zone.setdefault(a, z)
        device_zone.setdefault(b, "Central" if "Central" in b else z)

        ekey = frozenset({a, b})
        if ekey not in links_seen:
            links_seen.add(ekey)
            edges.append((a, b))

    devices = set(device_zone.keys())

    ZONE_POS = {
        "Front Left" : (930, 350),
        "Front Right": (930, 100),
        "Mid Left"   : (630,  50),
        "Mid Right"  : (630, 400),
        "Rear Left"  : (150, 350),
        "Rear Right" : (150, 100),
        "Central"    : (580, 230),
    }
    CENTRAL_SWITCH_POS = (630, 280)
    INSIDE_OFFSET = 80
    ROW_SPACING   = 50
    zone_counters = defaultdict(int)

    nodes = []
    for dev in sorted(devices, key=lambda d: (device_zone[d], d)):
        zone   = device_zone.get(dev, "Central")
        base_x, base_y = ZONE_POS.get(zone, (580, 230))

        if dev == "Central TSN Switch":
            x, y = CENTRAL_SWITCH_POS
        elif dev == "Central HPC":
            x, y = ZONE_POS["Central"]
        elif "Zonal Switch" in dev:
            x, y = base_x, base_y
        else:
            off_x = -INSIDE_OFFSET if base_x > 580 else INSIDE_OFFSET
            idx   = zone_counters[zone]
            zone_counters[zone] += 1
            x = base_x + off_x
            y = base_y + idx * ROW_SPACING

        nodes.append({
            "id"  : dev,
            "type": "TsnSwitch" if _is_switch(dev) else "TsnDevice",
            "x"   : x,
            "y"   : y,
            "gclConfigs": []
        })

    switch_ports = defaultdict(dict)
    links = []

    for a, b in edges:
        pa = _next_port(a, b, switch_ports) if _is_switch(a) else 0
        pb = _next_port(b, a, switch_ports) if _is_switch(b) else 0
        links.append({
            "sourceNode": a,
            "sourcePort": pa,
            "targetNode": b,
            "targetPort": pb,
            "linkSpeed" : DEFAULT_LINK_SPEED
        })

    canon2id = {_canon(n["id"]): n["id"] for n in nodes}

    flows = []
    for _, row in df_stream.iterrows():
        src_raw = row["Source Device"]
        dst_raw = row["Destination Device"]
        try:
            flows.append({
                "name"        : row["Stream Name"],
                "sourceId"    : canon2id[_canon(src_raw)],
                "destId"      : canon2id[_canon(dst_raw)],
                "packetSize"  : f'{int(row["Packet Size (Bytes)"])}B',
                "interval"    : row["Production Interval"],
                "trafficClass": int(row["Traffic Class"]),
            })
        except KeyError as miss:
            raise ValueError(
                f'Device “{miss.args[0]}” referenced in stream sheet '
                'but missing from topology'
            ) from None

    return {
        "nodes"       : nodes,
        "links"       : links,
        "flows"       : flows,
        "globalConfig": {
            "defaultSimTime" : "20ms",
            "defaultLinkSpeed": DEFAULT_LINK_SPEED,
            "networkName"     : "TsnZonedNetwork" 
        }
    }
