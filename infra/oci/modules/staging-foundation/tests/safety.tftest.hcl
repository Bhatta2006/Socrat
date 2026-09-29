mock_provider "oci" {
  override_during = plan
}

variables {
  tenancy_ocid            = "ocid1.tenancy.oc1..test"
  compartment_ocid        = "ocid1.compartment.oc1..test"
  ssh_authorized_key      = "ssh-ed25519 test-public-key"
  budget_alert_recipients = "owner@example.com"
}

override_data {
  target = data.oci_identity_availability_domains.available
  values = {
    availability_domains = [{ name = "test-availability-domain" }]
  }
}

override_data {
  target = data.oci_core_images.ubuntu_arm
  values = {
    images = [{ id = "ocid1.image.oc1.ap-hyderabad-1.test" }]
  }
}

override_data {
  target = data.oci_objectstorage_namespace.current
  values = {
    namespace = "test-namespace"
  }
}

run "free_first_defaults" {
  command = plan

  assert {
    condition     = oci_core_instance.application.shape == "VM.Standard.A1.Flex"
    error_message = "Staging must remain on the reviewed Ampere A1 shape."
  }

  assert {
    condition     = oci_core_instance.application.shape_config[0].ocpus == 2
    error_message = "Default staging compute must not exceed 2 OCPUs."
  }

  assert {
    condition     = oci_core_instance.application.shape_config[0].memory_in_gbs == 12
    error_message = "Default staging memory must not exceed 12 GB."
  }

  assert {
    condition     = oci_budget_budget.staging.amount == 55
    error_message = "The monthly staging budget must remain 55."
  }

  assert {
    condition     = length(oci_core_network_security_group_security_rule.ssh) == 0
    error_message = "SSH must remain closed unless a trusted administrator CIDR is provided."
  }

  assert {
    condition     = oci_objectstorage_bucket.backups.access_type == "NoPublicAccess"
    error_message = "The backup bucket must never be public."
  }
}

run "rejects_budget_above_ceiling" {
  command = plan

  variables {
    budget_amount = 56
  }

  expect_failures = [var.budget_amount]
}

run "restricts_ssh_to_explicit_cidr" {
  command = plan

  variables {
    admin_cidr = "203.0.113.10/32"
  }

  assert {
    condition     = length(oci_core_network_security_group_security_rule.ssh) == 1
    error_message = "An explicit administrator CIDR must create exactly one SSH rule."
  }

  assert {
    condition     = oci_core_network_security_group_security_rule.ssh[0].source == "203.0.113.10/32"
    error_message = "SSH access must use only the configured trusted CIDR."
  }
}
