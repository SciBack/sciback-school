variable "client_slug" {
  description = "Identificador corto del cliente (ej: agua-viva, san-martin)"
  type        = string
}

variable "tier" {
  description = "Tier de dimensionamiento: pilot | small | medium | large"
  type        = string
  default     = "pilot"

  validation {
    condition     = contains(["pilot", "small", "medium", "large"], var.tier)
    error_message = "Tier debe ser: pilot, small, medium o large."
  }
}

variable "aws_region" {
  description = "Región AWS para el cliente (producción = us-east-2 Ohio)"
  type        = string
  default     = "us-east-2"
}

variable "domain" {
  description = "Dominio principal del cliente (ej: erp.aguaviva.edu.pe)"
  type        = string
}

variable "alert_email" {
  description = "Email para alertas de CloudWatch"
  type        = string
}

# ── Mapeo de tier a tipos de instancia ───────────────────────

locals {
  tier_config = {
    pilot = {
      ec2_instance_type = "t3.medium"
      rds_instance_type = "db.t3.micro"
      rds_multi_az      = false
      ebs_size_gb       = 50
    }
    small = {
      ec2_instance_type = "t3.large"
      rds_instance_type = "db.t3.small"
      rds_multi_az      = false
      ebs_size_gb       = 100
    }
    medium = {
      ec2_instance_type = "t3.xlarge"
      rds_instance_type = "db.t3.medium"
      rds_multi_az      = true
      ebs_size_gb       = 200
    }
    large = {
      ec2_instance_type = "m6i.2xlarge"
      rds_instance_type = "db.r6g.large"
      rds_multi_az      = true
      ebs_size_gb       = 500
    }
  }

  config = local.tier_config[var.tier]

  common_tags = {
    Product   = "sciback-odoo"
    Client    = var.client_slug
    Tier      = var.tier
    ManagedBy = "terraform"
  }
}
