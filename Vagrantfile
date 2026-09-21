Vagrant.configure("2") do |config|

  config.vm.box = "ubuntu/jammy64"

  config.vm.define "control" do |control|

    control.vm.hostname = "shellter-control"

    control.vm.network "private_network",
      ip: "192.168.56.10"

    control.vm.provider "virtualbox" do |vb|
      vb.memory = 1024
      vb.cpus = 1
    end

  end

end