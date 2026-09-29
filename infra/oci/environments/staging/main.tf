module "staging_foundation" {
  source = "../../modules/staging-foundation"

  tenancy_ocid            = var.tenancy_ocid
  compartment_ocid        = var.compartment_ocid
  project_key             = var.project_key
  ssh_authorized_key      = var.ssh_authorized_key
  admin_cidr              = var.admin_cidr
  budget_amount           = 55
  budget_alert_recipients = var.budget_alert_recipients
  instance_ocpus          = 2
  instance_memory_gb      = 12
  backup_retention_days   = 30
}
