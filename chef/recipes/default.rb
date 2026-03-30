# Wicked Zerg - Battle Simulation
# Phase 154: Chef

package 'python3'
package 'wine'

directory '/opt/wicked-zerg' do
  owner 'ubuntu'
  group 'ubuntu'
  mode '0755'
  action :create
end

git '/opt/wicked-zerg' do
  repository 'https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git'
  revision 'main'
  action :sync
end

systemd_unit 'wicked-zerg.service' do
  content <<-EOU
[Unit]
Description=Wicked Zerg SC2 Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/wicked-zerg
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
EOU
  action [:create, :enable, :start]
end
