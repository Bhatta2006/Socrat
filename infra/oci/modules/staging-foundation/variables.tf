variable "tenancy_ocid" {
  description = "OCI tenancy OCID. Used only as the budget resource's parent compartment."
  type        = string
}

variable "compartment_ocid" {
  description = "Dedicated staging compartment OCID. Do not target the tenancy root."
  type        = string
}

variable "project_key" {
  description = "Stable technical identifier independent of the final company name."
  type        = string
  default     = "learning-platform"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,29}$", var.project_key))
    error_message = "project_key must be 3-30 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "ssh_authorized_key" {
  description = "Public SSH key only. Never provide a private key."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^(ssh-ed25519|ecdsa-sha2-nistp256|sk-ssh-ed25519@openssh.com) ", var.ssh_authorized_key))
    error_message = "Use an Ed25519, security-key Ed25519, or NIST P-256 public SSH key."
  }
}

variable "admin_cidr" {
  description = "Single trusted IPv4 CIDR allowed to reach SSH. Use an empty string to keep SSH closed."
  type        = string
  default     = ""

  validation {
    condition     = var.admin_cidr == "" || can(cidrnetmask(var.admin_cidr))
    error_message = "admin_cidr must be empty or a valid IPv4 CIDR."
  }
}

variable "budget_amount" {
  description = "Monthly OCI budget in the tenancy's billing currency. Alerts do not automatically stop resources."
  type        = number
  default     = 55

  validation {
    condition     = var.budget_amount >= 1 && var.budget_amount <= 55
    error_message = "This staging stack enforces a maximum monthly planning budget of 55."
  }
}

variable "budget_alert_recipients" {
  description = "Comma-separated email addresses for OCI budget alerts."
  type        = string

  validation {
    condition     = length(trimspace(var.budget_alert_recipients)) > 3
    error_message = "At least one budget alert recipient is required."
  }
}

variable "instance_ocpus" {
  description = "Ampere A1 OCPUs. Default matches the current Always Free allowance."
  type        = number
  default     = 2

  validation {
    condition     = var.instance_ocpus >= 1 && var.instance_ocpus <= 2
    error_message = "The free-first staging profile permits at most 2 A1 OCPUs."
  }
}

variable "instance_memory_gb" {
  description = "Ampere A1 memory in GB. Default matches the current Always Free allowance."
  type        = number
  default     = 12

  validation {
    condition     = var.instance_memory_gb >= 6 && var.instance_memory_gb <= 12
    error_message = "The free-first staging profile permits 6-12 GB of memory."
  }
}

variable "backup_retention_days" {
  description = "Application backup retention policy recorded as a resource tag for the deploy process."
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days >= 14 && var.backup_retention_days <= 90
    error_message = "Staging backup retention must be between 14 and 90 days."
  }
}
