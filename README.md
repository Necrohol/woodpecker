# Woodpecker CI Gentoo Overlay

A specialized Gentoo overlay for [Woodpecker CI](https://woodpecker-ci.org), providing pre-compiled binaries for **amd64**, **arm**, **arm64**, and **riscv64**.

This overlay is automatically updated daily via GitHub Actions to ensure the latest releases are always available.

## 🚀 Quick Install (The Lean Way)

You can add this overlay directly to Portage without installing extra tools like `eselect-repository`.

```bash
# 1. Download the repository configuration
sudo wget https://githubusercontent.com -O /etc/portage/repos.conf/woodpecker.conf

# 2. Sync the overlay
sudo emaint sync -r woodpecker
