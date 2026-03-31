# SC2 Bot - Chef Recipe (default)
# Server provisioning: packages, user, directories, config, service

# ==================== Attributes ====================
# Override in attributes/default.rb or node JSON:
#   node['sc2bot']['version']     = 'latest'
#   node['sc2bot']['install_dir'] = '/opt/sc2bot'
#   node['sc2bot']['log_level']   = 'INFO'
#   node['sc2bot']['port']        = 5678
#   node['sc2bot']['replicas']    = 3

install_dir = node['sc2bot']['install_dir'] || '/opt/sc2bot'
sc2_version = node['sc2bot']['version']     || 'latest'
log_level   = node['sc2bot']['log_level']   || 'INFO'
sc2_port    = node['sc2bot']['port']        || 5678

# ==================== Packages ====================
%w[python3 python3-pip python3-venv docker.io curl git].each do |pkg|
  package pkg do
    action :install
  end
end

# ==================== User & Group ====================
group 'sc2bot' do
  action :create
end

user 'sc2bot' do
  comment  'SC2 Bot Service Account'
  home     install_dir
  shell    '/bin/bash'
  group    'sc2bot'
  system   true
  action   :create
end

# ==================== Directories ====================
[install_dir,
 "#{install_dir}/replays",
 "#{install_dir}/logs",
 "#{install_dir}/models"].each do |dir|
  directory dir do
    owner     'sc2bot'
    group     'sc2bot'
    mode      '0755'
    recursive true
    action    :create
  end
end

# ==================== Python Virtual Environment ====================
bash 'create_sc2bot_venv' do
  code    "python3 -m venv #{install_dir}/venv"
  user    'sc2bot'
  not_if  { ::File.exist?("#{install_dir}/venv/bin/activate") }
end

bash 'install_python_deps' do
  code    "#{install_dir}/venv/bin/pip install --upgrade pip burnysc2 aiohttp prometheus-client pyyaml"
  user    'sc2bot'
  action  :run
end

# ==================== Configuration Template ====================
template "#{install_dir}/config.yml" do
  source 'sc2bot_config.yml.erb'
  owner  'sc2bot'
  group  'sc2bot'
  mode   '0640'
  variables(
    env:        node.chef_environment,
    port:       sc2_port,
    log_level:  log_level,
    version:    sc2_version,
  )
  notifies :restart, 'service[sc2bot]', :delayed
end

# ==================== Systemd Service ====================
template '/etc/systemd/system/sc2bot.service' do
  source 'sc2bot.service.erb'
  owner  'root'
  group  'root'
  mode   '0644'
  variables(
    install_dir: install_dir,
    user:        'sc2bot',
  )
  notifies :run,     'execute[systemctl_daemon_reload]', :immediately
  notifies :restart, 'service[sc2bot]', :delayed
end

execute 'systemctl_daemon_reload' do
  command 'systemctl daemon-reload'
  action  :nothing
end

service 'sc2bot' do
  supports status: true, restart: true, reload: true
  action  [:enable, :start]
end
