Vagrant.configure("2") do |config|

  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.box = "ubuntu/jammy64"

  config.vm.define "control" do |control|
    control.vm.hostname = "shellter-control"
    control.vm.network "private_network", ip: "192.168.56.10"
    control.vm.provider "virtualbox" do |vb|
      vb.memory = 1024
      vb.cpus = 1
    end
  end

  config.vm.define "db" do |db|
    db.vm.box = "ubuntu/jammy64"
    db.vm.hostname = "shellter-db"
    db.vm.network "private_network", ip: "192.168.56.11"
    db.vm.provider "virtualbox" do |vb|
      vb.memory = 1024
      vb.cpus = 1
    end
  end

end