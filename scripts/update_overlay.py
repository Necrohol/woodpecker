import os, requests

# Constants
REPO_ROOT = os.getcwd()
# Correct API endpoint for Woodpecker releases
API_URL = "https://github.com"
MAX_VERSIONS = 4
ARCH_MAP = {"amd64": "amd64", "arm": "arm", "arm64": "arm64", "riscv": "riscv64"}
PKGS = ["server", "agent", "cli"]

def setup_accounts():
    """Create acct-group/user once."""
    for cat in ["acct-group", "acct-user"]:
        path = os.path.join(REPO_ROOT, cat, "woodpecker")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            e_type = cat.replace("-", "_")
            content = f"EAPI=8\ninherit {e_type}\nACCT_{e_type.upper()}_ID=404\n"
            if "user" in cat: content += "ACCT_USER_GROUPS=( woodpecker )\n"
            with open(os.path.join(path, "woodpecker-0.ebuild"), "w") as f: f.write(content)

def setup_files(pkg):
    """Generates the systemd and env files used by src_install."""
    files_dir = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{pkg}", "files")
    os.makedirs(files_dir, exist_ok=True)
    
    # Systemd Unit
    unit = f'''[Unit]
Description=Woodpecker CI {pkg.capitalize()}
After=network.target

[Service]
Type=simple
User=woodpecker
Group=woodpecker
EnvironmentFile=-/etc/woodpecker/woodpecker-{pkg}.conf
ExecStart=/usr/bin/woodpecker-{pkg}
Restart=always

[Install]
WantedBy=multi-user.target
'''
    # Env File
    env = f'''# Woodpecker {pkg.capitalize()} Config
# See upstream docs for variables
WOODPECKER_AGENT_SECRET=$(openssl rand -hex 32)
'''
    with open(os.path.join(files_dir, f"woodpecker-{pkg}.service"), "w") as f: f.write(unit)
    with open(os.path.join(files_dir, f"woodpecker-{pkg}.conf"), "w") as f: f.write(env)

def update_ebuilds():
    r = requests.get(API_URL)
    if r.status_code != 200: return
    releases = r.json()
    # (Raw Tag, Gentoo Version)
    versions = [(r['tag_name'].lstrip('v'), r['tag_name'].lstrip('v').replace('-', '_')) for r in releases][:MAX_VERSIONS]

    for pkg in PKGS:
        setup_files(pkg)
        pkg_path = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{pkg}")
        os.makedirs(pkg_path, exist_ok=True)
        
        kept = []
        for raw_v, gentoo_v in versions:
            ebuild_name = f"woodpecker-{pkg}-{gentoo_v}.ebuild"
            kept.append(ebuild_name)
            
            # Construct SRC_URI with ARCH_MAP
            src_uri_lines = [f'{arch}? ( https://github.com{raw_v}/woodpecker-{pkg}_linux_{wp_arch}.tar.gz )' 
                             for arch, wp_arch in ARCH_MAP.items()]
            src_uri = "\n\t".join(src_uri_lines)

            content = f'''EAPI=8
inherit systemd

DESCRIPTION="Woodpecker CI {pkg} (binary)"
HOMEPAGE="https://woodpecker-ci.org"
SRC_URI="
	{src_uri}
"
S="${{WORKDIR}}"

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64 ~arm ~arm64 ~riscv"
RESTRICT="strip"

RDEPEND="
	acct-group/woodpecker
	acct-user/woodpecker
"

src_install() {{
	dobin woodpecker-{pkg}
	
	systemd_dounit "${{FILESDIR}}/woodpecker-{pkg}.service"
	
	insinto /etc/woodpecker
	newins "${{FILESDIR}}/woodpecker-{pkg}.conf" woodpecker-{pkg}.conf
}}
'''
            with open(os.path.join(pkg_path, ebuild_name), "w") as f: f.write(content)

        # Prune old ebuilds
        for f in os.listdir(pkg_path):
            if f.endswith(".ebuild") and f not in kept:
                os.remove(os.path.join(pkg_path, f))

if __name__ == "__main__":
    setup_accounts()
    update_ebuilds()

# ... (rest of your update.py logic above) ...

        content = f'''EAPI=8
inherit systemd

DESCRIPTION="Woodpecker CI {pkg} (binary)"
HOMEPAGE="https://woodpecker-ci.org"
SRC_URI="
	{src_uri}
"
S="${{WORKDIR}}"

LICENSE="Apache-2.0"
SLOT="0"
KEYWORDS="~amd64 ~arm ~arm64 ~riscv"
RESTRICT="strip"

RDEPEND="
	acct-group/woodpecker
	acct-user/woodpecker
"

src_install() {{
	dobin woodpecker-{pkg}
	
	systemd_dounit "${{FILESDIR}}/woodpecker-{pkg}.service"
	
	insinto /etc/woodpecker
	newins "${{FILESDIR}}/woodpecker-{pkg}.conf" woodpecker-{pkg}.conf
}}

pkg_postinst() {{
	elog "Woodpecker CI {pkg} has been installed."
	elog ""
	elog "1. Configuration:"
	elog "   Edit /etc/woodpecker/woodpecker-{pkg}.conf to set your environment variables."
	elog ""
	elog "2. Security:"
	elog "   If this is a fresh install, generate a shared secret for server-agent comms:"
	elog "   'openssl rand -hex 32'"
	elog ""
	elog "3. Service:"
	elog "   To start Woodpecker via systemd:"
	elog "   'systemctl enable --now woodpecker-{pkg}'"
    
	if [[ "{pkg}" == "server" ]]; then
		ewarn "Ensure your reverse proxy (Nginx/Lighttpd) is configured for WebSockets/SSE."
	fi
}}
'''
# ... (rest of the script) ...

