terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "sciback-ops-tfstate"
    region = "us-east-1"   # Virginia — labs/infra interna SciBack
    # key se pasa en tiempo de init: -backend-config="key=<client>/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# ── VPC ───────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "sciback-odoo-${var.client_slug}" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = false

  tags = { Name = "sciback-odoo-${var.client_slug}-public" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = { Name = "sciback-odoo-${var.client_slug}-private-a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = "${var.aws_region}b"

  tags = { Name = "sciback-odoo-${var.client_slug}-private-b" }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "sciback-odoo-${var.client_slug}-igw" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = { Name = "sciback-odoo-${var.client_slug}-rt-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ── Security Groups ───────────────────────────────────────────

resource "aws_security_group" "ec2" {
  name        = "sciback-odoo-${var.client_slug}-ec2"
  description = "EC2 Odoo — solo HTTP/HTTPS y SSM"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "sciback-odoo-${var.client_slug}-ec2-sg" }
}

resource "aws_security_group" "rds" {
  name        = "sciback-odoo-${var.client_slug}-rds"
  description = "RDS PostgreSQL — solo desde EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "sciback-odoo-${var.client_slug}-rds-sg" }
}

# ── EC2 ───────────────────────────────────────────────────────

data "aws_ami" "ubuntu_22" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_iam_instance_profile" "odoo" {
  name = "sciback-odoo-${var.client_slug}-profile"
  role = aws_iam_role.odoo.name
}

resource "aws_iam_role" "odoo" {
  name = "sciback-odoo-${var.client_slug}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.odoo.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.odoo.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess" # refinar a bucket específico en producción
}

resource "aws_iam_role_policy_attachment" "secrets" {
  role       = aws_iam_role.odoo.name
  policy_arn = "arn:aws:iam::aws:policy/SecretsManagerReadWrite" # refinar a secretos del cliente
}

resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.odoo.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_instance" "odoo" {
  ami                    = data.aws_ami.ubuntu_22.id
  instance_type          = local.config.ec2_instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.odoo.name

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
  }

  ebs_block_device {
    device_name = "/dev/sdb"
    volume_type = "gp3"
    volume_size = local.config.ebs_size_gb
    encrypted   = true

    tags = { Name = "sciback-odoo-${var.client_slug}-data" }
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 obligatorio
  }

  tags = { Name = "sciback-odoo-${var.client_slug}" }
}

resource "aws_eip" "odoo" {
  instance = aws_instance.odoo.id
  domain   = "vpc"

  tags = { Name = "sciback-odoo-${var.client_slug}-eip" }
}

# ── RDS PostgreSQL ────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "sciback-odoo-${var.client_slug}"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = { Name = "sciback-odoo-${var.client_slug}-db-subnet" }
}

resource "aws_db_instance" "postgres" {
  identifier             = "sciback-odoo-${var.client_slug}"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = local.config.rds_instance_type
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_type           = "gp2"
  storage_encrypted      = true
  db_name                = "sciback_school"
  username               = "odoo"
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = local.config.rds_multi_az
  publicly_accessible    = false
  deletion_protection    = true
  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "sciback-odoo-${var.client_slug}-final"

  tags = { Name = "sciback-odoo-${var.client_slug}" }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

# ── S3 ────────────────────────────────────────────────────────

resource "aws_s3_bucket" "adjuntos" {
  bucket = "sciback-odoo-${var.client_slug}-adjuntos"

  tags = { Name = "sciback-odoo-${var.client_slug}-adjuntos" }
}

resource "aws_s3_bucket_versioning" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "adjuntos" {
  bucket = aws_s3_bucket.adjuntos.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "backups" {
  bucket = "sciback-odoo-${var.client_slug}-backups"

  tags = { Name = "sciback-odoo-${var.client_slug}-backups" }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "glacier-after-30-days"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }
  }
}

# ── Secrets Manager ───────────────────────────────────────────

resource "aws_secretsmanager_secret" "odoo" {
  name                    = "sciback-odoo/${var.client_slug}/odoo"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "odoo" {
  secret_id = aws_secretsmanager_secret.odoo.id
  secret_string = jsonencode({
    master_password = random_password.master.result
    db_password     = random_password.db.result
    db_host         = aws_db_instance.postgres.address
    db_port         = "5432"
    db_name         = "sciback_school"
    db_user         = "odoo"
    s3_adjuntos     = aws_s3_bucket.adjuntos.id
    s3_backups      = aws_s3_bucket.backups.id
  })
}

resource "random_password" "master" {
  length  = 32
  special = false
}

# ── CloudWatch Alarms ─────────────────────────────────────────

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "sciback-odoo-${var.client_slug}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "CPU > 80% por 10 minutos"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.odoo.id
  }
}

resource "aws_sns_topic" "alerts" {
  name = "sciback-odoo-${var.client_slug}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
