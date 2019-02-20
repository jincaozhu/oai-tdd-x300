#!/usr/bin/env python

"""
FIXME describe USRP X300

use to test x300 with nexus5 tdd mode.

Use this profile to instantiate an experiment using Open Air Interface 5g nr 
(https://gitlab.eurecom.fr/oai/openairinterface5g/wikis/5g-nr-development-and-releases)
to realize an end-to-end SDR-based mobile network. This profile includes
the following resources:

  * SDR UE (d430 + USRP X300) running OAI ('rue1')
  * SDR eNodeB (d430 + USRP B210) running OAI ('enb1')


PhantomNet startup scripts automatically configure OAI for the
specific allocated resources.

Instructions:

Be sure to setup your SSH keys as outlined in the manual; it's better
to log in via a real SSH client to the nodes in your experiment.

The Open Air Interface source is located under /opt/oai on the enb1
and UE nodes.  It is mounted as a clone of a remote blockstore
(dataset) maintained by PhantomNet.  Feel free to change anything in
here, but be aware that your changes will not persist when your
experiment terminates.

To run OAI on eNB:

cd /opt/oai/openairinterface5g/

./targets/bin/init_nas_nos1 eNB

sudo ./targets/bin/lte-softmodem-nos1.Rel14 -O ./targets/PROJECTS/GENERIC-LTE-EPC/CONF/enb.band7.tm1.50PRB.usrpx310.conf


To run OAi on UE:

cd /opt/oai/openairinterface5g/

./targets/bin/init_nas_nos1 UE

sudo ./targets/bin/lte-softmodem-nos1.Rel14 -U  -C 2680000000 --ue-txgain 85 --ue-rxgain 87 --ue-scan-carrier -r50

"""

#
# Standard geni-lib/portal libraries
#
import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.emulab as elab
import geni.urn as URN

#
# PhantomNet extensions.
#
import geni.rspec.emulab.pnext as PN

#
# Globals
#
class GLOBALS(object):
    OAI_NR_ENB_DS = "urn:publicid:IDN+emulab.net:powdersandbox+ltdataset+oai-nr-enb"
    OAI_NR_UE_DS = "urn:publicid:IDN+emulab.net:powdersandbox+ltdataset+oai-nr-ue"
    OAI_DS = "urn:publicid:IDN+emulab.net:phantomnet+ltdataset+oai-develop"
    UE_IMG  = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:ANDROID444-STD")
    ADB_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU14-64-PNTOOLS")
    OAI_EPC_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU16-64-OAIEPC")
    OAI_ENB_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:OAI-Real-Hardware.enb1")
    OAI_NR_IMG = "urn:publicid:IDN+emulab.net+image+PowderSandbox//OAI-NR"
    #OAI_NR_IMG = "urn:publicid:IDN+emulab.net+image+PowderSandbox:oai-nr_ue"
    #OAI_NR_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:UBUNTU14-64-OAI")
    #OAI_NR_IMG = URN.Image(PN.PNDEFS.PNET_AM, "PhantomNet:OAI-Real-Hardware.enb1")
    OAI_CONF_SCRIPT = "/usr/bin/sudo /local/repository/bin/config_oai.pl"
    NUC_HWTYPE = "d430"
    UE_HWTYPE = "nexus5"

def connectOAI_DS(node, type):
    # Create remote read-write clone dataset object bound to OAI dataset
    bs = request.RemoteBlockstore("ds-%s" % node.name, "/opt/oai")
    if type == 1:
	    bs.dataset = GLOBALS.OAI_DS
    else:
	    bs.dataset = GLOBALS.OAI_NR_UE_DS    
    bs.rwclone = True

    # Create link from node to OAI dataset rw clone
    node_if = node.addInterface("dsif_%s" % node.name)
    bslink = request.Link("dslink_%s" % node.name)
    bslink.addInterface(node_if)
    bslink.addInterface(bs.interface)
    bslink.vlan_tagging = True
    bslink.best_effort = True

#
# This geni-lib script is designed to run in the PhantomNet Portal.
#
pc = portal.Context()

#
# Profile parameters.
#
pc.defineParameter("FIXED_UE", "Bind to a specific UE",
                   portal.ParameterType.STRING, "",
                   longDescription="Input the name of a PhantomNet UE node to allocate (e.g., \'ue1\').  Leave blank to let the mapping algorithm choose.")
pc.defineParameter("FIXED_ENB", "Bind to a specific eNodeB",
                   portal.ParameterType.STRING, "",
                   longDescription="Input the name of a PhantomNet eNodeB device to allocate (e.g., \'nuc1\').  Leave blank to let the mapping algorithm choose.  If you bind both UE and eNodeB devices, mapping will fail unless there is path between them via the attenuator matrix.")

params = pc.bindParameters()

#
# Give the library a chance to return nice JSON-formatted exception(s) and/or
# warnings; this might sys.exit().
#
pc.verifyParameters()

#
# Create our in-memory model of the RSpec -- the resources we're going
# to request in our experiment, and their configuration.
#
request = pc.makeRequestRSpec()

# Add a node to act as the ADB target host
#adb_t = request.RawPC("adb-tgt")
#adb_t.disk_image = GLOBALS.ADB_IMG

# Add OAI EPC (HSS, MME, SPGW) node.
epc = request.RawPC("epc")
epc.disk_image = GLOBALS.OAI_EPC_IMG
epc.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r EPC"))
connectOAI_DS(epc,1)

# Add a NUC eNB node.
enb1 = request.RawPC("enb1")
if params.FIXED_ENB:
    enb1.component_id = params.FIXED_ENB
enb1.hardware_type = GLOBALS.NUC_HWTYPE
enb1.disk_image = GLOBALS.OAI_NR_IMG
connectOAI_DS(enb1,1)
enb1.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r ENB"))
#enb1_rue1_rf = enb1.addInterface("rue1_rf")
enb1_usrp_if = enb1.addInterface( "usrp_if" )
enb1_usrp_if.addAddress( rspec.IPv4Address( "192.168.30.1", "255.255.255.0" ) )

# Add a OAI UE node.
rue1 = request.RawPC("rue1")
if params.FIXED_ENB:
    rue1.component_id = params.FIXED_ENB
rue1.hardware_type = GLOBALS.NUC_HWTYPE
rue1.disk_image = GLOBALS.OAI_NR_IMG
connectOAI_DS(rue1,0)
rue1.addService(rspec.Execute(shell="sh", command=GLOBALS.OAI_CONF_SCRIPT + " -r ENB"))
#enb1_rue1_rf = enb1.addInterface("rue1_rf")
rue1_usrp_if = rue1.addInterface( "usrp_if" )
rue1_usrp_if.addAddress( rspec.IPv4Address( "192.168.30.1", "255.255.255.0" ) )

# Add an OTS (Nexus 5) UE
#rue1 = request.UE("rue1")
#if params.FIXED_UE:
#    rue1.component_id = params.FIXED_UE
#rue1.hardware_type = GLOBALS.UE_HWTYPE
#rue1.disk_image = GLOBALS.UE_IMG
#rue1.adb_target = "adb-tgt"
#rue1_enb1_rf = rue1.addInterface("enb1_rf")

# Create the RF link between the Nexus 5 UE and eNodeB
#rflink2 = request.RFLink("rflink2")
#rflink2.addInterface(enb1_rue1_rf)
#rflink2.addInterface(rue1_enb1_rf)

# Add X300 node.
usrp_enb = request.RawPC( "usrp_enb" )
usrp_enb.hardware_type = "sdr"
usrp_enb.disk_image = URN.Image(PN.PNDEFS.PNET_AM, "emulab-ops:GENERICDEV-NOVLANS")
usrp_enb_if = usrp_enb.addInterface( "usrp-nuc" )
usrp_enb_if.addAddress( rspec.IPv4Address( "192.168.30.2", "255.255.255.0" ) )

usrplink_enb = request.Link( "usrp-sdr_enb" )
usrplink_enb.addInterface( enb1_usrp_if )
usrplink_enb.addInterface( usrp_enb_if )

usrp_ue = request.RawPC( "usrp_ue" )
usrp_ue.hardware_type = "sdr"
usrp_ue.disk_image = URN.Image(PN.PNDEFS.PNET_AM, "emulab-ops:GENERICDEV-NOVLANS")
usrp_ue_if = usrp_ue.addInterface( "usrp-nuc" )
usrp_ue_if.addAddress( rspec.IPv4Address( "192.168.30.2", "255.255.255.0" ) )

usrplink_ue = request.Link( "usrp-sdr_ue" )
usrplink_ue.addInterface( rue1_usrp_if )
usrplink_ue.addInterface( usrp_ue_if )


# Add a link connecting the NUC eNB and the OAI EPC node.
epclink = request.Link("s1-lan")
epclink.addNode(enb1)
epclink.addNode(epc)




#
# Print and go!
#
pc.printRequestRSpec(request)
