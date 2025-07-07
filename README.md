# TSN-INSIM
This repository contains the source code for the paper:

**INSIM: A Modular Simulation Platform for TSN-based In-Vehicle Networks**  

# 🔬 Reference
If you use this work, please cite:

M. Karimi, M. Nabi, A. Nelson, K. Goossens, and T. Basten, "INSIM: A Modular Simulation Platform for TSN-based In-Vehicle Networks," in *Proc. 2025 IEEE 102st Vehicular Technology Conf. (VTC2025-fall)*, Chengdu, China, October. 19–22, 2025.

# 📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

# 📄 Third Party License
# ✅ Bootstrap
This project uses and includes the Bootstrap library. The Bootstrap CSS file is located at: /static/css/bootstrap.min.css.
Bootstrap is published under the MIT License: https://github.com/twbs/bootstrap/blob/main/LICENSE.
If you use the INSIM software, you must comply with the Bootstrap license terms.

# ✅ OMNeT++ and INET Framework
For certain functionalities, this project can run OMNeT++ and the INET Framework on your machine (hosted environment).
This project does not publish or distribute the source code of OMNeT++ or INET, and does not include them.

If you want to use the OMNeT++ simulation features (which are optional components of INSIM), you need to Install OMNeT++ and the INET Framework separately on your host machine and configure the paths in app.py accordingly. INSIM will then run simulations by invoking the OMNeT++ shell.
If you wish to use this simulation functionality, you must follow the respective license terms of these tools:

OMNeT++: https://github.com/omnetpp/omnetpp/blob/master/doc/License
INET Framework: https://github.com/inet-framework/inet/blob/master/LICENSE.md

If you do not require OMNeT++ features, you can still use the core INSIM application by complying only with the INSIM and Bootstrap license.

Important: Responsibility for complying with all applicable third-party licenses lies solely with the user. You are responsible for ensuring your use of INSIM and any third-party components meets their respective license requirements.


# 📝 Abstract
In-vehicle networks (IVNs) are rapidly evolving to support increasingly complex automotive applications, demanding higher bandwidth and deterministic timing bounds. Time-Sensitive Networking (TSN) has emerged as a promising Ethernet-based technology that addresses these stringent requirements. However, evaluating TSN-based IVN strategies remains a challenge due to the lack of standardized benchmarks and simulation tools. This paper introduces INSIM, a modular simulation platform specifically designed for TSN-based IVNs, providing an intuitive graphical interface, an extensible plug-in architecture, and integrated benchmarking features. INSIM integrates analytical performance models and discrete-event simulations (as plug-ins), enhancing the workflow for engineers by refining topology design, adjusting parameters, conducting simulations, and assessing performance, while providing researchers with a flexible platform to plug in, analyze, and compare custom network resource managers or analytical performance models.

# 📬 Contact Us
For questions, comments, or collaborations, feel free to contact us: Mohammadparsa Karimi — m.karimi@tue.nl

# Acknowledgments
This work has received funding from the European Chips Joint Undertaking under Framework Partnership Agreement No 101139789 (HAL4SDV).