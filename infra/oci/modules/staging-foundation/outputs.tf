output "instance_id" {
  description = "OCI compute instance OCID."
  value       = oci_core_instance.application.id
}

output "public_ip" {
  description = "Ephemeral staging IP. It is not a substitute for a domain and trusted HTTPS."
  value       = oci_core_instance.application.public_ip
}

output "backup_bucket_name" {
  description = "Private Object Storage bucket for encrypted staging backups."
  value       = oci_objectstorage_bucket.backups.name
}

output "budget_id" {
  description = "OCI monthly budget OCID."
  value       = oci_budget_budget.staging.id
}
