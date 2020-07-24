# cloud-init-vultr

Unofficial Vultr support for cloud-init

# Install

Copy DataSourceVultr.py to your cloud-init install sources/ and change `datasource_list` to `[Vultr]` in you cloud.cfg

Example:
```shell
wget https://raw.githubusercontent.com/dimmili/cloud-init-vultr/master/DataSourceVultr.py -O /usr/lib/python3.8/site-packages/cloudinit/sources/DataSourceVultr.py
```

And add/change in your `/etc/cloud/cloud.cfg`:
`datasource_list = [Vultr]`
