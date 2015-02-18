# -*- mode: ruby -*-
# vi: set ft=ruby :

# Documentation: https://docs.vagrantup.com.

# The "2" is the configuration version. Do not change.
Vagrant.configure(2) do |config|

  config.vm.box = "chef/debian-7.6"

  config.vm.hostname = "medley"

  # Create a public (bridged) network so that the VM is reachable
  # through mDNS
  config.vm.network "public_network"

  # There are no shared folders between the guest and host
  config.vm.synced_folder "../data", "/vagrant_data"

  # Provider-specific configuration for RAM and hostname
  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = "256"
    vb.name = "medley"
  end

  # Customize the name displayed in VirtualBox
  config.vm.define "medley" do |medley|
  end

  # Use ansible for provisioning
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/provision.yml"
    ansible.extra_vars = {
      ansible_ssh_user: "vagrant"
    }
  end

end
