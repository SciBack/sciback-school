output "ec2_public_ip" {
  description = "IP pública del servidor Odoo"
  value       = aws_eip.odoo.public_ip
}

output "rds_endpoint" {
  description = "Endpoint RDS (interno VPC)"
  value       = aws_db_instance.postgres.address
  sensitive   = true
}

output "s3_adjuntos" {
  description = "Bucket S3 para adjuntos Odoo"
  value       = aws_s3_bucket.adjuntos.id
}

output "s3_backups" {
  description = "Bucket S3 para backups"
  value       = aws_s3_bucket.backups.id
}

output "secrets_arn" {
  description = "ARN del secreto en Secrets Manager"
  value       = aws_secretsmanager_secret.odoo.arn
}

output "next_steps" {
  description = "Pasos siguientes después del provisioning"
  value = <<-EOT
    1. Apuntar DNS: ${var.domain} → ${aws_eip.odoo.public_ip}
    2. Ejecutar Ansible: make deploy CLIENT=${var.client_slug}
    3. Obtener certificado SSL: (Ansible lo hace vía certbot)
    4. Verificar Odoo: https://${var.domain}/web/login
    5. Instalar módulos: make install MOD=sciback_school_portal CLIENT=${var.client_slug}
  EOT
}
