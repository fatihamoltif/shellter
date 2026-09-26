Vagrant.configure("2") do |config|

  config.vm.define "control" do |control|
    control.vm.box = "ubuntu/jammy64"
    control.vm.hostname = "shellter-control"
    control.vm.network "private_network", ip: "192.168.56.10"
    control.vm.provider "virtualbox" do |vb|
      vb.memory = 1024
      vb.cpus = 1
    end
  end

  config.vm.define "worker1" do |worker1|
    worker1.vm.box = "bento/ubuntu-22.04" # Image Ubuntu optimisée pour VMware
    worker1.vm.hostname = "worker1"
    worker1.vm.network "private_network", ip: "192.168.56.11"
    
    worker1.vm.provider "vmware_desktop" do |v|
      v.vmx["memsize"] = "1024"
      v.vmx["numvcpus"] = "1"
    end
  end

end
