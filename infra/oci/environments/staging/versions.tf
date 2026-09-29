terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "= 9.7.1"
    }
  }
}

provider "oci" {
  region = var.region
}
