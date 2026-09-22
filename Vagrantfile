Vagrant.configure("2") do |config|
  config.vm.define "worker1" do |worker1|
    worker1.vm.box = "bento/ubuntu-22.04" # Image Ubuntu optimisée pour VMware
    worker1.vm.hostname = "worker1"
    worker1.vm.network "private_network", ip: "192.168.56.20"
    
    worker1.vm.provider "vmware_desktop" do |v|
      v.gui = true
      v.vmx["memsize"] = "1024"
      v.vmx["numvcpus"] = "1"
    end
  end
end
