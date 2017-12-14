# -*- mode: ruby -*-
# vi: set ft=ruby :

# Documentation: https://docs.vagrantup.com.

# The "2" is the configuration version. Do not change.
Vagrant.configure(2) do |config|

  # This box includes guest additions, but debian/jessie64 does not.
  config.vm.box = "debian/contrib-jessie64"


  config.vm.hostname = "medley"

  # Create a public (bridged) network so that the VM is reachable
  # through mDNS
  config.vm.network "public_network"


  config.vm.synced_folder ".", "/vagrant"

  config.vm.provider "virtualbox" do |vb|
    # The machine is headless.
    vb.gui = false

    vb.memory = "256"

    # The name displayed in the VirtualBox GUI.
    vb.name = "medley"
  end

  # Provision using ansible. Run ansible from the host.
  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "ansible/provision.yml"
    ansible.extra_vars = {
      ansible_user: "vagrant"
    }
  end

end
