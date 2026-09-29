locals {
  name = "${var.project_key}-staging"
  tags = {
    environment           = "staging"
    managed-by            = "terraform"
    workload              = "learning-platform"
    backup-retention-days = tostring(var.backup_retention_days)
  }
}

data "oci_identity_availability_domains" "available" {
  compartment_id = var.tenancy_ocid
}

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  state                    = "AVAILABLE"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_objectstorage_namespace" "current" {
  compartment_id = var.compartment_ocid
}

resource "oci_core_vcn" "staging" {
  cidr_blocks    = ["10.42.0.0/16"]
  compartment_id = var.compartment_ocid
  display_name   = local.name
  dns_label      = "learningstg"
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "staging" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-internet"
  enabled        = true
  vcn_id         = oci_core_vcn.staging.id
  freeform_tags  = local.tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-public"
  vcn_id         = oci_core_vcn.staging.id
  freeform_tags  = local.tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.staging.id
  }
}

resource "oci_core_subnet" "public" {
  cidr_block                 = "10.42.10.0/24"
  compartment_id             = var.compartment_ocid
  display_name               = "${local.name}-public"
  dns_label                  = "public"
  prohibit_internet_ingress  = false
  prohibit_public_ip_on_vnic = false
  route_table_id             = oci_core_route_table.public.id
  vcn_id                     = oci_core_vcn.staging.id
  freeform_tags              = local.tags
}

resource "oci_core_network_security_group" "application" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-application"
  vcn_id         = oci_core_vcn.staging.id
  freeform_tags  = local.tags
}

resource "oci_core_network_security_group_security_rule" "web" {
  for_each = toset(["80", "443"])

  network_security_group_id = oci_core_network_security_group.application.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = "0.0.0.0/0"
  source_type               = "CIDR_BLOCK"
  description               = "Public web traffic"

  tcp_options {
    destination_port_range {
      min = tonumber(each.value)
      max = tonumber(each.value)
    }
  }
}

resource "oci_core_network_security_group_security_rule" "ssh" {
  count = var.admin_cidr == "" ? 0 : 1

  network_security_group_id = oci_core_network_security_group.application.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.admin_cidr
  source_type               = "CIDR_BLOCK"
  description               = "Temporary administrator SSH access"

  tcp_options {
    destination_port_range {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_network_security_group_security_rule" "egress" {
  network_security_group_id = oci_core_network_security_group.application.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
  description               = "Outbound package, registry, identity, and telemetry access"
}

resource "oci_core_instance" "application" {
  availability_domain = data.oci_identity_availability_domains.available.availability_domains[0].name
  compartment_id      = var.compartment_ocid
  display_name        = local.name
  shape               = "VM.Standard.A1.Flex"
  freeform_tags       = local.tags

  shape_config {
    memory_in_gbs = var.instance_memory_gb
    ocpus         = var.instance_ocpus
  }

  create_vnic_details {
    assign_public_ip = true
    display_name     = "${local.name}-primary"
    hostname_label   = "learning-staging"
    nsg_ids          = [oci_core_network_security_group.application.id]
    subnet_id        = oci_core_subnet.public.id
  }

  source_details {
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    source_type             = "image"
    boot_volume_size_in_gbs = 50
    boot_volume_vpus_per_gb = 10
  }

  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  agent_config {
    is_management_disabled = false
    is_monitoring_disabled = false
  }

  availability_config {
    recovery_action = "RESTORE_INSTANCE"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_authorized_key
    user_data           = base64encode(file("${path.module}/cloud-init.yaml"))
  }

  lifecycle {
    precondition {
      condition     = length(data.oci_core_images.ubuntu_arm.images) > 0
      error_message = "No compatible Ubuntu 24.04 ARM image is available in the selected region."
    }
  }
}

resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-backups"
  namespace      = data.oci_objectstorage_namespace.current.namespace
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"
  freeform_tags  = local.tags
}

resource "oci_budget_budget" "staging" {
  amount         = var.budget_amount
  compartment_id = var.tenancy_ocid
  reset_period   = "MONTHLY"
  display_name   = "${local.name}-monthly"
  description    = "Monthly ceiling for the staging compartment; alerts do not stop spending."
  target_type    = "COMPARTMENT"
  targets        = [var.compartment_ocid]
  freeform_tags  = local.tags
}

resource "oci_budget_alert_rule" "thresholds" {
  for_each = {
    actual_50   = { threshold = 50, type = "ACTUAL" }
    actual_80   = { threshold = 80, type = "ACTUAL" }
    forecast_80 = { threshold = 80, type = "FORECAST" }
    actual_100  = { threshold = 100, type = "ACTUAL" }
  }

  budget_id      = oci_budget_budget.staging.id
  display_name   = "${local.name}-${replace(each.key, "_", "-")}"
  description    = "Cost alert for ${each.value.type} spend at ${each.value.threshold}% of budget."
  message        = "OCI staging spend reached ${each.value.threshold}% (${each.value.type}). Review resources immediately."
  recipients     = var.budget_alert_recipients
  threshold      = each.value.threshold
  threshold_type = "PERCENTAGE"
  type           = each.value.type
}
