
// SPDX-License-Identifier: LGPL-3.0-or-later
package inet.networks.tsn;

import inet.networks.base.TsnNetworkBase;
import inet.node.contract.IEthernetNetworkNode;
import inet.node.ethernet.EthernetLink;

network TsnZonedNetwork extends TsnNetworkBase
{
    parameters:
        *.eth[*].bitrate = default(100Mbps);

    submodules:
        
        switch_2: <default("TsnSwitch")> like IEthernetNetworkNode {
            @display("p=355.98960876464844,258.125");
        }
        
        switch_3: <default("TsnSwitch")> like IEthernetNetworkNode {
            @display("p=467.8993377685547,128.26388549804688");
        }
        
        device_4: <default("TsnSwitch")> like IEthernetNetworkNode {
            @display("p=743.9062957763672,272.2743225097656");
        }
        
    connections allowunconnected:
        
        device_4.ethg++ <--> EthernetLink <--> switch_3.ethg++;
        
        switch_2.ethg++ <--> EthernetLink <--> switch_3.ethg++;
        
}