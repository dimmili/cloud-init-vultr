# This file is part of cloud-init. See LICENSE file for license information.

# Vultr metadata API
# https://www.vultr.com/metadata/

import pprint
import json

from cloudinit import log as logging
from cloudinit import net as cloudnet
from cloudinit import sources
from cloudinit import util
from cloudinit import url_helper

LOG = logging.getLogger(__name__)

BUILTIN_DS_CONFIG = {
    'metadata_url': 'http://169.254.169.254/v1.json',
    'dns_servers': ['10.61.10.10'],
    'retries': 10,
    'timeout': 1,
    'wait_retry': 1
}

class DataSourceVultr(sources.DataSource):
    dsname = 'Vultr'

    def __init__(self, sys_cfg, distro, paths):
        sources.DataSource.__init__(self, sys_cfg, distro, paths)
        self.distro = distro
        self.metadata = dict()
        self.ds_cfg = util.mergemanydict([
            util.get_cfg_by_path(sys_cfg, ["datasource", "Vultr"], {}),
            BUILTIN_DS_CONFIG])
        self.metadata_address = self.ds_cfg['metadata_url']
        self.retries = self.ds_cfg['retries']
        self.timeout = self.ds_cfg['timeout']
        self.wait_retry = self.ds_cfg['wait_retry']
        self.dns_servers = self.ds_cfg['dns_servers']
        self._network_config = None

    def _get_data(self):
        response = url_helper.readurl(self.metadata_address, timeout=self.timeout,
                                      sec_between=self.wait_retry,
                                      retries=self.retries)
        if not response.ok():
            raise RuntimeError("unable to read metadata at %s" % self.metadata_address)

        md = json.loads(response.contents.decode())

        LOG.debug("Vultr metadata: %s", pprint.pformat(md))

        self.metadata_full = md
        self.metadata['instance-id'] = md['instanceid']
        self.metadata['local-hostname'] = md['hostname']
        self.metadata['interfaces'] = md.get('interfaces')
        self.metadata['public-keys'] = md.get('public-keys')
        self.metadata['availability_zone'] = md.get('region', {}).get('EWR', 'unknown')

        return True

    @property
    def network_config(self):
        """Configure the networking. This needs to be done each boot, since
           the IP information may have changed due to snapshot and/or
           migration.
        """

        if self._network_config:
            return self._network_config

        interfaces = self.metadata.get('interfaces')

        if not interfaces:
            raise Exception("Unable to get meta-data from server....")

        # Convert Vultr network configuration to cloudinit.net format

        #    Example JSON:
        #    [
        #     {
        #         "ipv4": {
        #             "additional": [
        #                 {
        #                     "address": "192.0.2.3",
        #                     "netmask": "255.255.255.0"
        #                 }
        #             ],
        #             "address": "192.0.2.2",
        #             "gateway": "192.0.2.1",
        #             "netmask": "255.255.255.0"
        #         },
        #         "ipv6": {
        #             "additional": [
        #                 {
        #                     "network": "2001:0db8:0:2::",
        #                     "prefix": "64"
        #                 }
        #             ],
        #             "address": "2001:0db8:0:1:5428:d5ff:fe28:1910",
        #             "network": "2001:0db8:0:1::",
        #             "prefix": "64"
        #         },
        #         "mac": "00:00:00:00:00:00",
        #         "network-type": "public"
        #     },
        #     ......
        # ]

        nic_configs = []
        macs_to_nics = cloudnet.get_interfaces_by_mac()
        LOG.debug("nic mapping: %s", macs_to_nics)

        config = []
        for vultr_ip_dict in interfaces:
            mac = vultr_ip_dict["mac"]

            if mac not in macs_to_nics:
                raise ValueError("Did not find network interface on system "
                        "with mac '%s'. Cannot apply configuration: %s"
                        % (mac_address, nic))
            if_name = macs_to_nics[mac]  # if_name = string 'eth0', ...
            if_config= {
                    'type': 'physical',
                    'mac_address': mac,
                    'name': if_name,
                    'subnets': [{
                        'type': 'dhcp',
                        'control': 'auto',
                        }
                     ]
            }
            config.append(if_config)

            LOG.debug("nic '%s' configuration: %s", if_name, if_config)

        LOG.debug("added dns servers: %s", self.dns_servers)
        config.append({'type': 'nameserver', 'address': self.dns_servers})

        return {'version': 1, 'config': config}

# Used to match classes to dependencies
datasources = [
    (DataSourceVultr, (sources.DEP_FILESYSTEM, )),
]


# Return a list of data sources that match this set of dependencies
def get_datasource_list(depends):
    return sources.list_from_depends(depends, datasources)

# vi: ts=4 expandtab
