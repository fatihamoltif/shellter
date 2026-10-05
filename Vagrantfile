# Vagrantfile — Shellter
# Base importée depuis la branche de Fatiha (commit cae8254) pour permettre le test
# d'inventaire (ansible all -m ping).
#
# AJOUT P4 : config.ssh.insert_key = false
#   -> toutes les VM partagent la clé "insecure" de Vagrant. C'est le prérequis
#      supposé par l'inventaire Ansible (ansible/group_vars/all/main.yml), qui
#      utilise une seule clé pour joindre les 4 machines.
#   -> à répercuter dans la version de Fatiha lors de la fusion des branches.

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.ssh.insert_key = false

  config.vm.define "control" do |control|
    control.vm.hostname = "shellter-control"
    control.vm.network "private_network", ip: "192.168.56.10"
    control.vm.provider "virtualbox" do |vb|
      vb.memory = 1024
      vb.cpus = 1
    end
  end

  (1..3).each do |i|
    config.vm.define "worker#{i}" do |worker|
      worker.vm.hostname = "worker#{i}"
      worker.vm.network "private_network", ip: "192.168.56.#{10 + i}"
      worker.vm.provider "virtualbox" do |vb|
        vb.memory = 1024
        vb.cpus = 1
      end
    end
  end
end
