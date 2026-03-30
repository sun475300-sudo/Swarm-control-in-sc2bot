# Wicked Zerg - Battle Simulation Infrastructure
# Phase 151: Terraform

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_instance" "sc2_bot_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  
  tags = {
    Name        = "WickedZerg-SC2-Bot"
    Environment = "production"
    Project     = "Swarm-Control"
  }
}

resource "aws_security_group" "sc2_bot_sg" {
  name        = "sc2-bot-security-group"
  description = "Security group for SC2 Bot"
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "server_ip" {
  value = aws_instance.sc2_bot_server.public_ip
}
