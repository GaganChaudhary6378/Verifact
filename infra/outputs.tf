output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.verifact_backend.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.verifact_eip.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.verifact_backend.private_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/verifact-key ec2-user@${aws_eip.verifact_eip.public_ip}"
}

output "api_url" {
  description = "Backend API URL"
  value       = "http://${aws_eip.verifact_eip.public_ip}:8000"
}

output "api_docs_url" {
  description = "API documentation URL"
  value       = "http://${aws_eip.verifact_eip.public_ip}:8000/docs"
}

output "health_check_url" {
  description = "Health check endpoint URL"
  value       = "http://${aws_eip.verifact_eip.public_ip}:8000/health"
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.verifact_sg.id
}

output "kms_key_id" {
  description = "KMS key ID for EBS encryption"
  value       = aws_kms_key.ebs.id
}

output "kms_key_arn" {
  description = "KMS key ARN for EBS encryption"
  value       = aws_kms_key.ebs.arn
}
