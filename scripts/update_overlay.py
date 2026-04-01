import os
import requests

# --- Configuration ---
REPO_ROOT = os.getcwd()
API_URL = "https://github.com"
MAX_VERSIONS = 3
ARCH_MAP = {
    "amd64": "amd64", 
    "arm": "arm", 
    "arm64": "arm64", 
    "riscv": "riscv64"
}
PKGS = ["server", "agent", "cli"]

def setup_accounts():
    """Create acct-group/user with proper home for rootless Podman storage."""
    for cat in ["acct-group", "acct-user"]:
        path = os.path.join(REPO_ROOT, cat, "woodpecker")
        os.makedirs(path, exist_ok=True)
        e_type = cat.replace("-", "_")
        rdepend = 'RDEPEND="acct-group/woodpecker"' if "user" in cat else ""
        content = f'EAPI=8\ninherit {e_type}\n{rdepend}\nACCT_{e_type.upper()}_ID=404\n'
        if "user" in cat:
            # Important: Rootless Podman needs a real home directory for container storage
            content += 'ACCT_USER_GROUPS=( woodpecker )\nACCT_USER_HOME="/var/lib/woodpecker"\n'
        with open(os.path.join(path, "woodpecker-0.ebuild"), "w") as f:
            f.write(content)

def get_ebuild_content(pkg, raw_v, src_uri):
    """Generates the ebuild with post-inst instructions for Gentoo/Podman."""
    iuse = "sqlite mysql postgresql nginx apache" if pkg == "server" else ""
    
    content = f'''EAPI=8
inherit systemd

DESCRIPTION="Woodpecker CI {pkg} (binary)"
HOMEPAGE="https://woodpecker-ci.org"
SRC_URI="
\t{src_uri}
"
S="${{WORKDIR}}"

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64 ~arm ~arm64 ~riscv"
IUSE="{iuse}"
RESTRICT="strip"

RDEPEND="
\tacct-group/woodpecker
\tacct-user/woodpecker
\tapp-misc/ca-certificates
'''
    if pkg == "server":
        content += '\tsqlite? ( dev-db/sqlite:3 )\n\tmysql? ( dev-db/mysql )\n\tpostgresql? ( dev-db/postgresql )\n'
    elif pkg == "agent":
        content += '\tapp-containers/podman[rootless,seccomp,wrapper]\n\tapp-containers/podman-compose[wrapper]\n'
    
    content += '"\n\nsrc_install() {\n\tdobin woodpecker-' + pkg + '\n'
    if pkg != "cli":
        content += f'''
\tnewinitd "${{FILESDIR}}/woodpecker-{pkg}.initd" "woodpecker-{pkg}"
\tnewconfd "${{FILESDIR}}/woodpecker-{pkg}.confd" "woodpecker-{pkg}"
\tsystemd_dounit "${{FILESDIR}}/woodpecker-{pkg}.service"
\tinsinto /etc/woodpecker
\tnewins "${{FILESDIR}}/woodpecker-{pkg}.confd" "woodpecker-{pkg}.conf"
'''
    content += '}\n'

    if pkg == "agent":
        content += '''
pkg_postinst() {
\telog "For rootless Podman to work (especially for 'emerge' in containers):"
\telog "1. Ensure /etc/subuid and /etc/subgid contain 'woodpecker:100000:65536'"
\telog "2. The woodpecker user needs a valid shell and home (set to /var/lib/woodpecker)"
\telog "3. Set DOCKER_HOST='unix:///run/user/$(id -u woodpecker)/podman/podman.sock' in /etc/conf.d/woodpecker-agent"
}
'''
    return content

# ... [Include the rest of the update_ebuilds() and service generation logic from before] ...
def update_ebuilds():
    headers = {"Accept": "application/vnd.github.v3+json"}
    r = requests.get(API_URL, headers=headers)
    if r.status_code != 200:
        print(f"Error fetching releases: {r.status_code}")
        return
    
    releases = r.json()
    # (Raw Tag vX.Y.Z, Gentoo-safe version X_Y_Z)
    versions = []
    for rel in releases:
        if not rel.get('prerelease') and len(versions) < MAX_VERSIONS:
            raw = rel['tag_name']
            safe = raw.lstrip('v').replace('-', '_')
            versions.append((raw, safe))

    for pkg in PKGS:
        setup_files(pkg)
        pkg_path = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{pkg}")
        os.makedirs(pkg_path, exist_ok=True)
        
        current_ebuilds = []
        for raw_v, gentoo_v in versions:
            ebuild_name = f"woodpecker-{pkg}-{gentoo_v}.ebuild"
            current_ebuilds.append(ebuild_name)
            
            # Construct SRC_URI specifically for Woodpecker release naming
            src_uri_lines = []
            for arch, wp_arch in ARCH_MAP.items():
                line = f'{arch}? ( https://github.com{raw_v}/woodpecker-{pkg}_linux_{wp_arch}.tar.gz )'
                src_uri_lines.append(line)
            src_uri = "\n\t".join(src_uri_lines)

            content = get_ebuild_template(pkg, raw_v, src_uri)
            with open(os.path.join(pkg_path, ebuild_name), "w") as f:
                f.write(content)

        # Prune old versions not in the latest set
        for f in os.listdir(pkg_path):
            if f.endswith(".ebuild") and f not in current_ebuilds:
                os.remove(os.path.join(pkg_path, f))

if __name__ == "__main__":
    print("Initializing Overlay Accounts...")
    setup_accounts()
    print("Updating Package Ebuilds...")
    update_ebuilds()
    print("Done.")
