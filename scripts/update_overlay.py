import os, requests

REPO_ROOT = os.getcwd()
API_URL = "https://github.com"
MAX_VERSIONS = 4
PKGS = ["server", "agent", "cli"]
ARCH_MAP = {"amd64": "amd64", "arm": "arm", "arm64": "arm64", "riscv": "riscv64"}

def setup_accounts():
    """Run once: Creates acct-group and acct-user if missing."""
    for cat in ["acct-group", "acct-user"]:
        path = os.path.join(REPO_ROOT, cat, "woodpecker")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            ebuild_type = cat.replace("-", "_")
            # Group ID 404, User ID 404
            content = f"EAPI=8\ninherit {ebuild_type}\n"
            content += "ACCT_USER_ID=404\nACCT_USER_GROUPS=( woodpecker )\n" if "user" in cat else "ACCT_GROUP_ID=404\n"
            with open(os.path.join(path, "woodpecker-0.ebuild"), "w") as f:
                f.write(content)

def update_binaries():
    releases = requests.get(API_URL).json()
    # Gentoo: v3.0-rc1 -> 3.0_rc1
    versions = [(r['tag_name'].lstrip('v'), r['tag_name'].lstrip('v').replace('-', '_')) for r in releases][:MAX_VERSIONS]

    for suffix in PKGS:
        pkg_path = os.path.join(REPO_ROOT, "dev-util", f"woodpecker-{suffix}")
        os.makedirs(pkg_path, exist_ok=True)
        
        kept = []
        for raw_v, gentoo_v in versions:
            ebuild_name = f"woodpecker-{suffix}-{gentoo_v}.ebuild"
            kept.append(ebuild_name)
            
            src_uri = "\n\t".join([f'{arch}? ( https://github.com{raw_v}/woodpecker-{suffix}_linux_{wp_arch}.tar.gz )' 
                                   for arch, wp_arch in ARCH_MAP.items()])

            with open(os.path.join(pkg_path, ebuild_name), "w") as f:
                f.write(f'''EAPI=8
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
}}
''')
        # Prune old versions
        for f in os.listdir(pkg_path):
            if f.endswith(".ebuild") and f not in kept:
                os.remove(os.path.join(pkg_path, f))

if __name__ == "__main__":
    setup_accounts()
    update_binaries()
