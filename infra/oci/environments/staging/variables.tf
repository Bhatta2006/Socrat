variable "region" {
  description = "OCI home region. Always Free resources must be created in the tenancy home region."
  type        = string
  default     = "ap-hyderabad-1"

  validation {
    condition     = var.region == "ap-hyderabad-1"
    error_message = "This reviewed staging profile is fixed to OCI India South (Hyderabad)."
  }
}

variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID."
}

variable "compartment_ocid" {
  type        = string
  description = "Dedicated staging compartment OCID."
}

variable "ssh_authorized_key" {
  type        = string
  description = "Public SSH key only."
  sensitive   = true
}

variable "admin_cidr" {
  type        = string
  description = "Trusted administrator IPv4 CIDR; empty keeps SSH closed at the OCI network boundary."
  default     = ""
}

variable "budget_alert_recipients" {
  type        = string
  description = "Comma-separated email addresses for mandatory cost alerts."
}

variable "project_key" {
  type        = string
  description = "Stable technical identifier; it need not match the final company name."
  default     = "learning-platform"
}
