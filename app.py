from flask import Flask, render_template, request, make_response, jsonify, send_file
import io
import zipfile
import datetime
import subprocess
import os
import recommendation
import delay_calculation

import importlib
import traceback

app = Flask(__name__)
saved_config = None

# ---------------------------------------------------------------------
# P. Karimi @ TUE
# ---------------------------------------------------------------------

# Path to OMNET++ and INET files (Should be completed before running)

INI_FILE_PATH = r".........\inet4.5\showcases\tsn\trafficshaping\timeawareshaper\omnetpp.ini"
NED_PATH = r"...........\inet4.5\src"
INET_LIB_PATH = r".............\inet4.5\src\INET"

OPP_RUN_PATH = r"............\omnetpp-6.0.3\bin\opp_run.exe"
OMNET_QT_BIN = r".............\omnetpp-6.0.3\tools\win32.x86_64\opt\mingw64\bin"
OMNET_BIN = r".................\omnetpp-6.0.3\bin"
QT_PLUGIN_PATH = r".............\omnetpp-6.0.3\tools\win32.x86_64\opt\mingw64\plugins"

RESULTS_FOLDER = r".................\inet4.5\showcases\tsn\trafficshaping\timeawareshaper"
SCA_FILE = "results.sca"
VEC_FILE = "results.vec"

ANF_FILE = os.path.join(RESULTS_FOLDER, "TimeAwareShaperShowcase.anf")
CHART_OUTPUT_FOLDER = RESULTS_FOLDER
OPP_CHARTTOOL_PATH = r"..............\omnetpp-6.0.3\bin\opp_charttool.py"
OMNET_PYTHON_PATH = r"................\omnetpp-6.0.3\python"
PROJECT_MAPPING = r"......................\inet4.5"
WORKSPACE_DIR = r"........................\inet4.5"

@app.route('/')
def home():
    return render_template('design.html')

@app.route('/export', methods=['POST'])
def export():
    global saved_config
    data = request.get_json()
    saved_config = data
    nodes = data.get('nodes', [])
    links = data.get('links', [])
    flows = data.get('flows', [])
    global_config = data.get('globalConfig', {})

    ned_content = generate_ned_file(nodes, links, global_config)
    ini_content = generate_ini_file(nodes, links, flows, global_config)

    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("TsnZonedNetwork.ned", ned_content)
        zf.writestr("omnetpp.ini", ini_content)

    mem_zip.seek(0)
    response = make_response(mem_zip.read())
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Disposition'] = f'attachment; filename=tsn_project_{now}.zip'
    return response

@app.route('/simulate', methods=['POST'])
def simulate():
    global saved_config
    data = request.get_json()
    saved_config = data
    nodes = data.get('nodes', [])
    links = data.get('links', [])
    flows = data.get('flows', [])
    global_config = data.get('globalConfig', {})
    ned_content = generate_ned_file(nodes, links, global_config)
    ini_content = generate_ini_file(nodes, links, flows, global_config)

    try:
        with open(INI_FILE_PATH, 'w') as ini_file:
            ini_file.write(ini_content)
    except Exception as e:
        return jsonify({"error": f"Failed to write INI file: {str(e)}"}), 500

    network_name = global_config.get('networkName', 'TsnLinearNetwork')
    ned_subfolder = os.path.join(NED_PATH, "inet", "networks", "tsn")
    os.makedirs(ned_subfolder, exist_ok=True)
    ned_file_full_path = os.path.join(ned_subfolder, f"{network_name}.ned")
    with open(ned_file_full_path, 'w') as ned_file:
        ned_file.write(ned_content)

    env = os.environ.copy()
    env["PATH"] = f"{OMNET_QT_BIN};{OMNET_BIN};" + env["PATH"]
    env["QT_PLUGIN_PATH"] = QT_PLUGIN_PATH

    cmd = (
        f'cmd.exe /C "set PATH={OMNET_QT_BIN};{OMNET_BIN};%PATH% && '
        f'"{OPP_RUN_PATH}" -u Cmdenv -f "{INI_FILE_PATH}" -n "{NED_PATH}" -l "{INET_LIB_PATH}""'
    )
    print("Executing simulation command:", cmd)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                cwd=OMNET_BIN, env=env, timeout=300)
        output = {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        return jsonify(output)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/all_charts', methods=['GET'])
def all_charts():
    env = os.environ.copy()
    env["PYTHONPATH"] = OMNET_PYTHON_PATH
    env["PATH"] = OMNET_BIN + ";" + env.get("PATH", "")

    cmd_info = ["python", OPP_CHARTTOOL_PATH, "info", ANF_FILE]
    try:
        result_info = subprocess.run(cmd_info, env=env, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"opp_charttool info failed: {str(e)}"}), 500

    lines = result_info.stdout.splitlines()
    chart_indices = []
    for line in lines:
        line = line.strip()
        if line and line[0].isdigit():
            idx_str = line.split(".")[0]
            if idx_str.isdigit():
                chart_indices.append(int(idx_str))

    filenames = []
    i = 6
    out_filename = f"chart{i}.png"
    cmd_export = [
        "python", OPP_CHARTTOOL_PATH,
        "imageexport",
        "-f", "png",
        "-d", RESULTS_FOLDER,
        "-i", str(i),
        "-o", f"chart{i}",
        "-p", PROJECT_MAPPING,
        "-w", WORKSPACE_DIR,
        ANF_FILE
    ]
    try:
        subprocess.run(cmd_export, env=env, check=True)
        filenames.append(out_filename)
    except subprocess.CalledProcessError as e:
        print(f"Chart {i} export failed: {e}")
    return jsonify(filenames)

@app.route('/chart_image/<filename>')
def chart_image(filename):
    path = os.path.join(RESULTS_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, mimetype="image/png")

@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    app_name = data.get("appName", "")
    if not app_name:
        return jsonify({"error": "No application name provided"}), 400
    topology = recommendation.generate_recommended_topology(app_name)
    return jsonify(topology)

@app.route('/calc_delay', methods=['POST'])
def calc_delay():
    global saved_config
    data = request.get_json()
    saved_config = data
    return jsonify({"message": "Delay config stored OK"})

@app.route('/delay_calculation')
def delay_calculation_page():
    return render_template('delay.html')

@app.route('/delay_plot')
def delay_plot():
    global saved_config
    if not saved_config:
        return "No configuration available. Please set up your topology first.", 400

    chosen = PERFORMANCE_MODEL_STATE['selected']
    if chosen == "TAS-delay-calculation":
        buf = delay_calculation.generate_delay_plot(saved_config)
        return send_file(buf, mimetype='image/png')
    else:
        try:
            plugin_module = importlib.import_module(chosen)
            buf = plugin_module.generate_delay_plot(saved_config)
            return send_file(buf, mimetype='image/png')
        except Exception as ex:
            traceback.print_exc()
            return f"Error running custom performance model '{chosen}': {str(ex)}", 500


@app.route("/run_tas_scheduler", methods=["POST"])
def run_tas_scheduler():
    from drl_tas_runner import run_drl_scheduler

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    flows = data.get("flows", [])
    temp_csv = "temp_drl_scenario.csv"
    export_flows_to_csv(flows, temp_csv)


    chosen_sched = SCHEDULER_STATE['selected']
    if chosen_sched == "TAS-scheduler":
        try:
            gcl_output = run_drl_scheduler(temp_csv)
            return jsonify({"gcl": gcl_output})
        except Exception as ex:
            return jsonify({"error": str(ex)}), 500
    else:
        try:
            plugin_module = importlib.import_module(chosen_sched)
            gcl_output = plugin_module.run_drl_scheduler(temp_csv)
            return jsonify({"gcl": gcl_output})
        except Exception as ex:
            traceback.print_exc()
            return jsonify({"error": f"Error in custom scheduler '{chosen_sched}': {ex}"}), 500

def export_flows_to_csv(flows, csv_path):
    import csv
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "talker", "listener", "frame_size", "period", "deadline", "release_time", "queue"])
        for i, flow in enumerate(flows):
            sid = flow.get("sourceId", f"unknownSrc_{i}")
            did = flow.get("destId", f"unknownDst_{i}")
            pkt_size_str = flow.get("packetSize", "1000B")
            try:
                pkt_size_val = int(pkt_size_str.lower().replace("b",""))
            except:
                pkt_size_val = 1000
            period_val = 1.0
            deadline_val = 2.0
            release_val = 0.0
            queue_val = flow.get("trafficClass", 0)
            writer.writerow([i, sid, did, pkt_size_val, period_val, deadline_val, release_val, queue_val])


PERFORMANCE_MODEL_STATE = {
    "selected": "TAS-delay-calculation",  
    "plugins": ["TAS-delay-calculation"]  
}
SCHEDULER_STATE = {
    "selected": "TAS-scheduler",  
    "plugins": ["TAS-scheduler"]  
}


@app.route('/get_default_performance_code', methods=['GET'])
def get_default_performance_code():
    try:
        with open("delay_calculation.py", "r", encoding="utf-8") as f:
            code = f.read()
        return jsonify({"code": code})
    except:
        return jsonify({"error":"Could not read delay_calculation.py"}), 500


@app.route('/get_default_scheduler_code', methods=['GET'])
def get_default_scheduler_code():
    try:
        with open("drl_tas_runner.py", "r", encoding="utf-8") as f:
            code = f.read()
        return jsonify({"code": code})
    except:
        return jsonify({"error":"Could not read drl_tas_runner.py"}), 500


@app.route('/add_performance_plugin', methods=['POST'])
def add_performance_plugin():
    data = request.json
    plugin_name = data.get('pluginName', '').strip()
    plugin_code = data.get('pluginCode', '')
    if not plugin_name:
        return jsonify({"error":"No plugin name provided"}), 400

    filename = f"{plugin_name}.py"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(plugin_code)

        if plugin_name not in PERFORMANCE_MODEL_STATE["plugins"]:
            PERFORMANCE_MODEL_STATE["plugins"].append(plugin_name)
        return jsonify({"message": f"Plugin '{plugin_name}' added successfully."})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route('/select_performance_model', methods=['POST'])
def select_performance_model():
    data = request.json
    plugin_name = data.get('pluginName','')
    if not plugin_name:
        return jsonify({"error":"No plugin name provided"}), 400
    if plugin_name not in PERFORMANCE_MODEL_STATE["plugins"]:
        return jsonify({"error": f"Plugin '{plugin_name}' not in known plugins."}), 400
    PERFORMANCE_MODEL_STATE['selected'] = plugin_name
    return jsonify({"message": f"Performance model set to '{plugin_name}'"})


@app.route('/list_performance_plugins', methods=['GET'])
def list_performance_plugins():
    return jsonify(PERFORMANCE_MODEL_STATE["plugins"])


@app.route('/add_scheduler_plugin', methods=['POST'])
def add_scheduler_plugin():
    data = request.json
    plugin_name = data.get('pluginName', '').strip()
    plugin_code = data.get('pluginCode', '')
    if not plugin_name:
        return jsonify({"error":"No plugin name provided"}), 400

    filename = f"{plugin_name}.py"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(plugin_code)

        if plugin_name not in SCHEDULER_STATE["plugins"]:
            SCHEDULER_STATE["plugins"].append(plugin_name)
        return jsonify({"message": f"Scheduler plugin '{plugin_name}' added successfully."})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@app.route('/select_scheduler', methods=['POST'])
def select_scheduler():
    data = request.json
    plugin_name = data.get('pluginName','')
    if not plugin_name:
        return jsonify({"error":"No plugin name provided"}), 400
    if plugin_name not in SCHEDULER_STATE["plugins"]:
        return jsonify({"error": f"Plugin '{plugin_name}' not in known schedulers."}), 400
    SCHEDULER_STATE['selected'] = plugin_name
    return jsonify({"message": f"Scheduler set to '{plugin_name}'"})


@app.route('/list_scheduler_plugins', methods=['GET'])
def list_scheduler_plugins():
    return jsonify(SCHEDULER_STATE["plugins"])

def generate_ned_file(nodes, links, global_config):
    network_name = global_config.get('networkName', 'TsnLinearNetwork')
    default_link_speed = global_config.get('defaultLinkSpeed', '100Mbps')
    port_counts = {}
    for node in nodes:
        port_counts[node["id"]] = 0

    for link in links:
        s_node = link["sourceNode"]
        t_node = link["targetNode"]
        s_port = link.get("sourcePort", 0)
        t_port = link.get("targetPort", 0)
        port_counts[s_node] = max(port_counts[s_node], s_port + 1)
        port_counts[t_node] = max(port_counts[t_node], t_port + 1)

    header = f"""// Generated TSN Network
package inet.networks.tsn;

import inet.networks.base.TsnNetworkBase;
import inet.node.contract.IEthernetNetworkNode;
import inet.node.ethernet.EthernetLink;

network {network_name} extends TsnNetworkBase
{{
    parameters:
        *.eth[*].bitrate = default({default_link_speed});
    submodules:
"""

    submodules = []
    for node in nodes:
        node_id = node["id"]
        node_type = node["type"]
        x = node.get("x", 100)
        y = node.get("y", 100)
        needed_gates = port_counts[node_id]

        submodules.append(
            f'        {node_id}: <default("{node_type}")> like IEthernetNetworkNode {{\n'
            f'            parameters:\n'
            f'                numEthInterfaces = {needed_gates};\n'
            f'            @display("p={x},{y}");\n'
            f'        }}'
        )

    connections = ["    connections:"]
    for link in links:
        s_node = link["sourceNode"]
        t_node = link["targetNode"]
        s_port = link.get("sourcePort", 0)
        t_port = link.get("targetPort", 0)
        connections.append(
            f'        {s_node}.ethg[{s_port}] <--> EthernetLink <--> {t_node}.ethg[{t_port}];'
        )

    ned_body = "\n".join(submodules) + "\n\n" + "\n".join(connections)
    footer = "\n}\n"
    return header + ned_body + footer

def generate_ini_file(nodes, links, flows, global_config):
    network_name = global_config.get('networkName', 'TsnLinearNetwork')
    sim_time_limit = global_config.get('defaultSimTime', '1s')
    lines = [
        "[General]",
        f"network = inet.networks.tsn.{network_name}",
        f"sim-time-limit = {sim_time_limit}",
        'description = "Traffic shaping using time-aware shapers"',
        "",
        "**.displayGateSchedules = true",
        "**.gateFilter = \"**.eth[1].**\"",
        "**.gateScheduleVisualizer.height = 16",
        "**.gateScheduleVisualizer.placementHint = \"top\"",
        "",
    ]

    node_types = {n["id"]: n["type"] for n in nodes}

    source_apps = {}
    sink_apps = {}
    port_counter = 1000
    for flow in flows:
        src = flow['sourceId']
        dst = flow['destId']
        flow_port = port_counter
        port_counter += 1
        source_apps.setdefault(src, []).append({
            'name': flow['name'],
            'destAddress': dst,
            'destPort': flow_port,
            'packetLength': flow['packetSize'],
            'productionInterval': flow['interval'],
            'trafficClass': flow['trafficClass']
        })
        sink_apps.setdefault(dst, []).append({
            'port': flow_port
        })

    for node in nodes:
        if node["type"] == "TsnDevice":
            node_id = node["id"]
            src_list = source_apps.get(node_id, [])
            sink_list = sink_apps.get(node_id, [])
            total_apps = len(src_list) + len(sink_list)
            if total_apps > 0:
                lines.append(f"*.{node_id}.numApps = {total_apps}")

            app_index = 0
            for app in src_list:
                lines.append(f"*.{node_id}.app[{app_index}].typename = \"UdpSourceApp\"")
                lines.append(f"*.{node_id}.app[{app_index}].display-name = \"{app['name']}\"")
                lines.append(f"*.{node_id}.app[{app_index}].io.destAddress = \"{app['destAddress']}\"")
                lines.append(f"*.{node_id}.app[{app_index}].io.destPort = {app['destPort']}")
                lines.append(f"*.{node_id}.app[{app_index}].source.packetLength = {app['packetLength']}")
                lines.append(f"*.{node_id}.app[{app_index}].source.productionInterval = {app['productionInterval']}")
                app_index += 1

            for s in sink_list:
                lines.append(f"*.{node_id}.app[{app_index}].typename = \"UdpSinkApp\"")
                lines.append(f"*.{node_id}.app[{app_index}].io.localPort = {s['port']}")
                app_index += 1

    for node in nodes:
        if node["type"] == "TsnDevice":
            dev_id = node["id"]
            lines.append(f"*.{dev_id}.hasOutgoingStreams = true")
            lines.append(f"*.{dev_id}.hasIncomingStreams = true")
            src_list = source_apps.get(dev_id, [])
            if src_list:
                id_map = []
                enc_map = []
                for app in src_list:
                    p = app["destPort"]
                    tc = app["trafficClass"]
                    nm = app["name"]
                    id_map.append(f'{{stream: "{nm}", packetFilter: expr(udp.destPort == {p})}}')
                    enc_map.append(f'{{stream: "{nm}", pcp: {tc}}}')

                lines.append(f"*.{dev_id}.bridging.streamIdentifier.identifier.mapping = [{', '.join(id_map)}]")
                lines.append(f"*.{dev_id}.bridging.streamCoder.encoder.mapping = [{', '.join(enc_map)}]")

    lines.append("**.macLayer.queue.collectPacketBitLifeTime = true")

    for node in nodes:
        if node["type"] == "TsnSwitch":
            node_id = node["id"]
            lines.append(f"*.{node_id}.hasEgressTrafficShaping = true")

    for node in nodes:
        if node["type"] == "TsnSwitch":
            node_id = node["id"]
            gcl = node.get("gclConfigs", [])
            if not gcl:
                lines.append(f"*.{node_id}.eth[*].macLayer.queue.numTrafficClasses = 8")
                lines.append(f"*.{node_id}.eth[*].macLayer.queue.transmissionGate[0].offset = 0ms")
                lines.append(f"*.{node_id}.eth[*].macLayer.queue.transmissionGate[0].durations = [4ms,6ms]")
                lines.append(f"*.{node_id}.eth[*].macLayer.queue.transmissionGate[1].offset = 6ms")
                lines.append(f"*.{node_id}.eth[*].macLayer.queue.transmissionGate[1].durations = [2ms,8ms]")
            else:
                for portConfig in gcl:
                    port_idx = portConfig.get("portIndex", 0)
                    num_tc = portConfig.get("numTrafficClasses", 2)
                    lines.append(f"*.{node_id}.eth[{port_idx}].macLayer.queue.numTrafficClasses = 8")
                    schedule_list = portConfig.get("schedule", [])
                    for sched_idx, sched in enumerate(schedule_list):
                        offset = sched.get("offset", "0ms")
                        durations = sched.get("durations", "[4ms,6ms]")
                        queue_index = sched.get("queueIndex", 0)

                        lines.append(f"*.{node_id}.eth[{port_idx}].macLayer.queue.transmissionGate[{queue_index}].offset = {offset}")
                        lines.append(f"*.{node_id}.eth[{port_idx}].macLayer.queue.transmissionGate[{queue_index}].durations = {durations}")

    return "\n".join(lines)

if __name__ == '__main__':
    app.run(debug=True)
