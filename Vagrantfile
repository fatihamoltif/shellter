Vagrant.configure("2") do |config|

  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.box = "ubuntu/jammy64"

  config.vm.define "control" do |control|
    control.vm.hostname = "shellter-control"
    control.vm.network "private_network", ip: "192.168.56.10"
    control.vm.network "forwarded_port", guest: 80, host: 8080
    control.vm.network "forwarded_port", guest: 443, host: 8443
    control.vm.provider "virtualbox" do |vb|
      vb.memory = 2048
      vb.cpus = 1
    end
  end

end