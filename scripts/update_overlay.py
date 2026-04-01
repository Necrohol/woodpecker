import os, requests

REPO_ROOT = os.getcwd()
API_URL = "https://github.com"
MAX_VERSIONS = 4
PKGS = ["server", "agent", "cli"]
ARCH_MAP = {"amd64": "amd64", "arm": "arm", "arm64": "arm64", "riscv": "riscv64"}

def write_file(path, name, content):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, name), "w") as f:
        f.write(content)

def setup_files(suffix):
    """Generates OpenRC and Webserver config files."""
    pkg_path = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{suffix}", "files")
    
    # OpenRC Init Script
    init_script = f'''#!/sbin/openrc-run
description="Woodpecker CI {suffix}"
command="/usr/bin/woodpecker-{suffix}"
command_background="yes"
pidfile="/run/woodpecker-{suffix}.pid"
command_user="woodpecker:woodpecker"
output_log="/var/log/woodpecker-{suffix}.log"
error_log="/var/log/woodpecker-{suffix}.log"
'''
    write_file(pkg_path, f"woodpecker-{suffix}.initd", init_script)

    if suffix == "server":
        # Nginx Template
        nginx_conf = '''server {
    listen 80; server_name ci.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
    }
}'''
        write_file(pkg_path, "nginx.conf", nginx_conf)

def update_ebuilds():
    releases = requests.get(API_URL).json()
    versions = [(r['tag_name'].lstrip('v'), r['tag_name'].lstrip('v').replace('-', '_')) for r in releases][:MAX_VERSIONS]

    for suffix in PKGS:
        setup_files(suffix) # Create the files/ directory content
        pkg_path = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{suffix}")
        
        kept = []
        for raw_v, gentoo_v in versions:
            ebuild_name = f"woodpecker-{suffix}-{gentoo_v}.ebuild"
            kept.append(ebuild_name)
            
            src_uri = "\\n\\t".join([f'{arch}? ( https://github.com{raw_v}/woodpecker-{suffix}_linux_{wp_arch}.tar.gz )' 
                                   for arch, wp_arch in ARCH_MAP.items()])

            ebuild_content = f'''EAPI=8
DESCRIPTION="Woodpecker CI {suffix} (binary)"
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
	dobin woodpecker-{suffix}
	newinitd "${{FILESDIR}}/woodpecker-{suffix}.initd" woodpecker-{suffix}
	
	if [[ "{suffix}" == "server" ]]; then
		insinto /etc/nginx/modules.d
		doins "${{FILESDIR}}/nginx.conf"
	fi
}}
'''
            write_file(pkg_path, ebuild_name, ebuild_content)

if __name__ == "__main__":
    update_ebuilds()
