let nodes = [];
let links = [];
let flows = [];
let nodeCounter = 0;

let selectedNodeId = null;
let connectModeEnabled = false;
let selectedSourceNode = null;

let globalConfig = {
  defaultSimTime: "20ms",
  defaultLinkSpeed: "100Mbps"
};

window.onload = function() {
  document.getElementById("addSwitchBtn").onclick = () => addNode("TsnSwitch");
  document.getElementById("addDeviceBtn").onclick = () => addNode("TsnDevice");
  document.getElementById("connectModeBtn").onclick = () => toggleConnectMode();
  document.getElementById("configureNodeBtn").onclick = () => openSelectedNodeConfig();
  document.getElementById("flowsBtn").onclick = () => openFlowsModal();
  document.getElementById("linksBtn").onclick = () => openLinksModal();
  document.getElementById("globalConfigBtn").onclick = () => openGlobalConfigModal();
  document.getElementById("exportBtn").onclick = () => exportProject();
  document.getElementById("runSimBtn").onclick = () => runSimulation();
  document.getElementById("recommendAppBtn").onclick = () => openRecommendModal();

  document.getElementById("saveProjectBtn").onclick = saveProject;
  document.getElementById("loadProjectBtn").onclick = () => {
    document.getElementById("loadProjectFileInput").click();
  };
  document.getElementById("loadProjectFileInput").addEventListener("change", handleLoadFile);

  document.getElementById("choosePerformanceModelBtn").onclick = () => {
    refreshPerformanceModelList();
    showModal("choosePerformanceModelModal");
  };
  document.getElementById("runPerformanceModelBtn").onclick = runPerformanceModel;

  document.getElementById("chooseSchedulerBtn").onclick = () => {
    refreshSchedulerList();
    showModal("chooseSchedulerModal");
  };
  document.getElementById("runSchedulerBtn").onclick = runScheduler;
  document.getElementById("selectUseCaseBtn").onclick = () => showModal("useCaseModal");

};


function addNode(nodeType) {
  nodeCounter++;
  const nodeId = nodeType + "_" + nodeCounter;
  const nodeDiv = document.createElement("div");
  nodeDiv.id = nodeId;
  nodeDiv.className = "node";

  if (nodeType === "TsnSwitch") {
    nodeDiv.innerHTML = `
      <div style="text-align:center;">
        <img src="/static/images/switch.png" style="width:50px; height:50px;">
        <br>
        <span>${nodeId}</span>
      </div>
    `;
  } else if (nodeType === "TsnDevice") {
    nodeDiv.innerHTML = `
      <div style="text-align:center;">
        <img src="/static/images/device.png" style="width:50px; height:50px;">
        <br>
        <span>${nodeId}</span>
      </div>
    `;
  } else {
    nodeDiv.innerHTML = `<span>${nodeId}</span>`;
  }

  nodeDiv.style.backgroundColor = "transparent";
  nodeDiv.style.border = "none";

  nodeDiv.style.left = "50px";
  nodeDiv.style.top = (100 + nodeCounter * 30) + "px";
  nodeDiv.onmousedown = (e) => selectNode(nodeId, e);
  document.getElementById("canvas").appendChild(nodeDiv);

  nodes.push({
    id: nodeId,
    type: nodeType,
    x: 50,
    y: 100 + nodeCounter * 30,
    gclConfigs: []
  });

  makeDraggable(nodeDiv);
}

function selectNode(nodeId, e) {
  selectedNodeId = nodeId;
  document.querySelectorAll(".node").forEach(el => el.classList.remove("selected"));
  document.getElementById(nodeId).classList.add("selected");
  if (connectModeEnabled) {
    if (!selectedSourceNode) {
      selectedSourceNode = nodeId;
    } else {
      if (selectedSourceNode !== nodeId) {
        links.push({
          sourceNode: selectedSourceNode,
          sourcePort: 0,
          targetNode: nodeId,
          targetPort: 0,
          linkSpeed: globalConfig.defaultLinkSpeed
        });
        redrawAllLines();
      }
      selectedSourceNode = null;
    }
  }
  e.stopPropagation();
}

function toggleConnectMode() {
  connectModeEnabled = !connectModeEnabled;
  document.getElementById("connectModeBtn").style.backgroundColor = connectModeEnabled ? "lightgreen" : "";
  if (!connectModeEnabled) {
    selectedSourceNode = null;
  }
}

function makeDraggable(el) {
  let offsetX = 0;
  let offsetY = 0;
  let isDown = false;
  el.addEventListener("mousedown", function(e) {
    isDown = true;
    offsetX = el.offsetLeft - e.clientX;
    offsetY = el.offsetTop - e.clientY;
    el.style.zIndex = 9999;
    e.stopPropagation();
  });
  document.addEventListener("mouseup", function() {
    isDown = false;
    el.style.zIndex = 1;
  });
  document.addEventListener("mousemove", function(e) {
    if (isDown) {
      let newLeft = e.clientX + offsetX;
      let newTop = e.clientY + offsetY;
      el.style.left = newLeft + "px";
      el.style.top = newTop + "px";
      const nodeData = nodes.find(n => n.id === el.id);
      if (nodeData) {
        nodeData.x = newLeft;
        nodeData.y = newTop;
      }
      redrawAllLines();
    }
  });
}

function redrawAllLines() {
  document.querySelectorAll(".connection-line").forEach(el => el.remove());
  links.forEach(l => {
    drawLine(l.sourceNode, l.targetNode);
  });
}

function drawLine(sourceId, targetId) {
  const sEl = document.getElementById(sourceId);
  const tEl = document.getElementById(targetId);
  if (!sEl || !tEl) return;
  const x1 = sEl.offsetLeft + sEl.offsetWidth / 2;
  const y1 = sEl.offsetTop + sEl.offsetHeight / 2;
  const x2 = tEl.offsetLeft + tEl.offsetWidth / 2;
  const y2 = tEl.offsetTop + tEl.offsetHeight / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);
  const line = document.createElement("div");
  line.className = "connection-line";
  line.style.left = x1 + "px";
  line.style.top = y1 + "px";
  line.style.width = length + "px";
  line.style.transform = "rotate(" + angle + "deg)";
  document.getElementById("canvas").appendChild(line);
}


function openSelectedNodeConfig() {
  if (!selectedNodeId) {
    alert("No node selected!");
    return;
  }
  const node = nodes.find(n => n.id === selectedNodeId);
  if (!node) return;
  document.getElementById("nodeIdInput").value = node.id;
  document.getElementById("nodeTypeInput").value = node.type;
  if (node.type === "TsnSwitch") {
    document.getElementById("gclEditorSection").style.display = "block";
    buildGclEditor(node);
  } else {
    document.getElementById("gclEditorSection").style.display = "none";
  }
  showModal("nodeConfigModal");
}

function closeNodeConfigModal() {
  hideModal("nodeConfigModal");
}

function buildGclEditor(node) {
  const container = document.getElementById("gclPortsContainer");
  container.innerHTML = "";
  node.gclConfigs.forEach((gcl, idx) => {
    const portIndex = gcl.portIndex || 0;
    const numTC = gcl.numTrafficClasses || 3;
    const schedule = gcl.schedule || [];
    const card = document.createElement("div");
    card.className = "card mb-2 p-2";
    card.innerHTML = `
      <label>Port Index:</label>
      <input type="number" class="portIndexInput form-control mb-2" value="${portIndex}">
      <label>Num TCs:</label>
      <input type="number" class="numTcInput form-control mb-2" value="${numTC}">
      <hr>
      <div class="scheduleList"></div>
      <button class="btn btn-sm btn-outline-secondary addSchedBtn mt-2">Add Schedule Entry</button>
      <button class="btn btn-sm btn-outline-danger removePortBtn mt-2 float-right">Remove Port</button>
    `;
    container.appendChild(card);
    const sList = card.querySelector(".scheduleList");
    schedule.forEach(s => {
      const entryDiv = document.createElement("div");
      entryDiv.className = "form-row mb-2 scheduleItem";
      entryDiv.innerHTML = `
        <div class="col-4">
          <label class="col-form-label">Offset:</label>
          <input type="text" class="form-control offsetInput" value="${s.offset}">
        </div>
        <div class="col-4">
          <label class="col-form-label">Durations:</label>
          <input type="text" class="form-control durationsInput" value="${s.durations}">
        </div>
        <div class="col-4">
          <label class="col-form-label">QueueIndex:</label>
          <input type="number" class="form-control queueIndexInput" value="${s.queueIndex || 0}">
        </div>
      `;
      sList.appendChild(entryDiv);
    });
    const addSchedBtn = card.querySelector(".addSchedBtn");
    addSchedBtn.onclick = () => {
      const newDiv = document.createElement("div");
      newDiv.className = "form-row mb-2 scheduleItem";
      newDiv.innerHTML = `
        <div class="col-4">
          <label class="col-form-label">Offset:</label>
          <input type="text" class="form-control offsetInput" value="0ms">
        </div>
        <div class="col-4">
          <label class="col-form-label">Durations:</label>
          <input type="text" class="form-control durationsInput" value="[4ms,6ms]">
        </div>
        <div class="col-4">
          <label class="col-form-label">QueueIndex:</label>
          <input type="number" class="form-control queueIndexInput" value="0">
        </div>
      `;
      sList.appendChild(newDiv);
    };
    const removePortBtn = card.querySelector(".removePortBtn");
    removePortBtn.onclick = () => {
      node.gclConfigs.splice(idx, 1);
      buildGclEditor(node);
    };
  });
}

function addPortConfig() {
  const nodeId = document.getElementById("nodeIdInput").value;
  const node = nodes.find(n => n.id === nodeId);
  if (!node) return;
  node.gclConfigs.push({
    portIndex: 0,
    numTrafficClasses: 3,
    schedule: [
      { offset: "0ms", durations: "[4ms,6ms]", queueIndex: 0 }
    ]
  });
  buildGclEditor(node);
}

function saveNodeConfig() {
  const nodeId = document.getElementById("nodeIdInput").value;
  const node = nodes.find(n => n.id === nodeId);
  if (!node) return;
  if (node.type === "TsnSwitch") {
    const container = document.getElementById("gclPortsContainer");
    const cardEls = container.querySelectorAll(".card");
    let newConfigs = [];
    cardEls.forEach(cardEl => {
      const portIdx = parseInt(cardEl.querySelector(".portIndexInput").value) || 0;
      const numTC = parseInt(cardEl.querySelector(".numTcInput").value) || 3;
      const schedItems = cardEl.querySelectorAll(".scheduleItem");
      let schedule = [];
      schedItems.forEach(si => {
        const offVal = si.querySelector(".offsetInput").value;
        const durVal = si.querySelector(".durationsInput").value;
        const qIdx = parseInt(si.querySelector(".queueIndexInput").value) || 0;
        schedule.push({
          offset: offVal,
          durations: durVal,
          queueIndex: qIdx
        });
      });
      newConfigs.push({
        portIndex: portIdx,
        numTrafficClasses: numTC,
        schedule: schedule
      });
    });
    node.gclConfigs = newConfigs;
  }
  closeNodeConfigModal();
}

function openFlowsModal() {
  const deviceNodes = nodes.filter(n => n.type === "TsnDevice");
  const flowSource = document.getElementById("flowSource");
  const flowDestination = document.getElementById("flowDestination");
  flowSource.innerHTML = "";
  flowDestination.innerHTML = "";
  deviceNodes.forEach(d => {
    let op1 = document.createElement("option");
    op1.value = d.id;
    op1.text = d.id;
    flowSource.appendChild(op1);
    let op2 = document.createElement("option");
    op2.value = d.id;
    op2.text = d.id;
    flowDestination.appendChild(op2);
  });
  refreshFlowList();
  showModal("flowsModal");
}

function closeFlowsModal() {
  hideModal("flowsModal");
}

function addFlow() {
  const name = document.getElementById("flowName").value || ("Flow_" + flows.length);
  const sourceId = document.getElementById("flowSource").value;
  const destId = document.getElementById("flowDestination").value;
  const packetSize = document.getElementById("flowPacketSize").value;
  const interval = document.getElementById("flowInterval").value;
  const trafficClass = parseInt(document.getElementById("flowTrafficClass").value) || 0;
  if (sourceId === destId) {
    alert("Source and Destination must be different!");
    return;
  }
  flows.push({ name, sourceId, destId, packetSize, interval, trafficClass });
  refreshFlowList();
  document.getElementById("flowName").value = "";
}

function refreshFlowList() {
  const flowList = document.getElementById("flowList");
  flowList.innerHTML = "";
  flows.forEach((f, idx) => {
    const div = document.createElement("div");
    div.className = "alert alert-info p-2";
    div.style.fontSize = "0.9em";
    div.innerHTML = `
      <b>${f.name}</b>: ${f.sourceId} -> ${f.destId}, size=${f.packetSize}, interval=${f.interval}, class=${f.trafficClass}
      <button class="btn btn-sm btn-danger float-right">X</button>
    `;
    const btn = div.querySelector("button");
    btn.onclick = () => {
      flows.splice(idx, 1);
      refreshFlowList();
    };
    flowList.appendChild(div);
  });
}

function openLinksModal() {
  refreshLinksList();
  showModal("linksModal");
}

function closeLinksModal() {
  hideModal("linksModal");
}

function refreshLinksList() {
  const linksDiv = document.getElementById("linksList");
  linksDiv.innerHTML = "";
  links.forEach((l, idx) => {
    const row = document.createElement("div");
    row.className = "border p-2 mb-2";
    row.innerHTML = `
      <div><b>${l.sourceNode} [port:${l.sourcePort}]</b> -> <b>${l.targetNode} [port:${l.targetPort}]</b></div>
      <label>Source Port:</label>
      <input type="number" class="srcPortInput" value="${l.sourcePort}" style="width:80px;">
      <label>Target Port:</label>
      <input type="number" class="tgtPortInput" value="${l.targetPort}" style="width:80px;">
      <label>Link Speed:</label>
      <input type="text" class="linkSpeedInput" value="${l.linkSpeed}" style="width:100px;">
      <button class="btn btn-sm btn-danger float-right">Remove Link</button>
    `;
    linksDiv.appendChild(row);
    const removeBtn = row.querySelector("button");
    removeBtn.onclick = () => {
      links.splice(idx, 1);
      refreshLinksList();
      redrawAllLines();
    };
    const srcPortInp = row.querySelector(".srcPortInput");
    srcPortInp.onchange = () => { l.sourcePort = parseInt(srcPortInp.value) || 0; };
    const tgtPortInp = row.querySelector(".tgtPortInput");
    tgtPortInp.onchange = () => { l.targetPort = parseInt(tgtPortInp.value) || 0; };
    const linkSpdInp = row.querySelector(".linkSpeedInput");
    linkSpdInp.onchange = () => { l.linkSpeed = linkSpdInp.value; };
  });
}

function openGlobalConfigModal() {
  document.getElementById("globalSimTime").value = globalConfig.defaultSimTime;
  document.getElementById("globalLinkSpeed").value = globalConfig.defaultLinkSpeed;
  showModal("globalConfigModal");
}

function closeGlobalConfigModal() {
  hideModal("globalConfigModal");
}

function saveGlobalConfig() {
  globalConfig.defaultSimTime = document.getElementById("globalSimTime").value;
  globalConfig.defaultLinkSpeed = document.getElementById("globalLinkSpeed").value;
  closeGlobalConfigModal();
}

function exportProject() {
  const payload = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  fetch("/export", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  })
  .then(resp => resp.blob())
  .then(blob => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tsn_project.zip";
    a.click();
  })
  .catch(err => {
    console.error("Export error:", err);
    alert("Export failed. Check console.");
  });
}

function displaySimStatus(message) {
  displaySimResult(message);
}

function displaySimResult(message) {
  const simResultContent = document.getElementById("simResultContent");
  if (simResultContent) {
    simResultContent.innerText = message;
    showModal("simResultModal");
  }
}

function runSimulation() {
  const payload = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  displaySimStatus("Simulation started...");
  fetch("/simulate", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  })
  .then(resp => resp.json())
  .then(data => {
    if (data.error) {
      displaySimStatus("Simulation Error: " + data.error);
    } else {
      let resultText = "Simulation Completed.\nReturn Code: " + data.returncode +
                       "\n\nStandard Output:\n" + data.stdout +
                       "\n\nStandard Error:\n" + data.stderr;
      displaySimResult(resultText);
      localStorage.setItem("simLogs", resultText);
    }
  })
  .catch(err => {
    console.error("Simulation error:", err);
    displaySimStatus("Simulation failed. Check console for details.");
  });
}

function loadAllCharts() {
  const chartLoader    = document.getElementById("chartLoader");
  const chartContainer = document.getElementById("chartContainer");

  chartLoader.classList.remove("hidden");
  chartContainer.style.display = "none";
  chartContainer.innerHTML = "";

  fetch("/all_charts")
    .then(resp => resp.json())
    .then(chartFilenames => {
      if (!chartFilenames || chartFilenames.length === 0) {
        chartLoader.classList.add("hidden");
        chartContainer.style.display = "block";
        chartContainer.textContent = "No charts found.";
        return;
      }

      let imagesToLoad = chartFilenames.length;

      chartFilenames.forEach(filename => {
        const imgDiv = document.createElement("div");
        imgDiv.className = "col-md-4 chart-img";

        const img = document.createElement("img");
        img.className = "img-fluid";
        img.alt = "Chart Image";

        img.src = `/chart_image/${filename}?_=${Date.now()}`;

        img.onload = () => {
          imagesToLoad--;
          if (imagesToLoad === 0) {
            chartLoader.classList.add("hidden");
            chartContainer.style.display = "block";
          }
        };

        img.onerror = () => {
          console.error(`Error loading image ${filename}`);
          imagesToLoad--;
          if (imagesToLoad === 0) {
            chartLoader.classList.add("hidden");
            chartContainer.style.display = "block";
          }
        };

        imgDiv.appendChild(img);
        chartContainer.appendChild(imgDiv);
      });
    })
    .catch(err => {
      console.error("Error in /all_charts fetch:", err);
      chartLoader.classList.add("hidden");
      chartContainer.style.display = "block";
      chartContainer.textContent = "Failed to load charts. See console.";
    });
}

function openRecommendModal() {
  showModal("recommendModal");
}

function generateRecommendedTopology() {
  const select = document.getElementById("appSelect");
  const selectedApp = select.value;
  fetch("/recommend", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ appName: selectedApp })
  })
  .then(resp => resp.json())
  .then(data => {
    if(data.error){
      alert("Error: " + data.error);
      return;
    }
    loadTopologyFromRecommendation(data);
    hideModal("recommendModal");
  })
  .catch(err => {
    console.error("Error generating recommended topology:", err);
    alert("Error generating recommended topology. Check console.");
  });
}

function loadTopologyFromRecommendation(topology) {
  nodes = topology.nodes;
  links = topology.links;
  flows = topology.flows;
  globalConfig = topology.globalConfig;

  const canvas = document.getElementById("canvas");
  canvas.innerHTML = "";

  nodeCounter = nodes.length;

  nodes.forEach(node => {
    const nodeDiv = document.createElement("div");
    nodeDiv.id = node.id;
    nodeDiv.className = "node";

    if (node.type === "TsnSwitch") {
      nodeDiv.innerHTML = `
        <div style="text-align:center;">
          <img src="/static/images/switch.png" style="width:50px; height:50px;">
          <br>
          <span>${node.id}</span>
        </div>
      `;
    } else if (node.type === "TsnDevice") {
      nodeDiv.innerHTML = `
        <div style="text-align:center;">
          <img src="/static/images/device.png" style="width:50px; height:50px;">
          <br>
          <span>${node.id}</span>
        </div>
      `;
    } else {
      nodeDiv.innerHTML = `<span>${node.id}</span>`;
    }

    nodeDiv.style.backgroundColor = "transparent";
    nodeDiv.style.border = "none";

    nodeDiv.style.left = node.x + "px";
    nodeDiv.style.top = node.y + "px";
    nodeDiv.onmousedown = (ev) => selectNode(node.id, ev);
    canvas.appendChild(nodeDiv);
    makeDraggable(nodeDiv);
  });

  redrawAllLines();
}

function saveProject() {
  const data = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = 'insim_project.insim';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function handleLoadFile(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (evt) => {
    try {
      const loadedData = JSON.parse(evt.target.result);
      nodes = loadedData.nodes || [];
      links = loadedData.links || [];
      flows = loadedData.flows || [];
      globalConfig = loadedData.globalConfig || globalConfig;

      const canvas = document.getElementById("canvas");
      canvas.innerHTML = "";
      nodeCounter = nodes.length;

      nodes.forEach(node => {
        const nodeDiv = document.createElement("div");
        nodeDiv.id = node.id;
        nodeDiv.className = "node";

        if (node.type === "TsnSwitch") {
          nodeDiv.innerHTML = `
            <div style="text-align:center;">
              <img src="/static/images/switch.png" style="width:50px; height:50px;">
              <br>
              <span>${node.id}</span>
            </div>
          `;
        } else if (node.type === "TsnDevice") {
          nodeDiv.innerHTML = `
            <div style="text-align:center;">
              <img src="/static/images/device.png" style="width:50px; height:50px;">
              <br>
              <span>${node.id}</span>
            </div>
          `;
        } else {
          nodeDiv.innerHTML = `<span>${node.id}</span>`;
        }

        nodeDiv.style.backgroundColor = "transparent";
        nodeDiv.style.border = "none";

        nodeDiv.style.left = node.x + "px";
        nodeDiv.style.top = node.y + "px";
        nodeDiv.onmousedown = (ev) => selectNode(node.id, ev);
        canvas.appendChild(nodeDiv);
        makeDraggable(nodeDiv);
      });

      redrawAllLines();
      alert("Project loaded successfully!");
    } catch (err) {
      alert("Error reading file: " + err);
    }
  };
  reader.readAsText(file);
}


function runPerformanceModel() {
  const payload = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  fetch("/calc_delay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(resp => {
    if (!resp.ok) {
      throw new Error("Failed to store config for performance model");
    }
    window.location.href = "/delay_calculation";
  })
  .catch(err => {
    console.error("runPerformanceModel() error:", err);
    alert("Could not run performance model. Check console.");
  });
}

function refreshPerformanceModelList() {
  fetch("/list_performance_plugins")
    .then(r => r.json())
    .then(list => {
      const sel = document.getElementById("perfModelSelect");
      sel.innerHTML = "";
      list.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.text = name;
        sel.appendChild(opt);
      });
    })
    .catch(err => console.error(err));
}

function choosePerformanceModel() {
  const sel = document.getElementById("perfModelSelect");
  const chosen = sel.value;
  if (!chosen) {
    alert("No selection!");
    return;
  }
  fetch("/select_performance_model", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ pluginName: chosen })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      alert("Error: " + data.error);
      return;
    }
    alert(data.message);
    hideModal("choosePerformanceModelModal");
  })
  .catch(err => {
    console.error(err);
    alert("Failed to choose performance model. Check console.");
  });
}

function savePerformancePlugin() {
  const name = document.getElementById("perfPluginName").value.trim();
  const code = document.getElementById("perfPluginCode").value;
  if (!name) {
    alert("Please provide a plugin name.");
    return;
  }
  fetch("/add_performance_plugin", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ pluginName: name, pluginCode: code })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      alert("Error: " + data.error);
      return;
    }
    alert(data.message);
    hideModal("addPerformancePluginModal");
    refreshPerformanceModelList();
  })
  .catch(err => {
    console.error(err);
    alert("Failed to add performance plugin. Check console.");
  });
}

function showModalAddPerformance() {
  fetch("/get_default_performance_code")
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById("perfPluginCode").value = "Error reading default code.";
      } else {
        document.getElementById("perfPluginCode").value = data.code;
      }
    })
    .catch(err => {
      console.error(err);
      document.getElementById("perfPluginCode").value = "Error fetching default code.";
    });


  document.getElementById("perfPluginName").value = "";
}

function runScheduler() {
  const payload = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  fetch("/run_tas_scheduler", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  })
  .then(resp => resp.json())
  .then(data => {
    if(data.error){
      alert("Scheduler error: " + data.error);
      return;
    }
    const gcl = data.gcl;
    applyGCLSchedules(gcl);
    alert("Scheduler ran successfully. GCL configured!");
  })
  .catch(err => {
    console.error(err);
    alert("Failed to run scheduler. Check console.");
  });
}

function refreshSchedulerList() {
  fetch("/list_scheduler_plugins")
    .then(r => r.json())
    .then(list => {
      const sel = document.getElementById("schedulerSelect");
      sel.innerHTML = "";
      list.forEach(name => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.text = name;
        sel.appendChild(opt);
      });
    })
    .catch(err => console.error(err));
}

function chooseScheduler() {
  const sel = document.getElementById("schedulerSelect");
  const chosen = sel.value;
  if (!chosen) {
    alert("No selection!");
    return;
  }
  fetch("/select_scheduler", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ pluginName: chosen })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      alert("Error: " + data.error);
      return;
    }
    alert(data.message);
    hideModal("chooseSchedulerModal");
  })
  .catch(err => {
    console.error(err);
    alert("Failed to choose scheduler. Check console.");
  });
}

function saveSchedulerPlugin() {
  const name = document.getElementById("schedPluginName").value.trim();
  const code = document.getElementById("schedPluginCode").value;
  if (!name) {
    alert("Please provide a scheduler plugin name.");
    return;
  }
  fetch("/add_scheduler_plugin", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ pluginName: name, pluginCode: code })
  })
  .then(r => r.json())
  .then(data => {
    if (data.error) {
      alert("Error: " + data.error);
      return;
    }
    alert(data.message);
    hideModal("addSchedulerPluginModal");
    refreshSchedulerList();
  })
  .catch(err => {
    console.error(err);
    alert("Failed to add scheduler plugin. Check console.");
  });
}

function showModalAddScheduler() {
  fetch("/get_default_scheduler_code")
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById("schedPluginCode").value = "Error reading default scheduler code.";
      } else {
        document.getElementById("schedPluginCode").value = data.code;
      }
    })
    .catch(err => {
      console.error(err);
      document.getElementById("schedPluginCode").value = "Error fetching default scheduler code.";
    });

  document.getElementById("schedPluginName").value = "";
}

function applyGCLSchedules(gclData){
  gclData.forEach(entry => {
    const nObj = nodes.find(n => n.id === entry.nodeId);
    if(!nObj) return;
    if(!nObj.gclConfigs) nObj.gclConfigs = [];
    nObj.gclConfigs.push({
      portIndex: entry.portIndex,
      numTrafficClasses: entry.numTrafficClasses,
      schedule: entry.schedule
    });
  });
}

function showModal(id) {
  const el = document.getElementById(id);
  if (el) {

    if (id === 'addPerformancePluginModal') {
      showModalAddPerformance();  
    }
    else if (id === 'addSchedulerPluginModal') {
      showModalAddScheduler();
    }
    el.style.display = "block";
  }
}

function hideModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.style.display = "none";
  }
}



// -----------------------------------------------------------------------
// Lane Keeping Use Case
// -----------------------------------------------------------------------
function applyLaneKeepingUseCase() {
  hideModal("useCaseModal");

  const newData = {
    "nodes": [
      {
        "id": "Central_Switch",
        "type": "TsnSwitch",
        "x": 706,
        "y": 338,
        "gclConfigs": [
          {
            "portIndex": 0,
            "numTrafficClasses": 3,
            "schedule": [
              {
                "offset": "0ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 5
              },
              {
                "offset": "4ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 3
              }
            ]
          },
          {
            "portIndex": 2,
            "numTrafficClasses": 3,
            "schedule": [
              {
                "offset": "3ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 7
              }
            ]
          }
        ]
      },
      {
        "id": "Central_Computer",
        "type": "TsnDevice",
        "x": 704,
        "y": 260,
        "gclConfigs": []
      },
      {
        "id": "Zone_0_Switch",
        "type": "TsnSwitch",
        "x": 463,
        "y": 135,
        "gclConfigs": [
          {
            "portIndex": 0,
            "numTrafficClasses": 3,
            "schedule": [
              {
                "offset": "0ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 5
              }
            ]
          }
        ]
      },
      {
        "id": "Zone_0_Controller",
        "type": "TsnDevice",
        "x": 465,
        "y": 68,
        "gclConfigs": []
      },
      {
        "id": "Zone_0_Sensor0",
        "type": "TsnDevice",
        "x": 273,
        "y": 229,
        "gclConfigs": []
      },
      {
        "id": "Zone_0_Sensor1",
        "type": "TsnDevice",
        "x": 267,
        "y": 143,
        "gclConfigs": []
      },
      {
        "id": "Zone_0_Sensor2",
        "type": "TsnDevice",
        "x": 279,
        "y": 55,
        "gclConfigs": []
      },
      {
        "id": "Zone_1_Switch",
        "type": "TsnSwitch",
        "x": 485,
        "y": 390,
        "gclConfigs": [
          {
            "portIndex": 1,
            "numTrafficClasses": 3,
            "schedule": [
              {
                "offset": "3ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 7
              }
            ]
          }
        ]
      },
      {
        "id": "Zone_1_Controller",
        "type": "TsnDevice",
        "x": 480,
        "y": 321,
        "gclConfigs": []
      },
      {
        "id": "Zone_1_Sensor0",
        "type": "TsnDevice",
        "x": 273,
        "y": 473,
        "gclConfigs": []
      },
      {
        "id": "Zone_1_Sensor1",
        "type": "TsnDevice",
        "x": 274,
        "y": 408,
        "gclConfigs": []
      },
      {
        "id": "Zone_1_Sensor2",
        "type": "TsnDevice",
        "x": 272,
        "y": 338,
        "gclConfigs": []
      },
      {
        "id": "Zone_2_Switch",
        "type": "TsnSwitch",
        "x": 753,
        "y": 461,
        "gclConfigs": [
          {
            "portIndex": 0,
            "numTrafficClasses": 3,
            "schedule": [
              {
                "offset": "4ms",
                "durations": "[1ms,4ms]",
                "queueIndex": 3
              }
            ]
          }
        ]
      },
      {
        "id": "Zone_2_Controller",
        "type": "TsnDevice",
        "x": 904,
        "y": 460,
        "gclConfigs": []
      },
      {
        "id": "Zone_2_Sensor0",
        "type": "TsnDevice",
        "x": 640,
        "y": 532,
        "gclConfigs": []
      },
      {
        "id": "Zone_2_Sensor1",
        "type": "TsnDevice",
        "x": 779,
        "y": 532,
        "gclConfigs": []
      },
      {
        "id": "Zone_2_Sensor2",
        "type": "TsnDevice",
        "x": 906,
        "y": 535,
        "gclConfigs": []
      },
      {
        "id": "Zone_3_Switch",
        "type": "TsnSwitch",
        "x": 747,
        "y": 124,
        "gclConfigs": []
      },
      {
        "id": "Zone_3_Controller",
        "type": "TsnDevice",
        "x": 892,
        "y": 125,
        "gclConfigs": []
      },
      {
        "id": "Zone_3_Sensor0",
        "type": "TsnDevice",
        "x": 980,
        "y": 65,
        "gclConfigs": []
      },
      {
        "id": "Zone_3_Sensor1",
        "type": "TsnDevice",
        "x": 842,
        "y": 69,
        "gclConfigs": []
      },
      {
        "id": "Zone_3_Sensor2",
        "type": "TsnDevice",
        "x": 679,
        "y": 70,
        "gclConfigs": []
      },
      {
        "id": "Zone_4_Switch",
        "type": "TsnSwitch",
        "x": 1126,
        "y": 434,
        "gclConfigs": []
      },
      {
        "id": "Zone_4_Controller",
        "type": "TsnDevice",
        "x": 1129,
        "y": 370,
        "gclConfigs": []
      },
      {
        "id": "Zone_4_Sensor0",
        "type": "TsnDevice",
        "x": 1311,
        "y": 426,
        "gclConfigs": []
      },
      {
        "id": "Zone_4_Sensor1",
        "type": "TsnDevice",
        "x": 1242,
        "y": 505,
        "gclConfigs": []
      },
      {
        "id": "Zone_4_Sensor2",
        "type": "TsnDevice",
        "x": 1097,
        "y": 512,
        "gclConfigs": []
      },
      {
        "id": "Zone_5_Switch",
        "type": "TsnSwitch",
        "x": 1239,
        "y": 180,
        "gclConfigs": []
      },
      {
        "id": "Zone_5_Controller",
        "type": "TsnDevice",
        "x": 1236,
        "y": 240,
        "gclConfigs": []
      },
      {
        "id": "Zone_5_Sensor0",
        "type": "TsnDevice",
        "x": 1371,
        "y": 184,
        "gclConfigs": []
      },
      {
        "id": "Zone_5_Sensor1",
        "type": "TsnDevice",
        "x": 1193,
        "y": 75,
        "gclConfigs": []
      },
      {
        "id": "Zone_5_Sensor2",
        "type": "TsnDevice",
        "x": 1107,
        "y": 138,
        "gclConfigs": []
      }
    ],
    "links": [
      {
        "sourceNode": "Central_Switch",
        "targetNode": "Central_Computer",
        "sourcePort": 0,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Central_Switch",
        "targetNode": "Zone_0_Switch",
        "sourcePort": 1,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_0_Switch",
        "targetNode": "Zone_0_Controller",
        "sourcePort": 1,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_0_Sensor0",
        "targetNode": "Zone_0_Switch",
        "sourcePort": 0,
        "targetPort": 2,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_0_Sensor1",
        "targetNode": "Zone_0_Switch",
        "sourcePort": 0,
        "targetPort": 3,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_0_Sensor2",
        "targetNode": "Zone_0_Switch",
        "sourcePort": 0,
        "targetPort": 4,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_1_Switch",
        "targetNode": "Central_Switch",
        "sourcePort": 0,
        "targetPort": 2,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_1_Controller",
        "targetNode": "Zone_1_Switch",
        "sourcePort": 0,
        "targetPort": 1,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_1_Sensor0",
        "targetNode": "Zone_1_Switch",
        "sourcePort": 0,
        "targetPort": 2,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_1_Switch",
        "targetNode": "Zone_1_Sensor1",
        "sourcePort": 3,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_1_Sensor2",
        "targetNode": "Zone_1_Switch",
        "sourcePort": 0,
        "targetPort": 4,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_2_Switch",
        "targetNode": "Central_Switch",
        "sourcePort": 0,
        "targetPort": 3,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_2_Controller",
        "targetNode": "Zone_2_Switch",
        "sourcePort": 0,
        "targetPort": 1,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_2_Sensor0",
        "targetNode": "Zone_2_Switch",
        "sourcePort": 0,
        "targetPort": 2,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_2_Switch",
        "targetNode": "Zone_2_Sensor1",
        "sourcePort": 3,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_2_Switch",
        "targetNode": "Zone_2_Sensor2",
        "sourcePort": 4,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Central_Switch",
        "targetNode": "Zone_3_Switch",
        "sourcePort": 4,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_3_Switch",
        "targetNode": "Zone_3_Controller",
        "sourcePort": 1,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_3_Switch",
        "targetNode": "Zone_3_Sensor0",
        "sourcePort": 2,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_3_Switch",
        "targetNode": "Zone_3_Sensor1",
        "sourcePort": 3,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_3_Switch",
        "targetNode": "Zone_3_Sensor2",
        "sourcePort": 4,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Central_Switch",
        "targetNode": "Zone_4_Switch",
        "sourcePort": 5,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_4_Switch",
        "targetNode": "Zone_4_Controller",
        "sourcePort": 1,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_4_Switch",
        "targetNode": "Zone_4_Sensor0",
        "sourcePort": 2,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_4_Switch",
        "targetNode": "Zone_4_Sensor1",
        "sourcePort": 3,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_4_Switch",
        "targetNode": "Zone_4_Sensor2",
        "sourcePort": 4,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Central_Switch",
        "targetNode": "Zone_5_Switch",
        "sourcePort": 6,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_5_Switch",
        "targetNode": "Zone_5_Controller",
        "sourcePort": 1,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_5_Switch",
        "targetNode": "Zone_5_Sensor0",
        "sourcePort": 2,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_5_Switch",
        "targetNode": "Zone_5_Sensor1",
        "sourcePort": 3,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      },
      {
        "sourceNode": "Zone_5_Switch",
        "targetNode": "Zone_5_Sensor2",
        "sourcePort": 4,
        "targetPort": 0,
        "linkSpeed": "100Mbps"
      }
    ],
    "flows": [
      {
        "name": "Camera",
        "sourceId": "Zone_0_Sensor0",
        "destId": "Central_Computer",
        "packetSize": "1400B",
        "interval": "200us",
        "trafficClass": 5
      },
      {
        "name": "Streeing",
        "sourceId": "Central_Computer",
        "destId": "Zone_1_Controller",
        "packetSize": "200B",
        "interval": "200us",
        "trafficClass": 7
      },
      {
        "name": "Ultra",
        "sourceId": "Zone_2_Sensor0",
        "destId": "Central_Computer",
        "packetSize": "300B",
        "interval": "200us",
        "trafficClass": 3
      }
    ],
    "globalConfig": {
      "defaultSimTime": "20ms",
      "defaultLinkSpeed": "100Mbps"
    }
  };

  nodes = newData.nodes;
  links = newData.links;
  flows = newData.flows;
  globalConfig = newData.globalConfig || globalConfig;

  const canvas = document.getElementById("canvas");
  canvas.innerHTML = "";
  nodeCounter = nodes.length;

  nodes.forEach(n => {
    const nodeDiv = document.createElement("div");
    nodeDiv.id = n.id;
    nodeDiv.className = "node";

    if (n.type === "TsnSwitch") {
      nodeDiv.innerHTML = `
        <div style="text-align:center;">
          <img src="/static/images/switch.png" style="width:50px; height:50px;">
          <br>
          <span>${n.id}</span>
        </div>
      `;
    } else if (n.type === "TsnDevice") {
      nodeDiv.innerHTML = `
        <div style="text-align:center;">
          <img src="/static/images/device.png" style="width:50px; height:50px;">
          <br>
          <span>${n.id}</span>
        </div>
      `;
    } else {
      nodeDiv.innerHTML = `<span>${n.id}</span>`;
    }

    nodeDiv.style.backgroundColor = "transparent";
    nodeDiv.style.border = "none";

    nodeDiv.style.left = n.x + "px";
    nodeDiv.style.top = n.y + "px";
    nodeDiv.onmousedown = (ev) => selectNode(n.id, ev);
    canvas.appendChild(nodeDiv);
    makeDraggable(nodeDiv);
  });

  redrawAllLines();

  alert("Use Case loaded with your new GCL configurations!");
}

function runTASScheduling(){
  showModal("drlWaitModal");
  const payload = {
    nodes: nodes,
    links: links,
    flows: flows,
    globalConfig: globalConfig
  };
  fetch("/run_tas_scheduler", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  })
  .then(resp => resp.json())
  .then(data => {
    hideModal("drlWaitModal");
    if(data.error){
      alert("Scheduler error: " + data.error);
      return;
    }
    const gcl = data.gcl;
    applyGCLSchedules(gcl);
    alert("TAS successfully configured by DRL agent!");
  })
  .catch(err => {
    hideModal("drlWaitModal");
    console.error(err);
    alert("Failed to run DRL scheduling. See console.");
  });
}

function applyGCLSchedules(gclData){
  gclData.forEach(entry => {
    const nObj = nodes.find(n => n.id === entry.nodeId);
    if(!nObj) return;
    if(!nObj.gclConfigs) nObj.gclConfigs = [];
    nObj.gclConfigs.push({
      portIndex: entry.portIndex,
      numTrafficClasses: entry.numTrafficClasses,
      schedule: entry.schedule
    });
  });
}
