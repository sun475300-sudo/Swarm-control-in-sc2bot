# Wicked Zerg - Battle Simulation Deployment
# Phase 153: Puppet

class sc2_bot {
  package { 'python3':
    ensure => present,
  }
  
  package { 'wine':
    ensure => present,
  }
  
  file { '/opt/wicked-zerg':
    ensure  => directory,
    owner   => 'ubuntu',
    group   => 'ubuntu',
    mode    => '0755',
  }
  
  file { '/etc/systemd/system/wicked-zerg.service':
    ensure  => file,
    content => template('sc2_bot/wicked-zerg.service.erb'),
  }
  
  service { 'wicked-zerg':
    ensure     => running,
    enable     => true,
    hasrestart => true,
  }
}

node 'bot-server' {
  include sc2_bot
}
